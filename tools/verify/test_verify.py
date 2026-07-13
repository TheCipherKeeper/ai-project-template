from pathlib import Path

import json
import subprocess
import sys

from verify import (
    commit_matches_head,
    finalization_diff_errors,
    composition_errors,
    markdown_files,
    main,
    non_mermaid_diagrams,
    pipeline_errors,
    run,
    skeleton_errors,
    validate_json,
)
from sync import sync


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


def test_skeletons_use_standalone_directory(tmp_path: Path) -> None:
    standalone = tmp_path / "skeletons" / "standalone"
    standalone.mkdir(parents=True)
    (standalone / "AGENTS.md").write_text("ok\n", encoding="utf-8")

    errors = skeleton_errors(tmp_path)

    assert "skeletons/standalone/AGENTS.md" not in errors
    assert not any(error.startswith("skeletons/stub/") for error in errors)


def test_skeletons_reject_legacy_stub_directory_and_marker(tmp_path: Path) -> None:
    legacy = tmp_path / "skeletons" / "stub"
    legacy.mkdir(parents=True)
    standalone = tmp_path / "skeletons" / "standalone"
    standalone.mkdir(parents=True)
    (standalone / ".env.example").write_text("<STUB>_PORT=8080\n", encoding="utf-8")

    errors = skeleton_errors(tmp_path)

    assert "skeletons/stub: устаревшее имя, используйте skeletons/standalone" in errors
    assert "skeletons/standalone/.env.example: устаревший маркер stub" in errors


def test_skeletons_reject_divergent_shared_workflow(tmp_path: Path) -> None:
    for kind in ("hub", "service", "interface", "standalone"):
        workflow = tmp_path / "skeletons" / kind / ".github" / "workflows" / "verify.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(f"name: {kind}\n", encoding="utf-8")

    errors = skeleton_errors(tmp_path)

    assert "skeletons/*/.github/workflows/verify.yml: общая заготовка рассинхронизирована" in errors


def test_pipeline_rejects_unconfigured_markers(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "skeletons" / "service"
    subprocess.run([sys.executable, "-c", "import shutil,sys; shutil.copytree(sys.argv[1],sys.argv[2])", str(source), str(tmp_path / "service")], check=True)

    errors = pipeline_errors(tmp_path / "service")

    assert ".pipeline.json: остались маркеры первичной настройки" in errors


def test_pipeline_rejects_broken_stage_order(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "skeletons" / "hub"
    subprocess.run([sys.executable, "-c", "import shutil,sys; shutil.copytree(sys.argv[1],sys.argv[2])", str(source), str(tmp_path / "hub")], check=True)
    workflow = tmp_path / "hub" / ".github" / "workflows" / "verify.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace("    needs: review\n", "    needs: tests\n", 1),
        encoding="utf-8",
    )

    errors = pipeline_errors(tmp_path / "hub")

    assert ".github/workflows/verify.yml: build должен зависеть от review" in errors


def test_text_diagram_is_rejected(tmp_path: Path) -> None:
    diagram = tmp_path / "ARCHITECTURE.md"
    diagram.write_text("```text\nA → B\n```\n", encoding="utf-8")

    assert non_mermaid_diagrams(tmp_path) == ["ARCHITECTURE.md:1"]


def test_mermaid_diagram_is_accepted(tmp_path: Path) -> None:
    diagram = tmp_path / "ARCHITECTURE.md"
    diagram.write_text("```mermaid\nflowchart LR\n    A --> B\n```\n", encoding="utf-8")

    assert non_mermaid_diagrams(tmp_path) == []


def test_ascii_diagram_variants_are_rejected(tmp_path: Path) -> None:
    diagram = tmp_path / "ARCHITECTURE.md"
    diagram.write_text(
        "```text\nA -> B\n```\n\n````\n+---+\n| A |\n+---+\n````\n",
        encoding="utf-8",
    )

    assert non_mermaid_diagrams(tmp_path) == ["ARCHITECTURE.md:1", "ARCHITECTURE.md:5"]


def test_tilde_diagram_fence_is_rejected(tmp_path: Path) -> None:
    diagram = tmp_path / "ARCHITECTURE.md"
    diagram.write_text("~~~plantuml\nA -> B\n~~~\n", encoding="utf-8")

    assert non_mermaid_diagrams(tmp_path) == ["ARCHITECTURE.md:1"]


def test_explicitly_typed_log_with_arrow_is_accepted(tmp_path: Path) -> None:
    log = tmp_path / "RUNBOOK.md"
    log.write_text("```console\nworker --> ready\n```\n", encoding="utf-8")

    assert non_mermaid_diagrams(tmp_path) == []


def test_unfenced_text_diagram_is_rejected(tmp_path: Path) -> None:
    diagram = tmp_path / "ARCHITECTURE.md"
    diagram.write_text("Контекст.\n\nA --> B\n", encoding="utf-8")

    assert non_mermaid_diagrams(tmp_path) == ["ARCHITECTURE.md:3"]


def test_markdown_files_ignore_directory_with_markdown_name(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").mkdir()

    assert list(markdown_files(tmp_path)) == []


def test_commonmark_fence_variants_are_rejected(tmp_path: Path) -> None:
    diagram = tmp_path / "ARCHITECTURE.md"
    diagram.write_text("   ```uml\nA -> B\n   ````\n", encoding="utf-8")

    assert non_mermaid_diagrams(tmp_path) == ["ARCHITECTURE.md:1"]


def test_ascii_tree_is_rejected(tmp_path: Path) -> None:
    diagram = tmp_path / "ARCHITECTURE.md"
    diagram.write_text("```text\nroot\n+-- child\n+-- leaf\n```\n", encoding="utf-8")

    assert non_mermaid_diagrams(tmp_path) == ["ARCHITECTURE.md:1"]


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


def test_config_rejects_unknown_fields(tmp_path: Path) -> None:
    make_hub(tmp_path)
    (tmp_path / ".methodology.yml").write_text(
        "schema_version: 1\nrepository_type: hub\nmethodology_ref: v1.0.0\nextra: value\n",
        encoding="utf-8",
    )
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [ ] ready — Задача\n\nЦель:\nx\n\nГотово, когда:\n- x\n\nНе входит:\n- нет\n",
        encoding="utf-8",
    )

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-001" and check["status"] == "failed"
        for check in report["checks"]
    )


