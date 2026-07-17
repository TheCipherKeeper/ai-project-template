"""Детерминированный гейт методологии для локального запуска и CI."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tomllib
from datetime import datetime
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
        "tools/review/review.py",
        "tools/review/.env.example",
    ),
    "hub": (
        "AGENTS.md",
        "README.md",
        "BACKLOG.md",
        "COMPOSITION.md",
        "CONVENTIONS.md",
        ".methodology.yml",
        ".pipeline.json",
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
        ".pipeline.json",
        ".github/workflows/verify.yml",
        "docker-compose.yml",
    ),
    "interface": (
        "AGENTS.md",
        "README.md",
        "docs/ARCHITECTURE.md",
        ".methodology.yml",
        ".pipeline.json",
        ".github/workflows/verify.yml",
    ),
    "standalone": (
        "AGENTS.md",
        "README.md",
        "docs/ARCHITECTURE.md",
        ".methodology.yml",
        ".pipeline.json",
        ".github/workflows/verify.yml",
    ),
}
SUPPORTED_TYPES = frozenset(REQUIRED_BY_TYPE)
EXACT_REF_PATTERN = re.compile(r"^(?:[0-9a-f]{7,40}|v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?)$")
CONFIG_LINE_PATTERN = re.compile(r"^([a-z_]+):\s*(\S+)\s*$")
BASE_CONFIG_KEYS = frozenset({"schema_version", "repository_type", "methodology_ref"})
SERVICE_CONFIG_KEYS = frozenset({"service_name", "service_language", "service_modules"})
CONFIG_KEYS = BASE_CONFIG_KEYS | SERVICE_CONFIG_KEYS
SERVICE_LANGUAGES = frozenset({"python", "go", "rust"})
SERVICE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
SKELETON_REQUIRED = {
    kind: required for kind, required in REQUIRED_BY_TYPE.items() if kind != "methodology"
}
SHARED_SKELETON_FILES = (
    ".github/workflows/verify.yml",
)
PIPELINE_NEEDS = {
    "lint": "policy",
    "tests": "lint",
    "review": "tests",
    "build": "review",
    "artifact": "build",
    "merge": "artifact",
    "deploy": "merge",
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
NON_MERMAID_DIAGRAM_LANGUAGES = frozenset({
    "d2", "dot", "graphviz", "nomnoml", "plantuml", "puml", "uml", "vega", "vega-lite"
})
TEXT_DIAGRAM_PATTERN = re.compile(
    r"(?:-{1,2}>|<-{1,2}|[→←↔]|[┌┐└┘├┤┬┴┼│]|^\s*\+[-=]{2,}(?:\+|\s))",
    re.MULTILINE,
)
INLINE_TEXT_DIAGRAM_PATTERN = re.compile(
    r"^[ \t]*(?:[`\[]?[A-Za-zА-Яа-яЁё0-9_.:/-]+[`\]]?)[ \t]+(?:-{1,2}>|<-{1,2})[ \t]+\S+[ \t]*$"
    r"|[┌┐└┘├┤┬┴┼│]",
    re.MULTILINE,
)
RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


TASK_HEADING = re.compile(
    r"^### (TASK-[0-9]{4,})\. (?:(\[x\])|(\[ \] (ready|needs-input|blocked-external|automation-failed|retry-exhausted))) — .+$"
)
TASK_SCALAR_FIELDS = {
    "Цель": "goal",
    "Целевой репозиторий": "target",
    "Риск": "risk",
    "Автономность": "autonomy",
    "Откат": "rollback",
}
TASK_LIST_FIELDS = {
    "Готово, когда": "acceptance_criteria",
    "Не входит": "out_of_scope",
    "Триггеры": "triggers",
}
TASK_ALLOWED_VALUES = {
    "risk": {"low", "medium", "high", "critical"},
    "autonomy": {"auto-test-deploy", "human-before-production", "human-before-merge"},
    "triggers": {"architecture", "contract", "data", "infrastructure", "security"},
}
TASK_DIAGNOSTIC_STATUSES = {"needs-input", "blocked-external", "automation-failed", "retry-exhausted"}
TASK_HIGH_RISK_TRIGGERS = {"contract", "data", "security"}
TASK_AUTONOMY_RANK = {"auto-test-deploy": 0, "human-before-production": 1, "human-before-merge": 2}


class BacklogError(ValueError):
    """BACKLOG нельзя однозначно разобрать на задачи."""


def _backlog_field(block: str, label: str) -> str | None:
    labels = "|".join(re.escape(name) for name in (*TASK_SCALAR_FIELDS, *TASK_LIST_FIELDS, "Диагностика"))
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
        for label in (*TASK_SCALAR_FIELDS, *TASK_LIST_FIELDS, "Диагностика"):
            if len(re.findall(rf"^{re.escape(label)}:", block, re.MULTILINE)) > 1:
                raise BacklogError(f"{task_id}: поле «{label}» указано несколько раз")
        status = str(record["status"])
        diagnostic = _backlog_field(block, "Диагностика")
        first_content = next((line.strip() for line in block.splitlines()[1:] if line.strip()), "")
        if status in TASK_DIAGNOSTIC_STATUSES:
            if not diagnostic:
                raise BacklogError(f"{task_id}: диагностический статус требует поле «Диагностика»")
            if (
                not first_content.startswith("Диагностика:")
                or not first_content.removeprefix("Диагностика:").strip()
            ):
                raise BacklogError(f"{task_id}: поле «Диагностика» должно идти сразу после заголовка")
            record["diagnostic"] = " ".join(diagnostic.splitlines())
        for label, key in TASK_SCALAR_FIELDS.items():
            value = _backlog_field(block, label)
            if value:
                record[key] = " ".join(value.splitlines())
            elif key != "rollback":
                raise BacklogError(f"{task_id}: отсутствует поле «{label}»")
        for label, key in TASK_LIST_FIELDS.items():
            value = _backlog_field(block, label)
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
        for key, allowed in TASK_ALLOWED_VALUES.items():
            values = record[key] if isinstance(record[key], list) else [record[key]]
            invalid = [value for value in values if value not in allowed]
            if invalid:
                raise BacklogError(f"{task_id}: недопустимое значение {key}: {invalid[0]}")
        triggers = set(record["triggers"])
        risk = str(record["risk"])
        autonomy = str(record["autonomy"])
        if triggers & TASK_HIGH_RISK_TRIGGERS and risk not in {"high", "critical"}:
            raise BacklogError(
                f"{task_id}: триггеры contract, data и security требуют риск high или critical"
            )
        minimum_autonomy = 1 if risk in {"high", "critical"} else 0
        if TASK_AUTONOMY_RANK[autonomy] < minimum_autonomy:
            raise BacklogError(f"{task_id}: автономность слишком широка для риска {risk}")
        records[task_id] = record
    if not records:
        raise BacklogError("нет ни одной задачи TASK-NNNN")
    return records


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
    parser.add_argument("--commit", help="commit, для которого создан evidence")
    parser.add_argument(
        "--finalization-base",
        help="base SHA служебного PR task-finalization; включает проверку состава diff",
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
    missing = BASE_CONFIG_KEYS - values.keys()
    if missing:
        errors.append("нет полей: " + ", ".join(sorted(missing)))
    kind = values.get("repository_type")
    service_fields = SERVICE_CONFIG_KEYS & values.keys()
    if kind == "service":
        missing_service = SERVICE_CONFIG_KEYS - values.keys()
        if missing_service:
            errors.append("для service нет полей: " + ", ".join(sorted(missing_service)))
    elif service_fields:
        errors.append("поля service допустимы только для repository_type=service")
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
    for path in sorted(root.rglob("*.md")):
        if path.is_file() and not ignored_trees.intersection(path.relative_to(root).parts):
            yield path


def fenced_blocks(text: str):
    """Выделить ограждённые блоки CommonMark с их языком, телом и строкой."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        opening = re.match(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$", lines[index])
        if not opening:
            index += 1
            continue
        fence = opening.group("fence")
        marker = fence[0]
        language = opening.group("info").strip().split(maxsplit=1)[0].lower() if opening.group("info").strip() else ""
        start = index
        index += 1
        body = []
        closing = re.compile(rf"^ {{0,3}}{re.escape(marker)}{{{len(fence)},}}\s*$")
        while index < len(lines) and not closing.match(lines[index]):
            body.append(lines[index])
            index += 1
        if index < len(lines):
            yield start + 1, language, "\n".join(body)
            index += 1


