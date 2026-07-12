from pathlib import Path

from verify import markdown_files, run


def make_hub(tmp_path: Path, methodology_ref: str = "v1.0.0") -> None:
    (tmp_path / ".methodology.yml").write_text(
        f"repository_type: hub\nmethodology_ref: {methodology_ref}\n", encoding="utf-8"
    )
    for name in ("AGENTS.md", "README.md", "COMPOSITION.md", "CONVENTIONS.md"):
        (tmp_path / name).write_text("ok\n", encoding="utf-8")


def test_markdown_files_ignore_dependency_and_build_trees(tmp_path: Path) -> None:
    included = tmp_path / "docs" / "README.md"
    ignored = [
        tmp_path / "node_modules" / "dependency" / "README.md",
        tmp_path / "target" / "doc" / "README.md",
        tmp_path / ".venv" / "package" / "README.md",
    ]
    included.parent.mkdir(parents=True)
    included.write_text("ok", encoding="utf-8")
    for path in ignored:
        path.parent.mkdir(parents=True)
        path.write_text("ignored", encoding="utf-8")

    assert list(markdown_files(tmp_path)) == [included]


def test_hub_rejects_legacy_in_flight_status(tmp_path: Path) -> None:
    make_hub(tmp_path)
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [~] Устаревший статус\n", encoding="utf-8"
    )

    report = run(tmp_path)

    assert report["status"] == "failed"
    assert any(
        check["id"] == "VER-005" and check["status"] == "failed"
        for check in report["checks"]
    )


def test_instantiated_repository_requires_pinned_methodology(tmp_path: Path) -> None:
    make_hub(tmp_path, methodology_ref="latest")
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [ ] ready — Задача\n", encoding="utf-8"
    )

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-003" and check["status"] == "failed"
        for check in report["checks"]
    )


def test_hub_rejects_malformed_task_heading(tmp_path: Path) -> None:
    make_hub(tmp_path)
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-1. [ ] ready — Нестабильный ID\n", encoding="utf-8"
    )

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-006" and check["status"] == "failed"
        for check in report["checks"]
    )
