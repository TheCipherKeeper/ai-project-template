import json
from pathlib import Path

import pytest

from sync import BacklogError, sync, task_records


BACKLOG = """### TASK-0042. [ ] ready — Экспорт

Целевой репозиторий: reports
Риск: high
Автономность: human-before-production
Триггеры:
- contract

Цель:
Пользователь выгружает отчёт.

Готово, когда:
- доступен CSV
- ошибки видны пользователю

Не входит:
- импорт

Откат: вернуть предыдущий артефакт.
"""


def test_task_records_parse_canonical_backlog() -> None:
    assert task_records(BACKLOG)["TASK-0042"] == {
        "schema_version": 1,
        "id": "TASK-0042",
        "status": "ready",
        "target": "reports",
        "risk": "high",
        "autonomy": "human-before-production",
        "goal": "Пользователь выгружает отчёт.",
        "acceptance_criteria": ["доступен CSV", "ошибки видны пользователю"],
        "out_of_scope": ["импорт"],
        "triggers": ["contract"],
        "rollback": "вернуть предыдущий артефакт.",
    }


def test_sync_writes_records_and_removes_stale_files(tmp_path: Path) -> None:
    (tmp_path / "BACKLOG.md").write_text(BACKLOG, encoding="utf-8")
    tasks = tmp_path / ".tasks"
    tasks.mkdir()
    (tasks / "TASK-9999.json").write_text("{}", encoding="utf-8")

    assert sync(tmp_path) == [".tasks/TASK-0042.json", ".tasks/TASK-9999.json"]
    assert json.loads((tasks / "TASK-0042.json").read_text(encoding="utf-8"))["id"] == "TASK-0042"
    assert not (tasks / "TASK-9999.json").exists()
    assert sync(tmp_path, check=True) == []


def test_sync_check_does_not_modify_files(tmp_path: Path) -> None:
    (tmp_path / "BACKLOG.md").write_text(BACKLOG, encoding="utf-8")

    assert sync(tmp_path, check=True) == [".tasks/TASK-0042.json"]
    assert not (tmp_path / ".tasks").exists()


def test_task_records_reject_missing_machine_field() -> None:
    with pytest.raises(BacklogError, match="Риск"):
        task_records(BACKLOG.replace("Риск: high\n", ""))


def test_last_field_stops_at_next_markdown_section() -> None:
    records = task_records(BACKLOG + "\n## Выполнено\n\nПояснение.\n")

    assert records["TASK-0042"]["rollback"] == "вернуть предыдущий артефакт."


def test_sync_does_not_prune_when_task_heading_is_malformed(tmp_path: Path) -> None:
    (tmp_path / "BACKLOG.md").write_text(BACKLOG, encoding="utf-8")
    sync(tmp_path)
    task_path = tmp_path / ".tasks" / "TASK-0042.json"
    (tmp_path / "BACKLOG.md").write_text(BACKLOG.replace("### TASK-0042", "#### Task-0042"), encoding="utf-8")

    with pytest.raises(BacklogError, match="некорректный заголовок"):
        sync(tmp_path)

    assert task_path.exists()


def test_task_records_reject_unsupported_list_continuation() -> None:
    backlog = BACKLOG.replace("- доступен CSV", "- доступен CSV\n  только администратору")

    with pytest.raises(BacklogError, match="неподдерживаемую строку"):
        task_records(backlog)


@pytest.mark.parametrize(
    ("old", "new", "field"),
    [
        ("Риск: high", "Риск: severe", "risk"),
        ("Автономность: human-before-production", "Автономность: unlimited", "autonomy"),
        ("- contract", "- unknown", "triggers"),
    ],
)
def test_sync_rejects_invalid_schema_enum_before_mutation(
    tmp_path: Path, old: str, new: str, field: str
) -> None:
    backlog = tmp_path / "BACKLOG.md"
    backlog.write_text(BACKLOG, encoding="utf-8")
    sync(tmp_path)
    task_path = tmp_path / ".tasks" / "TASK-0042.json"
    original = task_path.read_text(encoding="utf-8")
    backlog.write_text(BACKLOG.replace(old, new), encoding="utf-8")

    with pytest.raises(BacklogError, match=field):
        sync(tmp_path)

    assert task_path.read_text(encoding="utf-8") == original


def test_task_records_reject_empty_list_item() -> None:
    with pytest.raises(BacklogError, match="Неподдерживаемую|неподдерживаемую|должно быть списком"):
        task_records(BACKLOG.replace("- импорт", "- "))


def test_task_records_reject_duplicate_field_and_trigger() -> None:
    with pytest.raises(BacklogError, match="указано несколько раз"):
        task_records(BACKLOG.replace("Риск: high", "Риск: high\nРиск: critical"))
    with pytest.raises(BacklogError, match="повторяющиеся элементы"):
        task_records(BACKLOG.replace("- contract", "- contract\n- contract"))


def test_task_records_enforce_risk_and_autonomy_policy() -> None:
    with pytest.raises(BacklogError, match="требуют риск high"):
        task_records(BACKLOG.replace("Риск: high", "Риск: medium"))
    with pytest.raises(BacklogError, match="автономность слишком широка"):
        task_records(BACKLOG.replace("Автономность: human-before-production", "Автономность: auto-test-deploy"))
    with pytest.raises(BacklogError, match="автономность слишком широка"):
        task_records(BACKLOG.replace("Риск: high", "Риск: critical"))


def test_diagnostic_status_requires_immediate_diagnostic() -> None:
    diagnostic = BACKLOG.replace("[ ] ready", "[ ] needs-input").replace(
        "\n\nЦелевой репозиторий:", "\n\nДиагностика: требуется выбор формата.\n\nЦелевой репозиторий:"
    )
    record = task_records(diagnostic)["TASK-0042"]
    assert record["diagnostic"] == "требуется выбор формата."

    with pytest.raises(BacklogError, match="требует поле"):
        task_records(BACKLOG.replace("[ ] ready", "[ ] needs-input"))
    with pytest.raises(BacklogError, match="сразу после заголовка"):
        task_records(
            BACKLOG.replace("[ ] ready", "[ ] needs-input").replace(
                "Цель:", "Диагностика: поздно.\n\nЦель:"
            )
        )


def test_sync_restores_previous_projection_after_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backlog = tmp_path / "BACKLOG.md"
    backlog.write_text(BACKLOG, encoding="utf-8")
    sync(tmp_path)
    task_path = tmp_path / ".tasks" / "TASK-0042.json"
    original = task_path.read_text(encoding="utf-8")
    backlog.write_text(BACKLOG.replace("доступен CSV", "доступен JSON"), encoding="utf-8")
    write_text = Path.write_text

    def failing_write(path: Path, data: str, *args: object, **kwargs: object) -> int:
        if path.name == "TASK-0042.json" and path.parent.name.startswith(".tasks-"):
            raise OSError("имитация сбоя записи")
        return write_text(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failing_write)
    with pytest.raises(OSError, match="имитация"):
        sync(tmp_path)

    assert task_path.read_text(encoding="utf-8") == original