def non_mermaid_diagrams(root: Path) -> list[str]:
    """Найти диаграммы Markdown, оформленные не блоками Mermaid."""
    violations = []
    for markdown in markdown_files(root):
        try:
            text = markdown.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            violations.append(f"{markdown.relative_to(root)}: невозможно прочитать: {error}")
            continue
        fenced_lines: set[int] = set()
        for line, language, body in fenced_blocks(text):
            body_lines = len(body.splitlines())
            fenced_lines.update(range(line, line + body_lines + 2))
            is_other_diagram_language = language in NON_MERMAID_DIAGRAM_LANGUAGES
            is_text_diagram = language in {"", "text"} and TEXT_DIAGRAM_PATTERN.search(body)
            if is_other_diagram_language or is_text_diagram:
                violations.append(f"{markdown.relative_to(root)}:{line}")
        outside = "\n".join(
            line if number not in fenced_lines else ""
            for number, line in enumerate(text.splitlines(), 1)
        )
        match = INLINE_TEXT_DIAGRAM_PATTERN.search(outside)
        if match:
            line = outside.count("\n", 0, match.start()) + 1
            violations.append(f"{markdown.relative_to(root)}:{line}")
    return violations


def broken_markdown_links(root: Path) -> list[str]:
    broken = []
    for markdown in markdown_files(root):
        try:
            text = markdown.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            broken.append(f"{markdown.relative_to(root)}: невозможно прочитать: {error}")
            continue
        for match in LINK_PATTERN.finditer(text):
            target = match.group(1).split("#", 1)[0].strip("<>")
            if not target or re.match(r"^(https?://|mailto:|<)", target):
                continue
            candidate = markdown.parent / unquote(target)
            if not candidate.exists():
                broken.append(f"{markdown.relative_to(root)}: {target}")
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


def resolve_ref(schema: dict[str, object], root_schema: dict[str, object]) -> dict[str, object]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    current: object = root_schema
    for part in ref.removeprefix("#/").split("/"):
        current = current[part] if isinstance(current, dict) else None
    return current if isinstance(current, dict) else {}


def validate_json(instance: object, schema: dict[str, object], root_schema=None, path="$ ") -> list[str]:
    """Проверить используемое методологией подмножество JSON Schema 2020-12."""
    root_schema = root_schema or schema
    schema = resolve_ref(schema, root_schema)
    errors: list[str] = []
    expected = schema.get("type")
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
    }
    if expected in type_map and (not isinstance(instance, type_map[expected]) or expected == "integer" and isinstance(instance, bool)):
        return [f"{path.strip()}: ожидается {expected}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path.strip()}: ожидается {schema['const']!r}")
    if isinstance(schema.get("enum"), list) and instance not in schema["enum"]:
        errors.append(f"{path.strip()}: недопустимое значение {instance!r}")
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required if isinstance(required, list) else []:
            if key not in instance:
                errors.append(f"{path}{key}: обязательное поле отсутствует")
        if schema.get("additionalProperties") is False and isinstance(properties, dict):
            for key in instance.keys() - properties.keys():
                errors.append(f"{path}{key}: неизвестное поле")
        if isinstance(properties, dict):
            for key, value in instance.items():
                child = properties.get(key)
                if isinstance(child, dict):
                    errors.extend(validate_json(value, child, root_schema, f"{path}{key}."))
    if isinstance(instance, list):
        if isinstance(schema.get("minItems"), int) and len(instance) < schema["minItems"]:
            errors.append(f"{path.strip()}: недостаточно элементов")
        if schema.get("uniqueItems") is True and len({json.dumps(x, sort_keys=True) for x in instance}) != len(instance):
            errors.append(f"{path.strip()}: элементы должны быть уникальны")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, value in enumerate(instance):
                errors.extend(validate_json(value, item_schema, root_schema, f"{path}{index}."))
    if isinstance(instance, str):
        if isinstance(schema.get("minLength"), int) and len(instance) < schema["minLength"]:
            errors.append(f"{path.strip()}: строка слишком короткая")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.fullmatch(pattern, instance):
            errors.append(f"{path.strip()}: значение не соответствует pattern")
        if schema.get("format") == "date-time":
            try:
                if not RFC3339_PATTERN.fullmatch(instance):
                    raise ValueError
                parsed = datetime.fromisoformat(instance.replace("Z", "+00:00"))
                if parsed.utcoffset() is None:
                    raise ValueError
            except (ValueError, OverflowError):
                errors.append(f"{path.strip()}: ожидается date-time")
    if isinstance(instance, int) and not isinstance(instance, bool):
        if isinstance(schema.get("minimum"), int) and instance < schema["minimum"]:
            errors.append(f"{path.strip()}: значение меньше minimum")
        if isinstance(schema.get("maximum"), int) and instance > schema["maximum"]:
            errors.append(f"{path.strip()}: значение больше maximum")
    if isinstance(schema.get("not"), dict) and not validate_json(instance, schema["not"], root_schema, path):
        errors.append(f"{path.strip()}: запрещённое значение")
    for condition in schema.get("allOf", []) if isinstance(schema.get("allOf"), list) else []:
        if not isinstance(condition, dict):
            continue
        if "if" not in condition:
            errors.extend(validate_json(instance, condition, root_schema, path))
            continue
        selector = condition.get("if", {}).get("properties", {})
        matches = isinstance(instance, dict) and all(
            key in instance and not validate_json(instance[key], value, root_schema, path)
            for key, value in selector.items()
        )
        branch = condition.get("then" if matches else "else")
        if isinstance(branch, dict):
            errors.extend(validate_json(instance, branch, root_schema, path))
    return errors


