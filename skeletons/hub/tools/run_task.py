# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "strands-agents[ollama,openai]==1.47.0",
# ]
# ///
"""Запустить первую готовую задачу хаба через Strands Agent."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


ENV_LINE = re.compile(r"^(?:export\s+)?([A-Z][A-Z0-9_]*)=(.*)$")
READY_TASK = re.compile(r"^###\s+(TASK-[0-9]{4,})\..*\[\s*\]\s+ready\b", re.MULTILINE)


class TaskAgentError(RuntimeError):
    """Ошибка конфигурации или безопасного выполнения задачи."""


def parse_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise TaskAgentError(f"не найден файл окружения: {path}")
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = ENV_LINE.fullmatch(line)
        if not match:
            raise TaskAgentError(f"{path}:{number}: ожидается NAME=value")
        name, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name] = value
    return values


def positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise TaskAgentError(f"{name} должен быть целым числом") from error
    if parsed <= 0:
        raise TaskAgentError(f"{name} должен быть положительным")
    return parsed


def configured(value: str) -> bool:
    return bool(value and not re.fullmatch(r"<[^>]+>", value))


@dataclass(frozen=True)
class Settings:
    provider: Literal["ollama", "openai"]
    base_url: str
    api_key: str = field(repr=False)
    model_id: str
    workspace: Path
    methodology: Path
    max_file_bytes: int
    command_timeout_seconds: int

    @classmethod
    def load(cls, hub: Path) -> "Settings":
        values = parse_env(hub / ".env")
        provider = values.get("TASK_AGENT_MODEL_PROVIDER", "ollama").lower()
        if provider not in {"ollama", "openai"}:
            raise TaskAgentError("TASK_AGENT_MODEL_PROVIDER должен быть ollama или openai")
        base_url = values.get(
            "TASK_AGENT_MODEL_BASE_URL",
            "http://localhost:11434" if provider == "ollama" else "",
        ).rstrip("/")
        required = {
            "TASK_AGENT_MODEL_BASE_URL": base_url,
            "TASK_AGENT_MODEL_ID": values.get("TASK_AGENT_MODEL_ID", ""),
            "TASK_AGENT_WORKSPACE": values.get("TASK_AGENT_WORKSPACE", ""),
            "TASK_AGENT_METHODOLOGY_PATH": values.get("TASK_AGENT_METHODOLOGY_PATH", ""),
        }
        if provider == "openai":
            required["TASK_AGENT_MODEL_API_KEY"] = values.get("TASK_AGENT_MODEL_API_KEY", "")
        missing = [name for name, value in required.items() if not configured(value)]
        if missing:
            raise TaskAgentError("не заданы переменные в .env: " + ", ".join(missing))
        workspace = Path(required["TASK_AGENT_WORKSPACE"]).expanduser().resolve()
        methodology = Path(required["TASK_AGENT_METHODOLOGY_PATH"]).expanduser().resolve()
        if not workspace.is_dir():
            raise TaskAgentError(f"рабочая область не существует: {workspace}")
        if not methodology.is_dir():
            raise TaskAgentError(f"репозиторий методологии не существует: {methodology}")
        try:
            hub.resolve().relative_to(workspace)
        except ValueError as error:
            raise TaskAgentError("хаб должен находиться внутри TASK_AGENT_WORKSPACE") from error
        try:
            methodology.relative_to(workspace)
        except ValueError as error:
            raise TaskAgentError("методология должна находиться внутри TASK_AGENT_WORKSPACE") from error
        return cls(
            provider=provider,
            base_url=base_url,
            api_key=values.get("TASK_AGENT_MODEL_API_KEY", ""),
            model_id=required["TASK_AGENT_MODEL_ID"],
            workspace=workspace,
            methodology=methodology,
            max_file_bytes=positive_int(
                values.get("TASK_AGENT_MAX_FILE_BYTES", "200000"),
                "TASK_AGENT_MAX_FILE_BYTES",
            ),
            command_timeout_seconds=positive_int(
                values.get("TASK_AGENT_COMMAND_TIMEOUT_SECONDS", "120"),
                "TASK_AGENT_COMMAND_TIMEOUT_SECONDS",
            ),
        )


def inside(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise TaskAgentError(f"путь выходит за рабочую область: {relative}") from error
    return candidate


def first_ready_task_block(hub: Path) -> str:
    backlog = (hub / "BACKLOG.md").read_text(encoding="utf-8")
    match = READY_TASK.search(backlog)
    if match is None:
        raise TaskAgentError("в BACKLOG.md нет задачи [ ] ready")
    tail = backlog[match.start():]
    cutoffs = []
    next_task = re.search(r"\n### ", tail[1:])
    if next_task:
        cutoffs.append(next_task.start() + 1)
    section = tail.find("\n## ")
    if section != -1:
        cutoffs.append(section)
    end = min(cutoffs) if cutoffs else len(tail)
    return tail[:end].strip()


def task_is_qualified(task_block: str) -> bool:
    return all(
        re.search(rf"^{re.escape(label)}:", task_block, re.MULTILINE)
        for label in ("Риск", "Автономность", "Триггеры", "Откат")
    )


def create_agent(settings: Settings, hub: Path):
    try:
        from strands import Agent, tool
        from strands.models.ollama import OllamaModel
        from strands.models.openai import OpenAIModel
    except ImportError as error:
        raise TaskAgentError("Strands Agents не установлен; запускайте файл через uv run") from error

    @tool
    def read_file(path: str) -> str:
        """Прочитать UTF-8 файл внутри рабочей области программы."""
        candidate = inside(settings.workspace, path)
        if not candidate.is_file():
            raise TaskAgentError(f"файл не найден: {path}")
        if candidate.stat().st_size > settings.max_file_bytes:
            raise TaskAgentError(f"файл превышает TASK_AGENT_MAX_FILE_BYTES: {path}")
        return candidate.read_text(encoding="utf-8")

    @tool
    def list_files(path: str = ".") -> str:
        """Перечислить файлы каталога внутри рабочей области без рекурсивного обхода."""
        candidate = inside(settings.workspace, path)
        if not candidate.is_dir():
            raise TaskAgentError(f"каталог не найден: {path}")
        return "\n".join(sorted(item.name + ("/" if item.is_dir() else "") for item in candidate.iterdir()))

    @tool
    def write_file(path: str, content: str) -> str:
        """Создать или полностью заменить UTF-8 файл внутри рабочей области программы."""
        candidate = inside(settings.workspace, path)
        in_methodology = candidate == settings.methodology or settings.methodology in candidate.parents
        if candidate.name == ".env" or ".git" in candidate.parts or in_methodology:
            raise TaskAgentError(f"запись запрещена: {path}")
        if len(content.encode("utf-8")) > settings.max_file_bytes:
            raise TaskAgentError(f"содержимое превышает TASK_AGENT_MAX_FILE_BYTES: {path}")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(content, encoding="utf-8")
        return f"записан {candidate.relative_to(settings.workspace)}"

    @tool
    def run_command(command: str, cwd: str = ".") -> str:
        """Запустить одну команду без shell внутри рабочей области программы."""
        arguments = shlex.split(command, posix=os.name != "nt")
        if not arguments:
            raise TaskAgentError("пустая команда")
        directory = inside(settings.workspace, cwd)
        if not directory.is_dir():
            raise TaskAgentError(f"рабочий каталог не найден: {cwd}")
        result = subprocess.run(
            arguments,
            cwd=directory,
            text=True,
            capture_output=True,
            timeout=settings.command_timeout_seconds,
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        if len(output.encode("utf-8")) > settings.max_file_bytes:
            output = output.encode("utf-8")[: settings.max_file_bytes].decode("utf-8", errors="ignore")
            output += "\n[вывод ограничен TASK_AGENT_MAX_FILE_BYTES]"
        return json.dumps({"exit_code": result.returncode, "output": output}, ensure_ascii=False)

    if settings.provider == "ollama":
        model = OllamaModel(host=settings.base_url, model_id=settings.model_id, temperature=0)
    else:
        model = OpenAIModel(
            client_args={"api_key": settings.api_key, "base_url": settings.base_url},
            model_id=settings.model_id,
            params={"temperature": 0},
        )
    hub_relative = hub.relative_to(settings.workspace)
    methodology_relative = settings.methodology.relative_to(settings.workspace)
    return Agent(
        model=model,
        tools=[read_file, list_files, write_file, run_command],
        system_prompt=(
            "Ты исполнитель одной задачи событийной системы. Рабочая область содержит хаб и "
            "разрешённые человеком продуктовые репозитории. Хаб расположен в "
            f"{hub_relative}. Сначала прочитай AGENTS.md хаба, затем задачу, COMPOSITION.md и "
            f"нормативные документы из {methodology_relative}. Выполняй только переданную задачу "
            "и только разрешённые переходы WORKFLOW.md. Не изменяй .env, секреты, lock-файлы, "
            "границы или назначение репозиториев. Не используй shell-конструкции: run_command "
            "принимает ровно одну команду. Доведи разрешённый цикл до done; если требуется решение "
            "человека или выполнено условие остановки, зафиксируй нормативный диагностический статус "
            "по правилам методологии и остановись. Не выдавай локальное изменение за завершённую задачу."
        ),
    )


def main() -> int:
    hub = Path.cwd().resolve()
    try:
        if not (hub / "BACKLOG.md").is_file() or not (hub / ".methodology.yml").is_file():
            raise TaskAgentError("команда должна запускаться из корня хаба")
        settings = Settings.load(hub)
        task_block = first_ready_task_block(hub)
        agent = create_agent(settings, hub)
        if task_is_qualified(task_block):
            instruction = "Выполни эту первую готовую и уже квалифицированную задачу хаба:\n"
        else:
            instruction = (
                "Сначала квалифицируй эту первую минимальную задачу: отдельным служебным PR "
                "task-qualification добавь в BACKLOG.md риск, автономность, триггеры и откат, "
                "слей PR и синхронизируй main хаба. Только после этого выполняй продуктовую задачу:\n"
            )
        result = agent(instruction + task_block)
        print(result)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError, TaskAgentError) as error:
        print(f"Ошибка исполнителя задачи: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
