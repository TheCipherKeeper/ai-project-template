"""Детерминированный гейт методологии для локального запуска и CI."""

from __future__ import annotations

import argparse
import json
import re
import sys
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
    ),
    "hub": (
        "AGENTS.md",
        "README.md",
        "BACKLOG.md",
        ".tasks",
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
NON_MERMAID_DIAGRAM_LANGUAGES = frozenset({
    "d2", "dot", "graphviz", "nomnoml", "plantuml", "puml", "uml", "vega", "vega-lite"
})
TEXT_DIAGRAM_PATTERN = re.compile(
    r"(?:-{1,2}>|<-{1,2}|[→←↔]|[┌┐└┘├┤┬┴┼│]|^\s*\+[-=]{2,}(?:\+|\s))",
    re.MULTILINE,
)


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
        text = markdown.read_text(encoding="utf-8")
        for line, language, body in fenced_blocks(text):
            is_other_diagram_language = language in NON_MERMAID_DIAGRAM_LANGUAGES
            is_text_diagram = language in {"", "text"} and TEXT_DIAGRAM_PATTERN.search(body)
            if is_other_diagram_language or is_text_diagram:
                violations.append(f"{markdown.relative_to(root)}:{line}")
    return violations


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
                datetime.fromisoformat(instance.replace("Z", "+00:00"))
            except ValueError:
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


def run(root: Path, ci_methodology_ref: str | None = None, expected_commit: str | None = None) -> dict[str, object]:
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

    diagram_violations = non_mermaid_diagrams(root)
    diagrams_message = "Все диаграммы Markdown оформлены блоками Mermaid"
    if diagram_violations:
        diagrams_message = "Диаграммы не в Mermaid: " + ", ".join(diagram_violations)
    checks.append(result("VER-014", not diagram_violations, diagrams_message, "*.md"))

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

        tasks, task_record_errors = load_records(
            root / ".tasks" if kind == "hub" else root / "skeletons/hub/.tasks",
            "task.schema.json",
        )
        parsed_headings = {
            match.group(1): "done" if "[x]" in heading else match.group(2)
            for heading in re.findall(r"^### TASK-.*$", backlog_text, re.MULTILINE)
            if (match := TASK_PATTERN.fullmatch(heading))
        }
        for task_id, status in parsed_headings.items():
            record = tasks.get(task_id)
            if record is None:
                task_record_errors.append(f"{task_id}: отсутствует машинная запись")
            elif record.get("status") != status:
                task_record_errors.append(
                    f"{task_id}: status={record.get('status')} не совпадает с backlog={status}"
                )
        for task_id in tasks.keys() - parsed_headings.keys():
            task_record_errors.append(f"{task_id}: нет соответствующей задачи в BACKLOG.md")
        checks.append(result("VER-012", not task_record_errors,
            "Машинные задачи валидны и соответствуют BACKLOG.md" if not task_record_errors
            else "Ошибки машинных задач: " + "; ".join(task_record_errors), ".tasks/*.json"))

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
            if expected_commit and record.get("commit") != expected_commit:
                evidence_errors.append(f"{task_id}: commit не совпадает с --commit")
            try:
                created = datetime.fromisoformat(str(record.get("created_at", "")).replace("Z", "+00:00"))
                retained = datetime.fromisoformat(str(record.get("retained_until", "")).replace("Z", "+00:00"))
                if retained <= created:
                    evidence_errors.append(f"{task_id}: retained_until должен быть позже created_at")
            except ValueError:
                pass  # Формат уже диагностирован валидатором схемы.
            results = record.get("checks", []) + record.get("reviews", [])
            probes = record.get("deployment", {}).get("probes", []) if isinstance(record.get("deployment"), dict) else []
            if record.get("status") == "passed" and any(
                item.get("status") == "failed" for item in results + probes if isinstance(item, dict)
            ):
                evidence_errors.append(f"{task_id}: passed evidence содержит failed результат")
        for task_id, task in tasks.items():
            if task.get("status") == "done" and task_id not in evidence:
                evidence_errors.append(f"{task_id}: завершённая задача не имеет evidence")
        checks.append(result("VER-013", not evidence_errors,
            "Evidence валиден, связан с задачами и контекстом CI" if not evidence_errors
            else "Ошибки evidence: " + "; ".join(evidence_errors), ".evidence/*.json"))
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
    report = run(root, args.methodology_ref, args.commit)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(output)
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
