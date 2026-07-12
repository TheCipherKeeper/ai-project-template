from pathlib import Path

from verify import markdown_files, run


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
    (tmp_path / ".methodology.yml").write_text("repository_type: hub\n", encoding="utf-8")
    for name in ("AGENTS.md", "README.md", "COMPOSITION.md", "CONVENTIONS.md"):
        (tmp_path / name).write_text("ok\n", encoding="utf-8")
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [~] Устаревший статус\n", encoding="utf-8"
    )

    report = run(tmp_path)

    assert report["status"] == "failed"
    assert any(
        check["id"] == "VER-005" and check["status"] == "failed"
        for check in report["checks"]
    )