def test_ci_ref_must_match_pinned_ref(tmp_path: Path) -> None:
    make_hub(tmp_path, methodology_ref="v1.0.0")
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [ ] ready — Задача\n\nЦель:\nx\n\nГотово, когда:\n- x\n\nНе входит:\n- нет\n",
        encoding="utf-8",
    )

    report = run(tmp_path, ci_methodology_ref="v2.0.0")

    assert any(
        check["id"] == "VER-003" and check["status"] == "failed"
        for check in report["checks"]
    )


def test_backlog_accepts_diagnostic_status_and_requires_fields(tmp_path: Path) -> None:
    make_hub(tmp_path)
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [ ] needs-input — Нужен выбор\n\nДиагностика: выбор человека.\n",
        encoding="utf-8",
    )

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-006"
        and check["status"] == "failed"
        and "отсутствует поле" in check["message"]
        for check in report["checks"]
    )


def test_methodology_rejects_powershell_scripts(tmp_path: Path) -> None:
    (tmp_path / ".methodology.yml").write_text(
        "schema_version: 1\nrepository_type: methodology\nmethodology_ref: self\n",
        encoding="utf-8",
    )
    (tmp_path / "tool.ps1").write_text("Write-Output bad\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-007" and check["status"] == "failed"
        for check in report["checks"]
    )


def test_service_does_not_require_local_backlog(tmp_path: Path) -> None:
    (tmp_path / ".methodology.yml").write_text(
        "schema_version: 1\nrepository_type: service\nmethodology_ref: v1.0.0\n",
        encoding="utf-8",
    )

    report = run(tmp_path)

    assert not any(check["id"] in {"VER-005", "VER-006"} for check in report["checks"])