def load_records(directory: Path, schema_name: str) -> tuple[dict[str, dict[str, object]], list[str]]:
    records: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    schema = json.loads((POLICY_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    if not directory.is_dir():
        return records, [f"отсутствует каталог {directory.name}"]
    for path in sorted(directory.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append(f"{path.name}: {error}")
            continue
        validation = validate_json(document, schema)
        errors.extend(f"{path.name}: {error}" for error in validation)
        if isinstance(document, dict):
            key = document.get("id") or document.get("task_id")
            if isinstance(key, str):
                if path.stem != key:
                    errors.append(f"{path.name}: имя файла должно быть {key}.json")
                if key in records:
                    errors.append(f"{path.name}: повтор записи {key}")
                records[key] = document
    return records, errors


def commit_matches_head(root: Path, commit: object) -> bool:
    """Проверить точное соответствие переданного CI-коммита текущему HEAD."""
    if not isinstance(commit, str):
        return False
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0 and completed.stdout.strip() == commit


def _task_status_in_backlog(backlog_text: str, task_id: str) -> str | None:
    pattern = re.compile(
        rf"^### {re.escape(task_id)}\. (?:\[ \] (ready|needs-input|blocked-external|automation-failed|retry-exhausted)|\[x\]) — .+$",
        re.MULTILINE,
    )
    match = pattern.search(backlog_text)
    if match is None:
        return None
    return "done" if match.group(1) is None else match.group(1)


def finalization_diff_errors(root: Path, base: str) -> list[str]:
    """Разрешить в финализации только BACKLOG и одно evidence."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-status", f"{base}...HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as error:
        return [f"git diff недоступен: {error}"]
    if completed.returncode != 0:
        return ["не удалось получить diff финализации"]
    changes = {}
    for line in completed.stdout.splitlines():
        parts = line.strip().split("\t")
        if len(parts) != 2:
            return ["финализация содержит переименование или некорректный путь"]
        status, path = parts
        changes[path.replace("\\", "/")] = status
    changed = set(changes)
    evidence_files = {path for path in changed if re.fullmatch(r"\.evidence/TASK-[0-9]{4,}\.json", path)}
    expected = {"BACKLOG.md"} | evidence_files
    errors = []
    if changed != expected:
        errors.append("финализация содержит файлы вне BACKLOG.md и .evidence")
    if len(evidence_files) != 1:
        errors.append("финализация требует ровно одно evidence")
    else:
        evidence_path = next(iter(evidence_files))
        if changes.get("BACKLOG.md") != "M" or changes.get(evidence_path) != "A":
            errors.append("BACKLOG должен изменяться, а evidence — добавляться впервые")
        task_id = Path(evidence_path).stem
        try:
            before = subprocess.run(
                ["git", "-C", str(root), "show", f"{base}:BACKLOG.md"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", check=True,
            )
            after = (root / "BACKLOG.md").read_text(encoding="utf-8")
            evidence = json.loads((root / evidence_path).read_text(encoding="utf-8"))
            before_status = _task_status_in_backlog(before.stdout, task_id)
            after_status = _task_status_in_backlog(after, task_id)
            if before_status is None or before_status == "done" or after_status != "done":
                errors.append("задача должна перейти из незавершённого состояния в done")
            if evidence.get("task_id") != task_id:
                errors.append("evidence должен соответствовать имени TASK-NNNN")
        except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, UnicodeDecodeError):
            errors.append("не удалось проверить переход состояния финализируемой задачи")
    return errors


def forbidden_artifacts(root: Path, kind: str) -> list[str]:
    violations = []
    if kind in {"methodology", "service", "interface", "standalone"} and (root / "adr").exists():
        violations.append("adr/")
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        relative = path.relative_to(root)
        if kind == "methodology" and path.suffix.lower() in FORBIDDEN_SCRIPT_SUFFIXES:
            violations.append(str(relative))
        if kind == "methodology" and "skeletons" in relative.parts:
            skeleton_index = relative.parts.index("skeletons")
            skeleton_relative = relative.parts[skeleton_index + 2 :]
            repository_tool = bool(skeleton_relative and skeleton_relative[0] == "tools")
            forbidden_source = (
                path.suffix.lower() in FORBIDDEN_SKELETON_SUFFIXES
                and not (repository_tool and path.suffix.lower() == ".py")
            )
            if path.name in FORBIDDEN_LOCK_NAMES or forbidden_source:
                violations.append(str(relative))
    return sorted(set(violations))


def pipeline_errors(root: Path, allow_placeholders: bool = False) -> list[str]:
    """Проверить конфигурацию и блокирующий порядок продуктового конвейера."""
    errors: list[str] = []
    config_path = root / ".pipeline.json"
    try:
        document = json.loads(config_path.read_text(encoding="utf-8"))
        schema = json.loads((POLICY_ROOT / "schemas/pipeline.schema.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f".pipeline.json: {error}"]
    errors.extend(f".pipeline.json: {error}" for error in validate_json(document, schema))
    if not allow_placeholders and re.search(r"<[^>]+>", json.dumps(document, ensure_ascii=False)):
        errors.append(".pipeline.json: остались маркеры первичной настройки")

    workflow = root / ".github/workflows/verify.yml"
    try:
        text = workflow.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        errors.append(f".github/workflows/verify.yml: {error}")
        return errors
    for job, dependency in PIPELINE_NEEDS.items():
        pattern = rf"(?ms)^  {job}:\s*$.*?^    needs:\s*{dependency}\s*$"
        if not re.search(pattern, text):
            errors.append(f".github/workflows/verify.yml: {job} должен зависеть от {dependency}")
    for stage in ("lint", "tests", "review", "build", "artifact", "deploy"):
        if f"tools/pipeline/run.py {stage}" not in text:
            errors.append(f".github/workflows/verify.yml: стадия {stage} не вызывает исполнитель")
    if 'gh pr merge "$PR_URL" --squash --delete-branch' not in text:
        errors.append(".github/workflows/verify.yml: merge не выполняет squash-слияние")
    return errors


def skeleton_errors(root: Path) -> list[str]:
    errors = []
    legacy_directory = root / "skeletons" / "stub"
    if legacy_directory.exists():
        errors.append("skeletons/stub: устаревшее имя, используйте skeletons/standalone")
    for kind, required in SKELETON_REQUIRED.items():
        directory = kind
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
        errors.extend(
            f"skeletons/{directory}/{error}"
            for error in pipeline_errors(skeleton, allow_placeholders=True)
        )
        if kind == "service" and (
            config.get("service_name") != "<service>"
            or config.get("service_language") != "<python|go|rust>"
            or config.get("service_modules") != "<module>[,<module>...]"
        ):
            errors.append(f"skeletons/{directory}/.methodology.yml: неверные поля service")
        if kind == "service":
            header, _ = documented_service_table(skeleton)
            expected = [
                "Модуль", "Ответственность", "Спецификация", "Язык",
                "Канонический корень", "Проверка границ",
            ]
            if header != expected:
                errors.append("skeletons/service/docs/ARCHITECTURE.md: неверные столбцы модулей")
        if kind == "standalone" and skeleton.is_dir():
            for path in skeleton.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if re.search(r"\bstub\b|<STUB>", text, re.IGNORECASE):
                    relative_path = path.relative_to(root).as_posix()
                    errors.append(f"{relative_path}: устаревший маркер stub")
    for relative in SHARED_SKELETON_FILES:
        variants = {
            (root / "skeletons" / kind / relative).read_bytes()
            for kind in SKELETON_REQUIRED
            if kind != "hub"
            if (root / "skeletons" / kind / relative).is_file()
        }
        if len(variants) > 1:
            errors.append(f"skeletons/*/{relative}: общая заготовка рассинхронизирована")
    return errors


SERVICE_LAYER_PATHS = (
    ("domain",),
    ("application",),
    ("ports", "inbound"),
    ("ports", "outbound"),
    ("adapters", "inbound"),
    ("adapters", "outbound"),
)
ALLOWED_LAYER_DEPENDENCIES = {
    "domain": {"domain"},
    "ports/inbound": {"domain", "ports/inbound"},
    "ports/outbound": {"domain", "ports/outbound"},
    "application": {"domain", "ports/inbound", "ports/outbound", "application"},
    "adapters/inbound": {"domain", "ports/inbound", "adapters/inbound"},
    "adapters/outbound": {"domain", "ports/outbound", "adapters/outbound"},
}


def service_modules(config: dict[str, str]) -> tuple[list[str], list[str]]:
    raw = config.get("service_modules", "")
    modules = raw.split(",") if raw else []
    errors = []
    if not modules or any(not SERVICE_NAME_PATTERN.fullmatch(module) for module in modules):
        errors.append("service_modules: требуется список уникальных имён через запятую без пробелов")
    if len(modules) != len(set(modules)):
        errors.append("service_modules: имена модулей должны быть уникальны")
    return modules, errors


def documented_service_table(root: Path) -> tuple[list[str], list[list[str]]]:
    architecture = root / "docs" / "ARCHITECTURE.md"
    if not architecture.is_file():
        return [], []
    match = re.search(
        r"(?ms)^## Модули\s+(.*?)(?=^##\s|\Z)",
        architecture.read_text(encoding="utf-8"),
    )
    if not match:
        return [], []
    rows = []
    for line in match.group(1).splitlines():
        if not line.startswith("|") or re.fullmatch(r"[|:\-\s]+", line):
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return (rows[0], rows[1:]) if rows else ([], [])


def canonical_service_paths(root: Path, config: dict[str, str], module: str) -> tuple[Path, Path]:
    language = config.get("service_language")
    service_name = config.get("service_name", "")
    if language == "python":
        return root / "src" / service_name / module, root / "src" / service_name / "bootstrap.py"
    if language == "go":
        return root / "internal" / module, root / "cmd" / service_name / "main.go"
    return root / "src" / module, root / "src" / "main.rs"


def layer_from_parts(parts: tuple[str, ...]) -> str | None:
    if not parts:
        return None
    if parts[0] in {"domain", "application"}:
        return parts[0]
    if len(parts) >= 2 and parts[0] in {"ports", "adapters"} and parts[1] in {"inbound", "outbound"}:
        return "/".join(parts[:2])
    return None


def dependency_error(source_module: str, source_layer: str, target_module: str, target_layer: str) -> str | None:
    if source_module != target_module:
        if target_layer != "ports/inbound":
            return f"{source_module}/{source_layer} обращается к внутреннему слою {target_module}/{target_layer}"
        return None
    if target_layer not in ALLOWED_LAYER_DEPENDENCIES[source_layer]:
        return f"{source_module}/{source_layer} зависит от запрещённого слоя {target_layer}"
    return None


def python_import_errors(root: Path, service_name: str, modules: list[str]) -> list[str]:
    errors = []
    package_root = root / "src" / service_name
    for module in modules:
        module_root = package_root / module
        for source in module_root.rglob("*.py") if module_root.is_dir() else ():
            relative = source.relative_to(package_root)
            source_layer = layer_from_parts(relative.parts[1:-1])
            if source_layer is None:
                allowed_init = relative.as_posix() in {
                    f"{module}/__init__.py",
                    f"{module}/ports/__init__.py",
                    f"{module}/adapters/__init__.py",
                }
                if allowed_init:
                    try:
                        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
                        if all(
                            isinstance(node, ast.Expr)
                            and isinstance(node.value, ast.Constant)
                            and isinstance(node.value.value, str)
                            for node in tree.body
                        ):
                            continue
                    except (SyntaxError, UnicodeDecodeError):
                        pass
                errors.append(f"{source.relative_to(root)}: Python-код вне канонического слоя")
                continue
            try:
                tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            except (SyntaxError, UnicodeDecodeError) as error:
                errors.append(f"{source.relative_to(root)}: невозможно разобрать imports: {error}")
                continue
            package = [service_name, *relative.parts[:-1]]
            for node in ast.walk(tree):
                targets = []
                if isinstance(node, ast.Import):
                    targets = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        base = package[: len(package) - node.level + 1]
                        target = ".".join([*base, *(node.module or "").split(".")])
                    else:
                        target = node.module or ""
                    targets = [target, *(f"{target}.{alias.name}" for alias in node.names if alias.name != "*")]
                for target in targets:
                    parts = tuple(part for part in target.split(".") if part)
                    if not source_layer.startswith("adapters/") and parts and parts[0] != service_name and parts[0] not in sys.stdlib_module_names:
                        errors.append(f"{source.relative_to(root)}:{node.lineno}: внутренний слой импортирует внешнюю библиотеку {parts[0]}")
                    if len(parts) < 3 or parts[0] != service_name or parts[1] not in modules:
                        continue
                    target_layer = layer_from_parts(parts[2:])
                    if target_layer and (error := dependency_error(module, source_layer, parts[1], target_layer)):
                        errors.append(f"{source.relative_to(root)}:{node.lineno}: {error}")
    return errors


def go_import_errors(root: Path, modules: list[str]) -> list[str]:
    errors = []
    go_mod = root / "go.mod"
    module_path = ""
    if go_mod.is_file():
        match = re.search(r"(?m)^module\s+(\S+)", go_mod.read_text(encoding="utf-8"))
        module_path = match.group(1) if match else ""
    if not module_path:
        return ["go.mod: отсутствует module path"]
    go_mod_text = go_mod.read_text(encoding="utf-8")
    required_modules = set(re.findall(
        r"(?m)^\s*(?:require\s+)?([A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)\s+v\S+",
        go_mod_text,
    ))
    for module in modules:
        module_root = root / "internal" / module
        for source in module_root.rglob("*.go") if module_root.is_dir() else ():
            relative = source.relative_to(module_root)
            source_layer = layer_from_parts(relative.parts[:-1])
            if source_layer is None:
                errors.append(f"{source.relative_to(root)}: Go-код вне канонического слоя")
                continue
            text = source.read_text(encoding="utf-8")
            text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)
            imports = re.findall(r'(?m)^\s*import\s+(?:[\w.]+\s+)?["`]([^"`\n]+)["`]', text)
            for block in re.findall(r"(?ms)^\s*import\s*\((.*?)\)", text):
                imports.extend(re.findall(r'["`]([^"`\n]+)["`]', block))
            for target in imports:
                prefix = f"{module_path}/internal/"
                external = "." in target.split("/", 1)[0] or any(
                    target == dependency or target.startswith(f"{dependency}/")
                    for dependency in required_modules
                )
                if not source_layer.startswith("adapters/") and external and not target.startswith(prefix):
                    errors.append(f"{source.relative_to(root)}: внутренний слой импортирует внешнюю библиотеку {target}")
                if not target.startswith(prefix):
                    continue
                parts = tuple(target.removeprefix(prefix).split("/"))
                if len(parts) < 2 or parts[0] not in modules:
                    continue
                target_layer = layer_from_parts(parts[1:])
                if target_layer and (error := dependency_error(module, source_layer, parts[0], target_layer)):
                    errors.append(f"{source.relative_to(root)}: {error}")
    return errors


def strip_rust_noncode(text: str) -> str:
    """Убрать строки и вложенные комментарии Rust, сохранив строки и позиции."""
    output = list(text)
    index = 0

    def erase(start: int, end: int) -> None:
        for position in range(start, end):
            if output[position] != "\n":
                output[position] = " "

    while index < len(text):
        if text.startswith("//", index):
            end = text.find("\n", index)
            end = len(text) if end == -1 else end
            erase(index, end)
            index = end
            continue
        if text.startswith("/*", index):
            start = index
            depth = 1
            index += 2
            while index < len(text) and depth:
                if text.startswith("/*", index):
                    depth += 1
                    index += 2
                elif text.startswith("*/", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            erase(start, index)
            continue
        raw = re.match(r'r(#{0,255})"', text[index:])
        if raw:
            start = index
            terminator = '"' + raw.group(1)
            content_start = index + raw.end()
            end = text.find(terminator, content_start)
            index = len(text) if end == -1 else end + len(terminator)
            erase(start, index)
            continue
        if text[index] == '"':
            start = index
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                elif text[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            erase(start, min(index, len(text)))
            continue
        character = re.match(r"'(?:\\.|[^'\\\n])'", text[index:])
        if character:
            end = index + character.end()
            erase(index, end)
            index = end
            continue
        index += 1
    return "".join(output)


def rust_import_errors(root: Path, modules: list[str]) -> list[str]:
    errors = []
    manifest = root / "Cargo.toml"
    if not manifest.is_file():
        return ["Cargo.toml: файл обязателен для Rust-сервиса"]
    try:
        cargo = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        return [f"Cargo.toml: невозможно разобрать зависимости: {error}"]
    dependencies = {
        name.replace("-", "_")
        for section in ("dependencies", "dev-dependencies", "build-dependencies")
        for name in cargo.get(section, {})
    }
    for target in cargo.get("target", {}).values():
        if isinstance(target, dict):
            dependencies.update(
                name.replace("-", "_")
                for section in ("dependencies", "dev-dependencies", "build-dependencies")
                for name in target.get(section, {})
            )
    for module in modules:
        module_root = root / "src" / module
        for source in module_root.rglob("*.rs") if module_root.is_dir() else ():
            relative = source.relative_to(module_root)
            source_layer = layer_from_parts(relative.parts[:-1])
            if source_layer is None:
                if relative.as_posix() in {"mod.rs", "ports/mod.rs", "adapters/mod.rs"}:
                    continue
                errors.append(f"{source.relative_to(root)}: Rust-код вне канонического слоя")
                continue
            text = strip_rust_noncode(source.read_text(encoding="utf-8"))
            imports = []
            for match in re.finditer(r"(?m)^\s*(?:pub\s+)?use\s+([^;]+);", text):
                expression = match.group(1).strip()
                line_number = text.count("\n", 0, match.start()) + 1
                if "{" in expression:
                    prefix, body = expression.split("{", 1)
                    if "{" in body or not body.endswith("}"):
                        errors.append(f"{source.relative_to(root)}:{line_number}: вложенный групповой use запрещён")
                        continue
                    prefix = prefix.rstrip(":")
                    imports.extend(
                        (f"{prefix}::{item.strip()}" if prefix else item.strip(), line_number)
                        for item in body[:-1].split(",")
                        if item.strip() and item.strip() != "self"
                    )
                else:
                    imports.append((expression.split(" as ", 1)[0].strip(), line_number))
            for target, line_number in imports:
                first = target.split("::", 1)[0]
                if not source_layer.startswith("adapters/") and first in dependencies:
                    errors.append(f"{source.relative_to(root)}:{line_number}: внутренний слой импортирует внешний crate {first}")
                tokens = target.split("::")
                if tokens[0] == "crate":
                    parts = tuple(tokens[1:])
                elif tokens[0] in {"self", "super"}:
                    resolved = [module, *relative.parts[:-1]]
                    while tokens and tokens[0] in {"self", "super"}:
                        token = tokens.pop(0)
                        if token == "super" and resolved:
                            resolved.pop()
                    parts = tuple([*resolved, *tokens])
                else:
                    parts = ()
                if len(parts) < 2 or parts[0] not in modules:
                    continue
                target_layer = layer_from_parts(parts[1:])
                if target_layer and (error := dependency_error(module, source_layer, parts[0], target_layer)):
                    errors.append(f"{source.relative_to(root)}:{line_number}: {error}")
            for match in re.finditer(r"crate::([a-z][a-z0-9_]*)::([a-z][a-z0-9_]*(?:::[a-z][a-z0-9_]*)?)", text):
                target_module, raw_layer = match.groups()
                if target_module not in modules:
                    continue
                target_layer = layer_from_parts(tuple(raw_layer.split("::")))
                line_number = text.count("\n", 0, match.start()) + 1
                if target_layer and (error := dependency_error(module, source_layer, target_module, target_layer)):
                    detail = f"{source.relative_to(root)}:{line_number}: {error}"
                    if detail not in errors:
                        errors.append(detail)
            for match in re.finditer(r"(?m)^\s*extern\s+crate\s+([a-z_][a-z0-9_]*)", text):
                crate_name = match.group(1)
                if not source_layer.startswith("adapters/") and crate_name in dependencies:
                    line_number = text.count("\n", 0, match.start()) + 1
                    errors.append(f"{source.relative_to(root)}:{line_number}: внутренний слой импортирует внешний crate {crate_name}")
            if not source_layer.startswith("adapters/"):
                for match in re.finditer(r"(?<![\w:])([a-z_][a-z0-9_]*)::", text):
                    crate_name = match.group(1)
                    if crate_name in dependencies:
                        line_number = text.count("\n", 0, match.start()) + 1
                        detail = f"{source.relative_to(root)}:{line_number}: внутренний слой использует внешний crate {crate_name}"
                        if detail not in errors:
                            errors.append(detail)
    return errors


def composition_root_errors(root: Path, language: str, path: Path) -> list[str]:
    if not path.is_file():
        return []
    relative = path.relative_to(root)
    text = path.read_text(encoding="utf-8")
    if language == "python":
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as error:
            return [f"{relative}: невозможно разобрать composition root: {error}"]
        allowed = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)
        assignments = [node for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))]
        def wiring_value(value: ast.expr | None) -> bool:
            if isinstance(value, (ast.Name, ast.Attribute)):
                return True
            if not isinstance(value, ast.Call):
                return False
            function = value.func.id if isinstance(value.func, ast.Name) else value.func.attr if isinstance(value.func, ast.Attribute) else ""
            return function[:1].isupper() or function in {"build", "create", "make", "new"}
        expressions = [node for node in tree.body if isinstance(node, ast.Expr)]
        terminal_calls = [
            node for node in expressions
            if isinstance(node.value, ast.Call)
            and (
                isinstance(node.value.func, ast.Name) and node.value.func.id in {"run", "serve", "start"}
                or isinstance(node.value.func, ast.Attribute) and node.value.func.attr in {"run", "serve", "start"}
            )
        ]
        docstrings = [node for node in expressions if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
        if (
            any(not isinstance(node, allowed + (ast.Expr,)) for node in tree.body)
            or any(not wiring_value(node.value) for node in assignments)
            or len(terminal_calls) > 1
            or len(expressions) != len(terminal_calls) + len(docstrings)
        ):
            return [f"{relative}: composition root содержит определения или управляющую логику"]
    elif language == "go":
        clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)
        functions = re.findall(r"(?m)^\s*func\s+([A-Za-z_]\w*)\s*\(", clean)
        forbidden = re.search(r"(?m)^\s*(?:type|const|var)\s+|^\s*func\s*\(", clean)
        control = re.search(r"\b(?:if|for|switch|select|go|defer|range)\b", clean)
        calls = re.findall(r"\b(?:[A-Za-z_]\w*\.)?([A-Za-z_]\w*)\s*\(", clean)
        allowed_calls = {"import", "main", "Run", "Start", "Serve", "Background", "TODO"}
        invalid_calls = [call for call in calls if call not in allowed_calls and not call.startswith("New")]
        if functions != ["main"] or forbidden or control or invalid_calls:
            return [f"{relative}: composition root должен содержать только func main"]
    else:
        functions = re.findall(r"(?m)^\s*(?:pub\s+)?fn\s+([A-Za-z_]\w*)\s*\(", text)
        forbidden = re.search(r"(?m)^\s*(?:struct|enum|trait|impl|const|static|type)\b", text)
        control = re.search(r"\b(?:if|for|while|loop|match|async|await)\b", text)
        calls = re.findall(r"\b([a-zA-Z_]\w*)\s*!?\(", text)
        allowed_calls = {"main", "new", "build", "from", "default", "run", "start", "serve"}
        if functions != ["main"] or forbidden or control or any(call not in allowed_calls for call in calls):
            return [f"{relative}: composition root должен содержать только fn main"]
    return []


def rust_module_manifest_errors(root: Path, path: Path, expected: set[str]) -> list[str]:
    if not path.is_file():
        return [f"отсутствует {path.relative_to(root)}"]
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    declaration_list = re.findall(r"(?m)^\s*(?:pub\s+)?mod\s+([a-z][a-z0-9_]*)\s*;\s*$", text)
    declarations = set(declaration_list)
    residue = re.sub(r"(?m)^\s*(?:pub\s+)?mod\s+[a-z][a-z0-9_]*\s*;\s*$", "", text).strip()
    if declarations != expected or len(declaration_list) != len(declarations) or residue:
        return [f"{path.relative_to(root)}: разрешены только объявления {sorted(expected)}"]
    return []


def source_outside_canon(root: Path, language: str, name: str, modules: list[str]) -> list[str]:
    suffix = {"python": ".py", "go": ".go", "rust": ".rs"}[language]
    ignored = {".git", ".venv", "build", "dist", "node_modules", "target", "vendor", "tools", "tests"}
    errors = []
    for source in root.rglob(f"*{suffix}"):
        relative = source.relative_to(root)
        if ignored.intersection(relative.parts):
            continue
        if language == "python":
            allowed_root = Path("src") / name
            allowed = relative.is_relative_to(allowed_root)
        elif language == "go":
            allowed = (
                relative.parts[:1] == ("internal",) and len(relative.parts) > 1 and relative.parts[1] in modules
            ) or relative == Path("cmd") / name / "main.go"
        else:
            allowed = (
                relative.parts[:1] == ("src",) and len(relative.parts) > 1 and relative.parts[1] in modules
            ) or relative == Path("src/main.rs")
        if not allowed:
            errors.append(f"{relative}: исходник вне канонических корней")
    return errors


def service_architecture_errors(root: Path, config: dict[str, str]) -> list[str]:
    errors = []
    name = config.get("service_name", "")
    language = config.get("service_language", "")
    modules, module_errors = service_modules(config)
    errors.extend(module_errors)
    if not SERVICE_NAME_PATTERN.fullmatch(name):
        errors.append("service_name: требуется lower_snake_case")
    if language not in SERVICE_LANGUAGES:
        errors.append("service_language: допустимы только python, go, rust")
    if errors:
        return errors
    expected_header = [
        "Модуль", "Ответственность", "Спецификация", "Язык", "Канонический корень", "Проверка границ"
    ]
    header, rows = documented_service_table(root)
    documented_modules = [row[0].strip("`") for row in rows if row]
    if header != expected_header or any(len(row) != len(expected_header) for row in rows):
        errors.append("docs/ARCHITECTURE.md: таблица модулей не соответствует каноническим столбцам")
    if documented_modules != modules:
        errors.append(
            "docs/ARCHITECTURE.md: порядок модулей "
            f"{documented_modules} не совпадает с service_modules {modules}"
        )
    for row, module in zip(rows, documented_modules):
        if len(row) != len(expected_header) or module not in modules:
            continue
        expected_root = canonical_service_paths(root, config, module)[0].relative_to(root).as_posix()
        values = [cell.strip("`") for cell in row]
        if values[3] != language or values[4].rstrip("/") != expected_root:
            errors.append(f"docs/ARCHITECTURE.md: неверные язык или корень модуля {module}")
        expected_spec = f"docs/specs/{module}.md"
        if values[2] != expected_spec or not (root / expected_spec).is_file():
            errors.append(f"docs/ARCHITECTURE.md: неверная или отсутствующая спецификация модуля {module}")
        if values[5] != "VER-015":
            errors.append(f"docs/ARCHITECTURE.md: модуль {module} должен проверяться VER-015")
        if any(not value or value == "TODO" for value in values[1:]):
            errors.append(f"docs/ARCHITECTURE.md: не заполнены поля модуля {module}")
    composition_roots = set()
    for module in modules:
        module_root, composition_root = canonical_service_paths(root, config, module)
        composition_roots.add(composition_root)
        for layer in SERVICE_LAYER_PATHS:
            directory = module_root.joinpath(*layer)
            if not directory.is_dir():
                errors.append(f"отсутствует каталог {directory.relative_to(root)}")
            elif language == "rust" and not (directory / "mod.rs").is_file():
                errors.append(f"отсутствует {directory.relative_to(root)}/mod.rs")
        if language == "rust":
            errors.extend(rust_module_manifest_errors(
                root, module_root / "mod.rs", {"domain", "application", "ports", "adapters"}
            ))
            errors.extend(rust_module_manifest_errors(
                root, module_root / "ports" / "mod.rs", {"inbound", "outbound"}
            ))
            errors.extend(rust_module_manifest_errors(
                root, module_root / "adapters" / "mod.rs", {"inbound", "outbound"}
            ))
    for composition_root in composition_roots:
        if not composition_root.is_file():
            errors.append(f"отсутствует composition root {composition_root.relative_to(root)}")
        else:
            errors.extend(composition_root_errors(root, language, composition_root))
    for test_kind in ("unit", "integration", "contract"):
        if not (root / "tests" / test_kind).is_dir():
            errors.append(f"отсутствует каталог tests/{test_kind}")
    if language == "python":
        source_root = root / "src" / name
        package_init = source_root / "__init__.py"
        if package_init.is_file():
            try:
                init_tree = ast.parse(package_init.read_text(encoding="utf-8"), filename=str(package_init))
                if any(
                    not isinstance(node, ast.Expr)
                    or not isinstance(node.value, ast.Constant)
                    or not isinstance(node.value.value, str)
                    for node in init_tree.body
                ):
                    errors.append(f"{package_init.relative_to(root)}: разрешена только строка документации")
            except (SyntaxError, UnicodeDecodeError) as error:
                errors.append(f"{package_init.relative_to(root)}: невозможно разобрать: {error}")
        for source in source_root.rglob("*.py") if source_root.is_dir() else ():
            relative = source.relative_to(source_root)
            if relative.parts[0] not in modules and relative.as_posix() not in {"__init__.py", "bootstrap.py"}:
                errors.append(f"{source.relative_to(root)}: исходник вне объявленного модуля")
        errors.extend(python_import_errors(root, name, modules))
    elif language == "go":
        internal = root / "internal"
        for source in internal.rglob("*.go") if internal.is_dir() else ():
            if source.relative_to(internal).parts[0] not in modules:
                errors.append(f"{source.relative_to(root)}: исходник вне объявленного модуля")
        command_root = root / "cmd" / name
        for source in command_root.rglob("*.go") if command_root.is_dir() else ():
            if source.name != "main.go":
                errors.append(f"{source.relative_to(root)}: вне composition root")
        errors.extend(go_import_errors(root, modules))
    else:
        source_root = root / "src"
        for source in source_root.rglob("*.rs") if source_root.is_dir() else ():
            relative = source.relative_to(source_root)
            if relative.parts[0] not in modules and relative.as_posix() != "main.rs":
                errors.append(f"{source.relative_to(root)}: исходник вне объявленного модуля")
        errors.extend(rust_import_errors(root, modules))
    errors.extend(source_outside_canon(root, language, name, modules))
    return errors


COMPOSITION_HEADERS = {
    "Сервисы": ["Сервис", "Репозиторий", "Версия/хеш", "Роль", "Публикует / Читает"],
    "Интерфейсы": [
        "Интерфейс", "Репозиторий", "Версия/хеш", "Визуализирует",
        "Потребляет (сервис-шлюз/маршрут)",
    ],
    "Автономные компоненты": [
        "Компонент", "Репозиторий", "Версия/хеш", "Форма", "Назначение / поверхности",
    ],
}
COMPONENT_VERSION_PATTERN = re.compile(
    r"^(?:[0-9a-f]{7,40}|sha256:[0-9a-f]{64}|v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?)$"
)


def composition_table(text: str, section: str) -> tuple[list[str], list[list[str]]]:
    match = re.search(rf"(?ms)^## {re.escape(section)}\s+(.*?)(?=^##\s|\Z)", text)
    if not match:
        return [], []
    rows = []
    for line in match.group(1).splitlines():
        if line.startswith("|") and not re.fullmatch(r"[|:\-\s]+", line):
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return (rows[0], rows[1:]) if rows else ([], [])


def composition_errors(root: Path) -> tuple[list[str], list[str]]:
    path = root / "COMPOSITION.md"
    if not path.is_file():
        return ["COMPOSITION.md отсутствует"], []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [f"COMPOSITION.md невозможно прочитать: {error}"], []
    errors: list[str] = []
    repositories: list[str] = []
    names: set[str] = set()
    gateways: set[str] = set()
    interfaces: list[list[str]] = []
    for section, expected_header in COMPOSITION_HEADERS.items():
        header, rows = composition_table(text, section)
        section_match = re.search(rf"(?ms)^## {re.escape(section)}\s+(.*?)(?=^##\s|\Z)", text)
        explicitly_empty = bool(
            section_match
            and re.search(r"(?mi)^\s*(?:-\s*)?нет[.!]?\s*$", section_match.group(1))
        )
        if explicitly_empty and not rows:
            continue
        if header != expected_header:
            errors.append(f"раздел «{section}»: неверные столбцы")
            continue
        if not rows:
            errors.append(f"раздел «{section}»: укажите компоненты или строку «нет» вне таблицы")
        for row in rows:
            if len(row) != len(expected_header):
                errors.append(f"раздел «{section}»: строка имеет неверное число столбцов")
                continue
            values = [cell.strip("`*") for cell in row]
            name, repository, version = values[:3]
            if any("<" in value or ">" in value or value in {"…", "..."} for value in values):
                errors.append(f"раздел «{section}»: остался маркер заготовки")
                continue
            if not name or name in names:
                errors.append(f"раздел «{section}»: пустое или повторное имя {name!r}")
            names.add(name)
            if not re.fullmatch(r"(?:https://\S+|ssh://\S+|git@[^\s:]+:\S+)", repository):
                errors.append(f"раздел «{section}»: репозиторий {repository!r} должен быть URL Git")
            elif repository in repositories:
                errors.append(f"раздел «{section}»: репозиторий {repository!r} указан повторно")
            else:
                repositories.append(repository)
            if not COMPONENT_VERSION_PATTERN.fullmatch(version):
                errors.append(f"раздел «{section}»: версия/хеш {version!r} не закреплены")
            if section == "Сервисы" and "`gateway`" in row[3]:
                gateways.add(name)
            if section == "Интерфейсы":
                interfaces.append(values)
    if interfaces and len(gateways) != 1:
        errors.append("при наличии интерфейсов требуется ровно один сервис-шлюз")
    if len(gateways) == 1:
        gateway = next(iter(gateways))
        for interface in interfaces:
            if not re.match(rf"^{re.escape(gateway)}\s+/", interface[4]):
                errors.append(f"интерфейс {interface[0]} должен ссылаться на сервис-шлюз {gateway}")
    dependencies = re.search(r"(?ms)^## Зависимости \(DAG\)\s+(.*?)(?=^##\s|\Z)", text)
    if not dependencies or not any(
        language == "mermaid" for _, language, _ in fenced_blocks(dependencies.group(1))
    ):
        errors.append("раздел зависимостей должен содержать диаграмму Mermaid")
    return errors, repositories


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
        match = TASK_PATTERN.fullmatch(heading)
        if match:
            for field in ("Цель:", "Готово, когда:", "Не входит:"):
                if field not in block:
                    errors.append(f"{heading}: отсутствует поле «{field}»")
            if match.group(2) in {"needs-input", "blocked-external", "automation-failed", "retry-exhausted"}:
                lines = [line.strip() for line in block.splitlines()[1:] if line.strip()]
                if not lines or not lines[0].startswith("Диагностика:") or not lines[0].removeprefix("Диагностика:").strip():
                    errors.append(f"{heading}: диагностика должна идти сразу после заголовка")
    return errors


def run(
    root: Path,
    ci_methodology_ref: str | None = None,
    expected_commit: str | None = None,
    finalization_base: str | None = None,
) -> dict[str, object]:
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
        path = root / item
        present = path.is_file()
        checks.append(result("VER-001", present, f"Обязательный файл: {item}", item))

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
    if expected_commit is not None:
        checks.append(
            result(
                "VER-017",
                commit_matches_head(root, expected_commit),
                "Переданный CI-коммит совпадает с текущим HEAD",
                ".git/HEAD",
            )
        )
    if finalization_base is not None:
        finalization_errors = finalization_diff_errors(root, finalization_base)
        checks.append(result(
            "VER-019",
            not finalization_errors,
            "Служебный PR изменяет только одну задачу и её evidence"
            if not finalization_errors else "Ошибки финализации: " + "; ".join(finalization_errors),
            "BACKLOG.md, .evidence/TASK-NNNN.json",
        ))

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

    diagram_violations = non_mermaid_diagrams(root)
    diagrams_message = "Все диаграммы Markdown оформлены блоками Mermaid"
    if diagram_violations:
        diagrams_message = "Диаграммы не в Mermaid: " + ", ".join(diagram_violations)
    checks.append(result("VER-014", not diagram_violations, diagrams_message, "*.md"))

    legacy_references = []
    for markdown in markdown_files(root):
        try:
            if LEGACY_DOC_PATTERN.search(markdown.read_text(encoding="utf-8")):
                legacy_references.append(str(markdown.relative_to(root)))
        except (OSError, UnicodeDecodeError) as error:
            legacy_references.append(f"{markdown.relative_to(root)}: невозможно прочитать: {error}")
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

    if kind == "service":
        architecture_errors = service_architecture_errors(root, config)
        checks.append(
            result(
                "VER-015",
                not architecture_errors,
                "Структура и зависимости сервиса соответствуют архитектурному канону"
                if not architecture_errors
                else "Нарушения архитектуры сервиса: " + "; ".join(architecture_errors),
                "src/, internal/, cmd/, tests/",
            )
        )

    if kind in {"hub", "service", "interface", "standalone"}:
        product_pipeline_errors = pipeline_errors(root)
        checks.append(
            result(
                "VER-018",
                not product_pipeline_errors,
                "Продуктовый конвейер настроен и имеет блокирующий порядок стадий"
                if not product_pipeline_errors
                else "Ошибки продуктового конвейера: " + "; ".join(product_pipeline_errors),
                ".pipeline.json, .github/workflows/verify.yml",
            )
        )

    if kind == "hub":
        composition_problems, child_repositories = composition_errors(root)
        composition_message = "Состав программы структурно валиден"
        if child_repositories:
            composition_message += "; дочерние репозитории: " + ", ".join(child_repositories)
        if composition_problems:
            composition_message = "Ошибки состава программы: " + "; ".join(composition_problems)
        checks.append(result("VER-016", not composition_problems, composition_message, "COMPOSITION.md"))

    if kind in {"hub", "methodology"}:
        backlog = root / "BACKLOG.md" if kind == "hub" else root / "skeletons/hub/BACKLOG.md"
        backlog_read_error = ""
        try:
            backlog_text = backlog.read_text(encoding="utf-8") if backlog.is_file() else ""
        except (OSError, UnicodeDecodeError) as error:
            backlog_text = ""
            backlog_read_error = f"{backlog.name}: невозможно прочитать: {error}"
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

        task_record_errors: list[str] = [backlog_read_error] if backlog_read_error else []
        try:
            tasks = task_records(backlog_text)
        except BacklogError as error:
            tasks = {}
            task_record_errors.append(str(error))
        checks.append(result("VER-012", not task_record_errors,
            "Задачи BACKLOG.md валидны" if not task_record_errors
            else "Ошибки задач: " + "; ".join(task_record_errors), backlog_location))

        evidence, evidence_errors = load_records(
            root / ".evidence" if kind == "hub" else root / "skeletons/hub/.evidence",
            "evidence.schema.json",
        )
        # README не является evidence; отсутствие JSON допустимо, пока нет done-задач.
        evidence_errors = [error for error in evidence_errors if "отсутствует каталог" not in error]
        for task_id, record in evidence.items():
            if task_id not in tasks:
                evidence_errors.append(f"{task_id}: evidence не связан с машинной задачей")
            if record.get("methodology_ref") != pinned_ref and kind != "methodology":
                evidence_errors.append(f"{task_id}: methodology_ref не совпадает с .methodology.yml")
            repository = record.get("repository")
            pr = record.get("pr")
            if isinstance(repository, str) and isinstance(pr, str) and not pr.startswith(repository.rstrip("/") + "/pull/"):
                evidence_errors.append(f"{task_id}: PR не принадлежит указанному продуктовому репозиторию")
            try:
                created = datetime.fromisoformat(str(record.get("created_at", "")).replace("Z", "+00:00"))
                retained = datetime.fromisoformat(str(record.get("retained_until", "")).replace("Z", "+00:00"))
                if retained <= created:
                    evidence_errors.append(f"{task_id}: retained_until должен быть позже created_at")
            except (ValueError, TypeError):
                pass  # Формат уже диагностирован валидатором схемы.
            results = record.get("checks", []) + record.get("reviews", [])
            probes = record.get("deployment", {}).get("probes", []) if isinstance(record.get("deployment"), dict) else []
            if record.get("status") == "passed" and any(
                item.get("status") == "failed" for item in results + probes if isinstance(item, dict)
            ):
                evidence_errors.append(f"{task_id}: passed evidence содержит failed результат")
            if record.get("status") == "passed":
                checks_passed = any(item.get("status") == "passed" for item in record.get("checks", []) if isinstance(item, dict))
                reviews_passed = any(item.get("status") == "passed" for item in record.get("reviews", []) if isinstance(item, dict))
                probes_passed = any(item.get("status") == "passed" for item in probes if isinstance(item, dict))
                if not checks_passed or not reviews_passed or not probes_passed:
                    evidence_errors.append(f"{task_id}: passed evidence требует успешные check, review и deployment probe")
        for task_id, task in tasks.items():
            if task.get("status") == "done":
                if task_id not in evidence:
                    evidence_errors.append(f"{task_id}: завершённая задача не имеет evidence")
                elif evidence[task_id].get("status") != "passed":
                    evidence_errors.append(f"{task_id}: завершённая задача требует evidence со статусом passed")
        checks.append(result("VER-013", not evidence_errors,
            "Evidence валиден, связан с задачами и контекстом CI" if not evidence_errors
            else "Ошибки evidence: " + "; ".join(evidence_errors), ".evidence/*.json"))
        malformed_tasks = [backlog_read_error] if backlog_read_error else backlog_errors(backlog_text)
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
    report = run(root, args.methodology_ref, args.commit, args.finalization_base)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(output)
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
