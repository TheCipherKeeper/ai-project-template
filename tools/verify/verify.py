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
        "docs/refs/VERIFICATION.md",
        ".methodology.yml",
    ),
    "hub": (
        "AGENTS.md",
        "README.md",
        "BACKLOG.md",
        "COMPOSITION.md",
        "CONVENTIONS.md",
        ".methodology.yml",
    ),
    "service": (
        "AGENTS.md",
        "README.md",
        "docs/ARCHITECTURE.md",
        "Dockerfile",
        ".methodology.yml",
    ),
    "interface": (
        "AGENTS.md",
        "README.md",
        "docs/ARCHITECTURE.md",
        ".methodology.yml",
    ),
    "standalone": (
        "AGENTS.md",
        "README.md",
        "docs/ARCHITECTURE.md",
        ".methodology.yml",
    ),
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
REPOSITORY_TYPE_PATTERN = re.compile(r"^repository_type:\s*([a-z]+)\s*$", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=POLICY_ROOT,
        help="корень проверяемого репозитория (по умолчанию — репозиторий методологии)",
    )
    parser.add_argument("--report", type=Path, help="путь для JSON-отчёта")
    return parser.parse_args()


def repository_type(root: Path) -> str:
    config = root / ".methodology.yml"
    if not config.is_file():
        return "methodology"
    match = REPOSITORY_TYPE_PATTERN.search(config.read_text(encoding="utf-8"))
    return match.group(1) if match else "methodology"


def result(check_id: str, passed: bool, message: str, location: str) -> dict[str, str]:
    return {
        "id": check_id,
        "status": "passed" if passed else "failed",
        "message": message,
        "location": location,
    }


def markdown_files(root: Path):
    for path in root.rglob("*.md"):
        if ".git" not in path.relative_to(root).parts:
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


def run(root: Path) -> dict[str, object]:
    checks: list[dict[str, str]] = []
    kind = repository_type(root)

    required = REQUIRED_BY_TYPE.get(kind, ())
    checks.append(
        result(
            "VER-001",
            bool(required),
            f"Поддерживаемый тип репозитория: {kind}",
            ".methodology.yml",
        )
    )
    for item in required:
        checks.append(result("VER-001", (root / item).exists(), f"Обязательный файл: {item}", item))

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

    invalid_json = []
    for schema in (POLICY_ROOT / "schemas").glob("*.json"):
        try:
            json.loads(schema.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            invalid_json.append(schema.name)
    json_message = "JSON-схемы валидны"
    if invalid_json:
        json_message = "Невалидные JSON-схемы: " + ", ".join(invalid_json)
    checks.append(result("VER-011", not invalid_json, json_message, "schemas/"))

    backlog = root / "BACKLOG.md" if kind == "hub" else root / "skeletons/hub/BACKLOG.md"
    backlog_text = backlog.read_text(encoding="utf-8") if backlog.is_file() else ""
    in_flight = len(re.findall(r"^### .*\[~\]", backlog_text, re.MULTILINE))
    checks.append(
        result(
            "VER-005",
            in_flight <= 1,
            "В backlog не более одного активного пункта",
            "BACKLOG.md" if kind == "hub" else "skeletons/hub/BACKLOG.md",
        )
    )

    failed = any(check["status"] == "failed" for check in checks)
    return {"status": "failed" if failed else "passed", "repository_type": kind, "checks": checks}


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    report = run(root)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(output)
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