def make_python_service(tmp_path: Path) -> None:
    (tmp_path / ".methodology.yml").write_text(
        "schema_version: 1\nrepository_type: service\nmethodology_ref: v1.0.0\n"
        "service_name: demo\nservice_language: python\nservice_modules: orders\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "specs").mkdir()
    (docs / "specs" / "orders.md").write_text("# Orders\n", encoding="utf-8")
    (docs / "ARCHITECTURE.md").write_text(
        "# Архитектура\n\n## Модули\n\n"
        "| Модуль | Ответственность | Спецификация | Язык | Канонический корень | Проверка границ |\n"
        "|---|---|---|---|---|---|\n"
        "| `orders` | Заказы | `docs/specs/orders.md` | python | `src/demo/orders/` | VER-015 |\n",
        encoding="utf-8",
    )
    module = tmp_path / "src" / "demo" / "orders"
    for parts in (
        ("domain",), ("application",), ("ports", "inbound"),
        ("ports", "outbound"), ("adapters", "inbound"), ("adapters", "outbound"),
    ):
        directory = module.joinpath(*parts)
        directory.mkdir(parents=True)
        (directory / "README.md").write_text("Назначение.\n", encoding="utf-8")
    bootstrap = tmp_path / "src" / "demo" / "bootstrap.py"
    bootstrap.write_text("# composition root\n", encoding="utf-8")
    for kind in ("unit", "integration", "contract"):
        (tmp_path / "tests" / kind).mkdir(parents=True)


def test_python_service_accepts_canonical_architecture(tmp_path: Path) -> None:
    make_python_service(tmp_path)

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and check["status"] == "passed" for check in report["checks"])


