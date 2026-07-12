# AGENTS.md — сервис

Репозиторий одного независимо поставляемого сервиса. Общий цикл —
`<methodology-repo>/docs/WORKFLOW.md`, архитектурные правила —
`<methodology-repo>/docs/ARCHITECTURE.md`.

## Правила

- Выполняй только текущую задачу из `<hub>/BACKLOG.md`.
- Работай в `feat/TASK-NNNN-<slug>` через PR; прямой commit в `main` запрещён.
- Один сервис использует один основной язык.
- По умолчанию добавляй модуль, а не новый сервис.
- Обновляй код, тесты, `docs/ARCHITECTURE.md` и применимые спеки вместе.
- Публичные API/events имеют versioned schema и contract tests.
- Секреты, `.env` и lock-файлы не меняй без разрешения.
- ADR хранится только в `<hub>/adr/` и нужен для труднообратимого системного
  решения.
- Placeholder/TODO явно помечается и не считается готовым результатом.

## Команды

Оставь одну строку выбранного стека и удали остальные.

| Стек | Проверка | Тест | Сборка |
|---|---|---|---|
| Python | `ruff format --check . && ruff check . && pyright` | `pytest` | `uv build` |
| Go | `gofmt -l . && go vet ./...` | `go test ./...` | `go build ./...` |
| Rust | `cargo fmt --check && cargo clippy -- -D warnings` | `cargo test` | `cargo build --release` |
| TypeScript | `pnpm lint && tsc --noEmit` | `pnpm test` | `pnpm build` |

Перед merge обязателен verifier методологии, команды выбранного стека и
применимые проверки из `<methodology-repo>/docs/REFERENCE.md`.

## Git

Conventional Commits со scope модуля или `deploy`/`docs`; squash merge после
зелёного гейта. Test deployment идёт по commit SHA. Тег выпуска создаётся только
отдельной задачей.
