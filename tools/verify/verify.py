"""Детерминированный гейт методологии для локального запуска и CI."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


POLICY_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_BY_TYPE = {
    "methodology": (
        "AGENTS.md",
        "README.md",
        "docs/INDEX.md",
        "docs/START.md",
        "docs/WORKFLOW.md",
        "docs/ARCHITECTURE.md",
        "docs/OPERATIONS.md",
        "docs/REFERENCE.md",
        ".methodology.yml",
    ),
    "hub": (
        "AGENTS.md",
        "README.md",
        "BACKLOG.md",
        "COMPOSITION.md",
        "CONVENTIONS.md",
        ".methodology.yml",
        ".github/workflows/verify.yml",
        ".evidence/README.md",
        "docker-compose.yml",
    ),
    "service": (
        "AGENTS.md",
        "README.md",
        "docs/ARCHITECTURE.md",
        "Dockerfile",
        ".methodology.yml",
        ".github/workflows/verify.yml",
        ".evidence/README.md",
        "docker-compose.yml",
    ),
    "interface": (
        "AGENTS.md",
        "README.md",
        "docs/ARCHITECTURE.md",
        ".methodology.yml",
        ".github/workflows/verify.yml",
        ".evidence/README.md",
    ),
    "standalone": (
        "AGENTS.md",
        "README.md",
        "docs/ARCHITECTURE.md",
        ".methodology.yml",
        ".github/workflows/verify.yml",
        ".evidence/README.md",
    ),
}
SUPPORTED_TYPES = frozenset(REQUIRED_BY_TYPE)
EXACT_REF_PATTERN = re.compile(r"^(?:[0-9a-f]{7,40}|v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?)$")
CONFIG_LINE_PATTERN = re.compile(r"^([a-z_]+):\s*(\S+)\s*$")
CONFIG_KEYS = frozenset({"schema_version", "repository_type", "methodology_ref"})
SKELETON_REQUIRED = {
    kind: required for kind, required in REQUIRED_BY_TYPE.items() if kind != "methodology"
}
FORBIDDEN_SCRIPT_SUFFIXES = {".sh", ".ps1"}
FORBIDDEN_SKELETON_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".py", ".rs", ".ts", ".tsx"
}
FORBIDDEN_LOCK_NAMES = {
    "Cargo.lock", "Gemfile.lock", "package-lock.json", "pnpm-lock.yaml", "poetry.lock", "uv.lock", "yarn.lock"
}
FORBIDDEN_METHODOLOGY_ARTIFACTS = (
    "ARCHITECTURE.md",
    "BACKLOG.md",
    "COMPOSITION.md",
    "CONVENTIONS.md",
    "Dockerfile",
    "docker-compose.yml",
)
LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)]+)")
TASK_PATTERN = re.compile(
    r"^### (TASK-[0-9]{4,})\. (?:\[ \] (ready|needs-input|blocked-external|automation-failed|retry-exhausted)|\[x\]) — .+$"
)
LEGACY_DOC_PATTERN = re.compile(r"docs/(?:guide|refs)/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=POLICY_ROOT,
        help="корень проверяемого репозитория (по умолчанию — репозиторий методологии)",
    )
    parser.add_argument("--report", type=Path, help="путь для JSON-отчёта")
    parser.add_argument(
        "--methodology-ref",
        help="точный ref методологии, фактически загруженный CI",
    )
    return parser.parse_args()


def methodology_config(root: Path) -> tuple[dict[str, str], list[str]]:
    config = root / ".methodology.yml"
    if not config.is_file():
        return {}, ["отсутствует .methodology.yml"]
    values: dict[str, str] = {}
    errors = []
    for number, raw_line in enumerate(config.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = CONFIG_LINE_PATTERN.fullmatch(line)
        if not match:
            errors.append(f"строка {number}: ожидается key: value")
            continue
        key, value = match.groups()
        if key not in CONFIG_KEYS:
            errors.append(f"строка {number}: неизвестное поле {key}")
        elif key in values:
            errors.append(f"строка {number}: повтор поля {key}")
        else:
            values[key] = value
    missing = CONFIG_KEYS - values.keys()
    if missing:
        errors.append("нет полей: " + ", ".join(sorted(missing)))
    return values, errors


def result(check_id: str, passed: bool, message: str, location: str) -> dict[str, str]:
    return {
        "id": check_id,
        "status": "passed" if passed else "failed",
        "message": message,
        "location": location,
    }


def markdown_files(root: Path):
    ignored_trees = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "build",
        "dist",
        "node_modules",
        "target",
        "vendor",
    }
    for path in root.rglob("*.md"):
        if not ignored_trees.intersection(path.relative_to(root).parts):
            yield path


def broken_markdown_links(root: Path) -> list[str]:
    broken = []
    for markdown in markdown_files(root):
        for match in LINK_PATTERN.finditer(markdown.read_text(encoding="utf-8")):
            target = match.group(1).split("#", 1)[0].strip("<>")
            if not target or re.match(r"^(https?://|mailto:|<)", target):
                continue
            candidate = markdown.parent / unquote(target)
            if not candidate.exists():
                broken.append(f"{markdown}: {target}")
    return broken


def schema_errors(document: object, name: str) -> list[str]:
    if not isinstance(document, dict):
        return [f"{name}: корень схемы не является object"]
    errors = []
    if document.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append(f"{name}: требуется JSON Schema draft 2020-12")
    if document.get("type") != "object":
        errors.append(f"{name}: корневой type должен быть object")
    properties = document.get("properties")
    if not isinstance(properties, dict):
        errors.append(f"{name}: отсутствует object properties")
        properties = {}
    required = document.get("required", [])
    if not isinstance(required, list) or any(item not in properties for item in required):
        errors.append(f"{name}: required должен ссылаться только на properties")
    if document.get("additionalProperties") is not False:
        errors.append(f"{name}: корень должен запрещать additionalProperties")
    definitions = document.get("$defs", {})
    for ref in re.findall(r'"\$ref"\s*:\s*"([^"]+)"', json.dumps(document)):
        if not ref.startswith("#/$defs/") or ref.removeprefix("#/$defs/") not in definitions:
            errors.append(f"{name}: неразрешимая локальная ссылка {ref}")
    return errors


def forbidden_artifacts(root: Path, kind: str) -> list[str]:
    violations = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        relative = path.relative_to(root)
        if kind == "methodology" and path.suffix.lower() in FORBIDDEN_SCRIPT_SUFFIXES:
            violations.append(str(relative))
        if kind == "methodology" and "skeletons" in relative.parts:
            if path.name in FORBIDDEN_LOCK_NAMES or path.suffix.lower() in FORBIDDEN_SKELETON_SUFFIXES:
                violations.append(str(relative))
    return sorted(set(violations))


def skeleton_errors(root: Path) -> list[str]:
    errors = []
    for kind, required in SKELETON_REQUIRED.items():
        directory = "stub" if kind == "standalone" else kind
        skeleton = root / "skeletons" / directory
        for item in required:
            if not (skeleton / item).exists():
                errors.append(f"skeletons/{directory}/{item}")
        config, config_errors = methodology_config(skeleton)
        if config_errors:
            errors.extend(f"skeletons/{directory}/.methodology.yml: {error}" for error in config_errors)
        if config.get("schema_version") != "1" or config.get("repository_type") != kind:
            errors.append(f"skeletons/{directory}/.methodology.yml: неверные schema_version/repository_type")
        if config.get("methodology_ref") != "<tag-or-commit>":
            errors.append(f"skeletons/{directory}/.methodology.yml: требуется <tag-or-commit>")
    return errors


def backlog_errors(backlog_text: str) -> list[str]:
    errors = []
    headings = re.findall(r"^### TASK-.*$", backlog_text, re.MULTILINE)
    seen = set()
    for heading in headings:
        match = TASK_PATTERN.fullmatch(heading)
        if not match:
            errors.append(f"некорректный заголовок: {heading}")
            continue
        task_id = match.group(1)
        if task_id in seen:
            errors.append(f"повтор task ID: {task_id}")
        seen.add(task_id)
    if not headings:
        errors.append("нет ни одной задачи TASK-NNNN")
    for block in re.split(r"(?=^### TASK-)", backlog_text, flags=re.MULTILINE)[1:]:
        heading = block.splitlines()[0]
        if TASK_PATTERN.fullmatch(heading):
            for field in ("Цель:", "Готово, когда:", "Не входит:"):
                if field not in block:
                    errors.append(f"{heading}: отсутствует поле «{field}»")
    return errors


def run(root: Path, ci_methodology_ref: str | None = None) -> dict[str, object]:
    checks: list[dict[str, str]] = []
    config, config_errors = methodology_config(root)
    kind = config.get("repository_type", "invalid")

    config_valid = not config_errors and config.get("schema_version") == "1" and kind in SUPPORTED_TYPES
    config_message = "Конфигурация методологии соответствует schema version 1"
    if not config_valid:
        details = config_errors[:]
        if config.get("schema_version") != "1":
            details.append("schema_version должен быть 1")
        if kind not in SUPPORTED_TYPES:
            details.append(f"неподдерживаемый repository_type: {kind}")
        config_message = "; ".join(details)
    checks.append(result("VER-001", config_valid, config_message, ".methodology.yml"))

    required = REQUIRED_BY_TYPE.get(kind, ())
    for item in required:
        checks.append(result("VER-001", (root / item).exists(), f"Обязательный файл: {item}", item))

    pinned_ref = config.get("methodology_ref")
    valid_ref = pinned_ref == "self" if kind == "methodology" else bool(
        pinned_ref and EXACT_REF_PATTERN.fullmatch(pinned_ref)
    )
    if ci_methodology_ref is not None and kind != "methodology":
        valid_ref = valid_ref and pinned_ref == ci_methodology_ref
    ref_message = "Версия методологии закреплена точным ref"
    if ci_methodology_ref is not None and pinned_ref != ci_methodology_ref:
        ref_message = f"methodology_ref={pinned_ref} не совпадает с CI ref={ci_methodology_ref}"
    checks.append(
        result(
            "VER-003",
            valid_ref,
            ref_message,
            ".methodology.yml",
        )
    )

    if kind == "methodology":
        for item in FORBIDDEN_METHODOLOGY_ARTIFACTS:
            checks.append(
                result(
                    "VER-002",
                    not (root / item).exists(),
                    f"Запрещённый корневой артефакт: {item}",
                    item,
                )
            )

    broken_links = broken_markdown_links(root)
    links_message = "Markdown-ссылки разрешаются"
    if broken_links:
        links_message = "Висячие ссылки: " + "; ".join(broken_links)
    checks.append(result("VER-010", not broken_links, links_message, "*.md"))

    legacy_references = []
    for markdown in markdown_files(root):
        if LEGACY_DOC_PATTERN.search(markdown.read_text(encoding="utf-8")):
            legacy_references.append(str(markdown.relative_to(root)))
    checks.append(
        result(
            "VER-004",
            not legacy_references,
            "Нет ссылок на удалённые docs/guide и docs/refs"
            if not legacy_references
            else "Устаревшие ссылки: " + ", ".join(legacy_references),
            "*.md",
        )
    )

    invalid_json = []
    for schema in (POLICY_ROOT / "schemas").glob("*.json"):
        try:
            document = json.loads(schema.read_text(encoding="utf-8"))
            invalid_json.extend(schema_errors(document, schema.name))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            invalid_json.append(f"{schema.name}: {error}")
    json_message = "JSON-схемы структурно валидны и их локальные ссылки разрешаются"
    if invalid_json:
        json_message = "Невалидные JSON-схемы: " + "; ".join(invalid_json)
    checks.append(result("VER-011", not invalid_json, json_message, "schemas/"))

    forbidden = forbidden_artifacts(root, kind)
    checks.append(
        result(
            "VER-007",
            not forbidden,
            "Нет запрещённых артефактов методологии и кода/lock-файлов в skeletons"
            if not forbidden
            else "Запрещённые артефакты: " + ", ".join(forbidden),
            "**/*",
        )
    )

    if kind == "methodology":
        structural_errors = skeleton_errors(root)
        checks.append(
            result(
                "VER-008",
                not structural_errors,
                "Все скелеты имеют обязательную структуру и согласованную конфигурацию"
                if not structural_errors
                else "Ошибки скелетов: " + "; ".join(structural_errors),
                "skeletons/",
            )
        )

    if kind in {"hub", "methodology"}:
        backlog = root / "BACKLOG.md" if kind == "hub" else root / "skeletons/hub/BACKLOG.md"
        backlog_text = backlog.read_text(encoding="utf-8") if backlog.is_file() else ""
        backlog_location = "BACKLOG.md" if kind == "hub" else "skeletons/hub/BACKLOG.md"
        legacy_in_flight = len(re.findall(r"^### .*\[~\]", backlog_text, re.MULTILINE))
        checks.append(
            result(
                "VER-005",
                legacy_in_flight == 0,
                "В backlog нет устаревшего статуса [~]",
                backlog_location,
            )
        )
        malformed_tasks = backlog_errors(backlog_text)
        checks.append(
            result(
                "VER-006",
                not malformed_tasks,
                "Задачи содержат уникальный TASK-NNNN, допустимый статус и обязательные поля"
                if not malformed_tasks
                else "Некорректные задачи: " + "; ".join(malformed_tasks),
                backlog_location,
            )
        )

    failed = any(check["status"] == "failed" for check in checks)
    return {"status": "failed" if failed else "passed", "repository_type": kind, "checks": checks}


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    report = run(root, args.methodology_ref)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(output)
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