def test_service_rejects_forbidden_layer_dependency(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    source = tmp_path / "src" / "demo" / "orders" / "domain" / "rules.py"
    source.write_text("from demo.orders.adapters.outbound import database\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and check["status"] == "failed" and "запрещённого слоя" in check["message"]
        for check in report["checks"]
    )


def test_python_from_import_cannot_bypass_layer_boundary(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    source = tmp_path / "src" / "demo" / "orders" / "domain" / "rules.py"
    source.write_text("from demo.orders.adapters import outbound\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "запрещённого слоя" in check["message"]
        for check in report["checks"]
    )


def test_service_rejects_undeclared_source_module(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    source = tmp_path / "src" / "demo" / "billing" / "domain" / "rules.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "вне объявленного модуля" in check["message"]
        for check in report["checks"]
    )


def test_service_rejects_typescript_language(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    config = tmp_path / ".methodology.yml"
    config.write_text(config.read_text(encoding="utf-8").replace("python", "typescript"), encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "только python, go, rust" in check["message"]
        for check in report["checks"]
    )


def test_python_service_rejects_external_library_in_inner_layer(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    source = tmp_path / "src" / "demo" / "orders" / "application" / "handler.py"
    source.write_text("import sqlalchemy\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "внутренний слой импортирует внешнюю библиотеку" in check["message"]
        for check in report["checks"]
    )


def make_non_python_service(tmp_path: Path, language: str) -> None:
    (tmp_path / ".methodology.yml").write_text(
        "schema_version: 1\nrepository_type: service\nmethodology_ref: v1.0.0\n"
        f"service_name: demo\nservice_language: {language}\nservice_modules: orders\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "specs").mkdir()
    (docs / "specs" / "orders.md").write_text("# Orders\n", encoding="utf-8")
    root_path = "internal/orders/" if language == "go" else "src/orders/"
    (docs / "ARCHITECTURE.md").write_text(
        "# Архитектура\n\n## Модули\n\n"
        "| Модуль | Ответственность | Спецификация | Язык | Канонический корень | Проверка границ |\n"
        "|---|---|---|---|---|---|\n"
        f"| `orders` | Заказы | `docs/specs/orders.md` | {language} | `{root_path}` | VER-015 |\n",
        encoding="utf-8",
    )
    module = tmp_path / ("internal" if language == "go" else "src") / "orders"
    for parts in (
        ("domain",), ("application",), ("ports", "inbound"),
        ("ports", "outbound"), ("adapters", "inbound"), ("adapters", "outbound"),
    ):
        directory = module.joinpath(*parts)
        directory.mkdir(parents=True)
        filename = "mod.rs" if language == "rust" else "README.md"
        (directory / filename).write_text("// layer\n" if language == "rust" else "Layer.\n", encoding="utf-8")
    for kind in ("unit", "integration", "contract"):
        (tmp_path / "tests" / kind).mkdir(parents=True)
    if language == "go":
        (tmp_path / "go.mod").write_text("module example.test/demo\n", encoding="utf-8")
        main = tmp_path / "cmd" / "demo" / "main.go"
        main.parent.mkdir(parents=True)
        main.write_text("package main\nfunc main() {}\n", encoding="utf-8")
    else:
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        (module / "mod.rs").write_text(
            "pub mod domain;\npub mod application;\npub mod ports;\npub mod adapters;\n",
            encoding="utf-8",
        )
        (module / "ports" / "mod.rs").write_text(
            "pub mod inbound;\npub mod outbound;\n", encoding="utf-8"
        )
        (module / "adapters" / "mod.rs").write_text(
            "pub mod inbound;\npub mod outbound;\n", encoding="utf-8"
        )
        (tmp_path / "src" / "main.rs").write_text("fn main() {}\n", encoding="utf-8")


def test_go_service_accepts_canonical_architecture(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "go")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and check["status"] == "passed" for check in report["checks"])


def test_go_inner_layer_accepts_own_module_import(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "go")
    source = tmp_path / "internal" / "orders" / "application" / "handler.go"
    source.write_text(
        'package application\nimport "example.test/demo/internal/orders/ports/inbound"\n',
        encoding="utf-8",
    )

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and check["status"] == "passed" for check in report["checks"])


def test_rust_service_accepts_canonical_architecture(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "rust")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and check["status"] == "passed" for check in report["checks"])


def test_go_raw_import_cannot_bypass_external_dependency_rule(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "go")
    source = tmp_path / "internal" / "orders" / "domain" / "rules.go"
    source.write_text("package domain\nimport `gorm.io/gorm`\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "внутренний слой импортирует внешнюю библиотеку" in check["message"]
        for check in report["checks"]
    )


def test_rust_external_crate_call_without_use_is_rejected(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "rust")
    manifest = tmp_path / "Cargo.toml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + '\n[dependencies]\nsqlx = "1"\n', encoding="utf-8")
    source = tmp_path / "src" / "orders" / "domain" / "mod.rs"
    source.write_text('fn query() { sqlx::query("select 1"); }\n', encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "использует внешний crate sqlx" in check["message"]
        for check in report["checks"]
    )


def test_rust_standard_grouped_use_is_accepted(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "rust")
    source = tmp_path / "src" / "orders" / "domain" / "mod.rs"
    source.write_text("use std::{fmt, io};\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and check["status"] == "passed" for check in report["checks"])


def test_rust_ignores_external_crate_names_in_comments_and_strings(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "rust")
    manifest = tmp_path / "Cargo.toml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + '\n[dependencies]\nsqlx = "1"\n', encoding="utf-8")
    source = tmp_path / "src" / "orders" / "domain" / "mod.rs"
    source.write_text(
        '// sqlx::query("ignored");\n'
        '/* outer /* inner */ sqlx::query("ignored"); */\n'
        'const NOTE: &str = "sqlx::query";\n',
        encoding="utf-8",
    )

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and check["status"] == "passed" for check in report["checks"])


def test_service_rejects_noncanonical_module_table(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    architecture = tmp_path / "docs" / "ARCHITECTURE.md"
    architecture.write_text(
        "# Архитектура\n\n## Модули\n\n| Модуль | Роль |\n|---|---|\n| `orders` | Заказы |\n",
        encoding="utf-8",
    )

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "каноническим столбцам" in check["message"]
        for check in report["checks"]
    )


def test_python_composition_root_rejects_function_definitions(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    bootstrap = tmp_path / "src" / "demo" / "bootstrap.py"
    bootstrap.write_text("def business_rule():\n    return 1\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "управляющую логику" in check["message"]
        for check in report["checks"]
    )


def test_python_package_init_rejects_application_code(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    package_init = tmp_path / "src" / "demo" / "__init__.py"
    package_init.write_text("import sqlalchemy\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "разрешена только строка" in check["message"] for check in report["checks"])


def test_python_composition_root_rejects_arbitrary_call(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    bootstrap = tmp_path / "src" / "demo" / "bootstrap.py"
    bootstrap.write_text("delete_all_orders()\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "управляющую логику" in check["message"] for check in report["checks"])


def test_python_composition_root_rejects_factory_prefix_bypass(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    bootstrap = tmp_path / "src" / "demo" / "bootstrap.py"
    bootstrap.write_text("result = build_and_execute_business_logic()\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "управляющую логику" in check["message"] for check in report["checks"])


def test_go_composition_root_rejects_types_and_methods(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "go")
    main = tmp_path / "cmd" / "demo" / "main.go"
    main.write_text(
        "package main\ntype Rules struct{}\nfunc (Rules) Calculate() int { return 42 }\nfunc main() {}\n",
        encoding="utf-8",
    )

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "только func main" in check["message"] for check in report["checks"])


def test_rust_composition_root_rejects_types_and_impl(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "rust")
    main = tmp_path / "src" / "main.rs"
    main.write_text("struct Rules;\nimpl Rules { fn calculate() -> i32 { 42 } }\nfn main() {}\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "только fn main" in check["message"] for check in report["checks"])


def test_go_commented_import_cannot_bypass_dependency_rule(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "go")
    source = tmp_path / "internal" / "orders" / "domain" / "rules.go"
    source.write_text('package domain\nimport /* dependency */ "gorm.io/gorm"\n', encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "внутренний слой импортирует внешнюю библиотеку" in check["message"]
        for check in report["checks"]
    )


def test_rust_extern_crate_cannot_bypass_dependency_rule(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "rust")
    manifest = tmp_path / "Cargo.toml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + '\n[dependencies]\nsqlx = "1"\n', encoding="utf-8")
    source = tmp_path / "src" / "orders" / "domain" / "mod.rs"
    source.write_text("extern crate sqlx as db;\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "импортирует внешний crate sqlx" in check["message"]
        for check in report["checks"]
    )


def test_python_composition_root_rejects_conditional_assignment(tmp_path: Path) -> None:
    make_python_service(tmp_path)
    bootstrap = tmp_path / "src" / "demo" / "bootstrap.py"
    bootstrap.write_text("result = delete_all_orders() if should_delete else None\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "управляющую логику" in check["message"] for check in report["checks"])


def test_go_composition_root_rejects_control_flow(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "go")
    main = tmp_path / "cmd" / "demo" / "main.go"
    main.write_text('package main\nfunc main() { if true { println("business") } }\n', encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "только func main" in check["message"] for check in report["checks"])


def test_rust_composition_root_rejects_control_flow(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "rust")
    main = tmp_path / "src" / "main.rs"
    main.write_text('fn main() { if true { println!("business"); } }\n', encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "только fn main" in check["message"] for check in report["checks"])


def test_rust_target_dependency_is_rejected_in_inner_layer(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "rust")
    manifest = tmp_path / "Cargo.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + '\n[target.\'cfg(windows)\'.dependencies]\nsqlx = "1"\n',
        encoding="utf-8",
    )
    source = tmp_path / "src" / "orders" / "domain" / "mod.rs"
    source.write_text('#[cfg(windows)]\nfn query() { sqlx::query("select 1"); }\n', encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-015" and "внешний crate sqlx" in check["message"] for check in report["checks"])


def test_go_dotless_required_module_is_external(tmp_path: Path) -> None:
    make_non_python_service(tmp_path, "go")
    manifest = tmp_path / "go.mod"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "require corp/db v1.0.0\n", encoding="utf-8")
    source = tmp_path / "internal" / "orders" / "domain" / "rules.go"
    source.write_text('package domain\nimport "corp/db"\n', encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-015" and "внутренний слой импортирует внешнюю библиотеку" in check["message"]
        for check in report["checks"]
    )


def test_hub_requires_machine_task_matching_backlog(tmp_path: Path) -> None:
    make_hub(tmp_path)
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [ ] ready — Задача\n\nЦель:\nx\n\nГотово, когда:\n- x\n\nНе входит:\n- нет\n",
        encoding="utf-8",
    )

    report = run(tmp_path)

    assert any(check["id"] == "VER-012" and check["status"] == "failed" for check in report["checks"])


def test_hub_rejects_machine_task_not_generated_from_backlog(tmp_path: Path) -> None:
    make_hub(tmp_path)
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [ ] ready — Задача\n\n"
        "Целевой репозиторий: hub\nРиск: low\nАвтономность: auto-test-deploy\n"
        "Триггеры:\n- нет\n\nЦель:\nx\n\nГотово, когда:\n- x\n\nНе входит:\n- нет\n",
        encoding="utf-8",
    )
    sync(tmp_path)
    task_path = tmp_path / ".tasks" / "TASK-0001.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["target"] = "other"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-012"
        and check["status"] == "failed"
        and "не сгенерирована" in check["message"]
        for check in report["checks"]
    )


def test_done_task_requires_evidence(tmp_path: Path) -> None:
    make_hub(tmp_path)
    (tmp_path / "BACKLOG.md").write_text(
        "### TASK-0001. [x] — Задача\n\nЦель:\nx\n\nГотово, когда:\n- x\n\nНе входит:\n- нет\n",
        encoding="utf-8",
    )
    tasks = tmp_path / ".tasks"
    tasks.mkdir()
    (tasks / "TASK-0001.json").write_text(json.dumps({
        "schema_version": 1, "id": "TASK-0001", "status": "done", "target": "hub",
        "risk": "low", "autonomy": "auto-test-deploy", "goal": "x",
        "acceptance_criteria": ["x"], "out_of_scope": ["нет"]
    }), encoding="utf-8")

    report = run(tmp_path)

    assert any(check["id"] == "VER-013" and check["status"] == "failed" for check in report["checks"])


def test_evidence_schema_requires_digest_sources_and_reviewer() -> None:
    schema = json.loads((Path(__file__).parents[2] / "schemas/evidence.schema.json").read_text(encoding="utf-8"))
    invalid = {
        "schema_version": 1, "task_id": "TASK-0001", "run_id": "1",
        "repository": "https://github.com/acme/app",
        "pr": "https://github.com/acme/app/pull/1", "commit": "abcdef1",
        "methodology_ref": "v1.0.0", "checks": [{"name": "gate", "status": "passed"}],
        "reviews": [{"name": "review", "status": "passed", "source": "run:1"}],
        "attempts": 1, "artifact": "image:latest",
        "deployment": {"environment": "test", "probes": [{"name": "smoke", "status": "passed", "source": "run:1"}]},
        "status": "passed", "created_at": "2026-01-01T00:00:00Z", "retained_until": "2026-02-01T00:00:00Z"
    }

    errors = validate_json(invalid, schema)

    assert any("checks.0.source" in error for error in errors)
    assert any("reviews.0.reviewer" in error for error in errors)
    assert any("artifact" in error for error in errors)


def test_date_time_requires_full_rfc3339_timestamp() -> None:
    schema = {"type": "string", "format": "date-time"}

    assert validate_json("2026-01-01", schema)
    assert validate_json("2026-01-01T00:00:00", schema)
    assert validate_json("2026-01-01T00:00:00Z", schema) == []


def test_done_task_rejects_failed_evidence(tmp_path: Path) -> None:
    make_hub(tmp_path)
    backlog = (
        "### TASK-0001. [x] — Задача\n\nЦелевой репозиторий: hub\nРиск: low\n"
        "Автономность: auto-test-deploy\nТриггеры:\n- нет\n\nЦель:\nx\n\n"
        "Готово, когда:\n- x\n\nНе входит:\n- нет\n"
    )
    (tmp_path / "BACKLOG.md").write_text(backlog, encoding="utf-8")
    sync(tmp_path)
    evidence = tmp_path / ".evidence"
    evidence.mkdir()
    (evidence / "TASK-0001.json").write_text(json.dumps({
        "schema_version": 1, "task_id": "TASK-0001", "run_id": "1",
        "repository": "https://github.com/acme/app",
        "pr": "https://github.com/acme/app/pull/1", "commit": "abcdef1",
        "methodology_ref": "v1.0.0",
        "checks": [{"name": "gate", "status": "passed", "source": "run:1"}],
        "reviews": [], "attempts": 1, "artifact": "sha256:" + "a" * 64,
        "deployment": {"environment": "test", "probes": [
            {"name": "smoke", "status": "failed", "source": "run:1"}
        ]},
        "status": "failed", "created_at": "2026-01-01T00:00:00Z",
        "retained_until": "2026-02-01T00:00:00Z",
    }), encoding="utf-8")

    report = run(tmp_path)

    assert any(
        check["id"] == "VER-013" and check["status"] == "failed"
        and "требует evidence со статусом passed" in check["message"]
        for check in report["checks"]
    )


def test_done_task_rejects_evidence_without_passed_results_or_matching_pr(tmp_path: Path) -> None:
    make_hub(tmp_path)
    backlog = (
        "### TASK-0001. [x] — Задача\n\nЦелевой репозиторий: hub\nРиск: low\n"
        "Автономность: auto-test-deploy\nТриггеры:\n- нет\n\nЦель:\nx\n\n"
        "Готово, когда:\n- x\n\nНе входит:\n- нет\n"
    )
    (tmp_path / "BACKLOG.md").write_text(backlog, encoding="utf-8")
    sync(tmp_path)
    evidence = tmp_path / ".evidence"
    evidence.mkdir()
    na = {"name": "check", "status": "not_applicable", "source": "https://ci.example/run/1", "reason": "нет"}
    review = {**na, "name": "review", "reviewer": "agent"}
    (evidence / "TASK-0001.json").write_text(json.dumps({
        "schema_version": 1, "task_id": "TASK-0001", "repository": "https://github.com/acme/app",
        "run_id": "1", "pr": "https://github.com/other/app/pull/1", "commit": "abcdef1",
        "methodology_ref": "v1.0.0", "checks": [na], "reviews": [review], "attempts": 1,
        "artifact": "sha256:" + "a" * 64,
        "deployment": {"environment": "test", "probes": [na]}, "status": "passed",
        "created_at": "2026-01-01T00:00:00Z", "retained_until": "2026-02-01T00:00:00Z",
    }), encoding="utf-8")

    report = run(tmp_path)
    message = next(check["message"] for check in report["checks"] if check["id"] == "VER-013")
    assert "PR не принадлежит" in message
    assert "требует успешные check, review и deployment probe" in message


def test_task_schema_requires_diagnostic_for_diagnostic_status() -> None:
    schema = json.loads((Path(__file__).parents[2] / "schemas/task.schema.json").read_text(encoding="utf-8"))
    task = {
        "schema_version": 1, "id": "TASK-0001", "status": "needs-input", "target": "hub",
        "risk": "low", "autonomy": "auto-test-deploy", "goal": "x",
        "acceptance_criteria": ["x"], "out_of_scope": ["нет"], "triggers": [],
    }

    assert any("diagnostic" in error for error in validate_json(task, schema))
    task["diagnostic"] = "требуется решение"
    assert validate_json(task, schema) == []


def test_hub_composition_is_structurally_validated(tmp_path: Path) -> None:
    (tmp_path / "COMPOSITION.md").write_text(
        "# Состав программы\n\n## Сервисы\n\n"
        "| Сервис | Репозиторий | Версия/хеш | Роль | Публикует / Читает |\n"
        "|---|---|---|---|---|\n"
        "| api | https://github.com/acme/api | v1.2.3 | сервис-шлюз (`gateway`) | нет |\n\n"
        "## Интерфейсы\n\n"
        "| Интерфейс | Репозиторий | Версия/хеш | Визуализирует | Потребляет (сервис-шлюз/маршрут) |\n"
        "|---|---|---|---|---|\n"
        "| web | https://github.com/acme/web | abcdef1 | данные | api /v1/data |\n\n"
        "## Автономные компоненты\n\n"
        "| Компонент | Репозиторий | Версия/хеш | Форма | Назначение / поверхности |\n"
        "|---|---|---|---|---|\n"
        "| cli | https://github.com/acme/cli | sha256:" + "a" * 64 + " | cli | импорт |\n\n"
        "## Зависимости (DAG)\n\n```mermaid\ngraph LR\n api --> web\n```\n",
        encoding="utf-8",
    )

    errors, repositories = composition_errors(tmp_path)

    assert errors == []
    assert repositories == [
        "https://github.com/acme/api", "https://github.com/acme/web", "https://github.com/acme/cli"
    ]


def test_ci_commit_must_match_repository_head() -> None:
    repository = Path(__file__).parents[2]
    head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    assert commit_matches_head(repository, head)
    assert not commit_matches_head(repository, "0000000000000000000000000000000000000000")


def test_finalization_diff_allows_one_task_and_rejects_product_files(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / "BACKLOG.md").write_text("ready\n", encoding="utf-8")
    task_path = tmp_path / ".tasks/TASK-0001.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text(json.dumps({"id": "TASK-0001", "status": "ready"}), encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "initial"], check=True, capture_output=True)
    base = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()
    (tmp_path / "BACKLOG.md").write_text("done\n", encoding="utf-8")
    task_path.write_text(json.dumps({"id": "TASK-0001", "status": "done"}), encoding="utf-8")
    evidence = tmp_path / ".evidence/TASK-0001.json"
    evidence.parent.mkdir()
    evidence.write_text(json.dumps({"task_id": "TASK-0001"}), encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "finalize"], check=True, capture_output=True)

    assert finalization_diff_errors(tmp_path, base) == []

    (tmp_path / "product.py").write_text("print('unexpected')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "product"], check=True, capture_output=True)
    assert any("вне" in error for error in finalization_diff_errors(tmp_path, base))


def test_finalization_rejects_existing_evidence_and_done_task(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / "BACKLOG.md").write_text("done\n", encoding="utf-8")
    task = tmp_path / ".tasks/TASK-0001.json"
    task.parent.mkdir(parents=True)
    task.write_text(json.dumps({"id": "TASK-0001", "status": "done"}), encoding="utf-8")
    evidence = tmp_path / ".evidence/TASK-0001.json"
    evidence.parent.mkdir()
    evidence.write_text(json.dumps({"task_id": "TASK-0001", "status": "failed"}), encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "initial"], check=True, capture_output=True)
    base = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()
    (tmp_path / "BACKLOG.md").write_text("changed\n", encoding="utf-8")
    task.write_text(json.dumps({"id": "TASK-0001", "status": "done", "changed": True}), encoding="utf-8")
    evidence.write_text(json.dumps({"task_id": "TASK-0001", "status": "passed"}), encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "rewrite"], check=True, capture_output=True)

    errors = finalization_diff_errors(tmp_path, base)
    assert any("добавляться впервые" in error for error in errors)
    assert any("незавершённого" in error for error in errors)


def test_workflow_passes_pr_and_merge_commits_and_fetches_history() -> None:
    root = Path(__file__).parents[2]
    for kind in ("hub", "service", "interface", "standalone"):
        workflow = (root / "skeletons" / kind / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
        assert "fetch-depth: 0" in workflow
        assert "ref: ${{ github.event.pull_request.head.sha }}" in workflow
        assert '--commit "${{ github.event.pull_request.head.sha }}"' in workflow
        assert '--commit "${{ needs.merge.outputs.commit }}"' in workflow


def test_composition_requires_mermaid_inside_dependency_section(tmp_path: Path) -> None:
    (tmp_path / "COMPOSITION.md").write_text(
        "# Состав\n\n```mermaid\ngraph LR\nA --> B\n```\n\n"
        "## Сервисы\n\nнет\n\n## Интерфейсы\n\nнет\n\n"
        "## Автономные компоненты\n\nнет\n\n## Зависимости (DAG)\n\nДиаграмма отсутствует.\n",
        encoding="utf-8",
    )

    errors, _ = composition_errors(tmp_path)

    assert "раздел зависимостей должен содержать диаграмму Mermaid" in errors


def test_invalid_utf8_backlog_produces_failed_report(tmp_path: Path) -> None:
    make_hub(tmp_path)
    (tmp_path / "BACKLOG.md").write_bytes(b"\xff")

    report = run(tmp_path)

    assert report["status"] == "failed"
    assert any(
        check["id"] == "VER-006" and "невозможно прочитать" in check["message"]
        for check in report["checks"]
    )


def test_cli_writes_report_and_returns_failure_code(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "verification.json"
    monkeypatch.setattr(sys, "argv", ["verify.py", "--root", str(tmp_path), "--report", str(report)])

    assert main() == 1
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "failed"
