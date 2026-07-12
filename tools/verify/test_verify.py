from pathlib import Path

import json

from verify import markdown_files, non_mermaid_diagrams, run, validate_json


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
        "| Модуль | Ответственность | Спека | Язык | Канонический корень | Проверка границ |\n"
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
        "| Модуль | Ответственность | Спека | Язык | Канонический корень | Проверка границ |\n"
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
