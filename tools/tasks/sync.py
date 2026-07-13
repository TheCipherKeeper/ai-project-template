"""Создать машинные записи задач из канонического BACKLOG.md."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path


TASK_HEADING = re.compile(
    r"^### (TASK-[0-9]{4,})\. (?:(\[x\])|(\[ \] (ready|needs-input|blocked-external|automation-failed|retry-exhausted))) — .+$"
)
SCALAR_FIELDS = {
    "Цель": "goal",
    "Целевой репозиторий": "target",
    "Риск": "risk",
    "Автономность": "autonomy",
    "Откат": "rollback",
}
LIST_FIELDS = {
    "Готово, когда": "acceptance_criteria",
    "Не входит": "out_of_scope",
    "Триггеры": "triggers",
}
ALLOWED_VALUES = {
    "risk": {"low", "medium", "high", "critical"},
    "autonomy": {"auto-test-deploy", "human-before-production", "human-before-merge"},
    "triggers": {"architecture", "contract", "data", "infrastructure", "security"},
}
DIAGNOSTIC_STATUSES = {
    "needs-input", "blocked-external", "automation-failed", "retry-exhausted"
}
HIGH_RISK_TRIGGERS = {"contract", "data", "security"}
AUTONOMY_RANK = {
    "auto-test-deploy": 0,
    "human-before-production": 1,
    "human-before-merge": 2,
}


class BacklogError(ValueError):
    """Backlog нельзя однозначно представить машинными записями."""


def _field(block: str, label: str) -> str | None:
    labels = "|".join(re.escape(name) for name in (*SCALAR_FIELDS, *LIST_FIELDS, "Диагностика"))
    match = re.search(
        rf"^{re.escape(label)}:\s*(.*?)\s*(?=^(?:{labels}):|^## |\Z)",
        block,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else None


def task_records(backlog_text: str) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    task_like_headings = re.findall(r"^#{1,6}\s+task-[^\n]*$", backlog_text, re.MULTILINE | re.IGNORECASE)
    malformed = [heading for heading in task_like_headings if not TASK_HEADING.fullmatch(heading)]
    if malformed:
        raise BacklogError(f"некорректный заголовок: {malformed[0]}")
    blocks = re.split(r"(?=^### TASK-)", backlog_text, flags=re.MULTILINE)[1:]
    for block in blocks:
        heading = block.splitlines()[0]
        match = TASK_HEADING.fullmatch(heading)
        if not match:
            raise BacklogError(f"некорректный заголовок: {heading}")
        task_id = match.group(1)
        if task_id in records:
            raise BacklogError(f"повтор task ID: {task_id}")
        record: dict[str, object] = {
            "schema_version": 1,
            "id": task_id,
            "status": "done" if match.group(2) else match.group(4),
        }
        for label in (*SCALAR_FIELDS, *LIST_FIELDS, "Диагностика"):
            if len(re.findall(rf"^{re.escape(label)}:", block, re.MULTILINE)) > 1:
                raise BacklogError(f"{task_id}: поле «{label}» указано несколько раз")
        status = str(record["status"])
        diagnostic = _field(block, "Диагностика")
        first_content = next((line.strip() for line in block.splitlines()[1:] if line.strip()), "")
        if status in DIAGNOSTIC_STATUSES:
            if not diagnostic:
                raise BacklogError(f"{task_id}: диагностический статус требует поле «Диагностика»")
            if (
                not first_content.startswith("Диагностика:")
                or not first_content.removeprefix("Диагностика:").strip()
            ):
                raise BacklogError(f"{task_id}: поле «Диагностика» должно идти сразу после заголовка")
            record["diagnostic"] = " ".join(diagnostic.splitlines())
        for label, key in SCALAR_FIELDS.items():
            value = _field(block, label)
            if value:
                record[key] = " ".join(value.splitlines())
            elif key != "rollback":
                raise BacklogError(f"{task_id}: отсутствует поле «{label}»")
        for label, key in LIST_FIELDS.items():
            value = _field(block, label)
            if value is None:
                raise BacklogError(f"{task_id}: отсутствует поле «{label}»")
            if key == "triggers" and value == "- нет":
                record[key] = []
                continue
            lines = [line for line in value.splitlines() if line.strip()]
            unexpected = [line for line in lines if not line.startswith("- ")]
            if unexpected:
                raise BacklogError(
                    f"{task_id}: поле «{label}» содержит неподдерживаемую строку: {unexpected[0].strip()}"
                )
            items = [line[2:].strip() for line in lines]
            if not items or any(not item for item in items):
                raise BacklogError(f"{task_id}: поле «{label}» должно быть списком")
            if len(items) != len(set(items)):
                raise BacklogError(f"{task_id}: поле «{label}» содержит повторяющиеся элементы")
            record[key] = items
        for key, allowed in ALLOWED_VALUES.items():
            values = record[key] if isinstance(record[key], list) else [record[key]]
            invalid = [value for value in values if value not in allowed]
            if invalid:
                raise BacklogError(f"{task_id}: недопустимое значение {key}: {invalid[0]}")
        triggers = set(record["triggers"])
        risk = str(record["risk"])
        autonomy = str(record["autonomy"])
        if triggers & HIGH_RISK_TRIGGERS and risk not in {"high", "critical"}:
            raise BacklogError(
                f"{task_id}: триггеры contract, data и security требуют риск high или critical"
            )
        minimum_autonomy = 2 if risk == "critical" else 1 if risk == "high" else 0
        if AUTONOMY_RANK[autonomy] < minimum_autonomy:
            raise BacklogError(f"{task_id}: автономность слишком широка для риска {risk}")
        records[task_id] = record
    if not records:
        raise BacklogError("нет ни одной задачи TASK-NNNN")
    return records


def serialized(record: dict[str, object]) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2) + "\n"


def sync(root: Path, check: bool = False) -> list[str]:
    backlog = root / "BACKLOG.md"
    records = task_records(backlog.read_text(encoding="utf-8"))
    task_dir = root / ".tasks"
    if task_dir.exists() and not task_dir.is_dir():
        raise BacklogError(".tasks должен быть каталогом")
    differences: list[str] = []
    existing = {path.name: path for path in task_dir.glob("TASK-*.json")} if task_dir.is_dir() else {}
    expected_names = {f"{task_id}.json" for task_id in records}
    contents = {f"{task_id}.json": serialized(record) for task_id, record in records.items()}
    for task_id, record in records.items():
        path = task_dir / f"{task_id}.json"
        content = contents[path.name]
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            differences.append(path.relative_to(root).as_posix())
    for name, path in existing.items():
        if name not in expected_names:
            differences.append(path.relative_to(root).as_posix())
    if differences and not check:
        staging = Path(tempfile.mkdtemp(prefix=".tasks-", dir=root))
        backup = staging.with_name(staging.name + "-previous")
        try:
            if task_dir.is_dir():
                shutil.copytree(task_dir, staging, dirs_exist_ok=True)
            for path in staging.glob("TASK-*.json"):
                path.unlink()
            for name, content in contents.items():
                (staging / name).write_text(content, encoding="utf-8")
            if task_dir.exists():
                task_dir.rename(backup)
            try:
                staging.rename(task_dir)
            except OSError:
                if backup.exists():
                    backup.rename(task_dir)
                raise
            if backup.exists():
                shutil.rmtree(backup, ignore_errors=True)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
            if backup.exists():
                if not task_dir.exists():
                    backup.rename(task_dir)
                else:
                    shutil.rmtree(backup, ignore_errors=True)
    return sorted(differences)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="корень хабового репозитория")
    parser.add_argument("--check", action="store_true", help="только проверить актуальность .tasks")
    args = parser.parse_args()
    try:
        differences = sync(args.root.resolve(), check=args.check)
    except (OSError, BacklogError) as error:
        print(f"Ошибка: {error}")
        return 1
    if args.check and differences:
        print(".tasks не синхронизирован: " + ", ".join(differences))
        return 1
    print(".tasks актуален" if not differences else "Обновлено: " + ", ".join(differences))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
