# Стеки (референс)

Микросервис реализуется на одном из четырёх стеков. Стек выбирается один раз
для всего репо — правило «один сервис = один язык». Здесь — **авторитетный**
toolchain, layout и команды для каждого. В `AGENTS.md` — компактная строка
выбранного стека (заполни одну), здесь — полная конфигурация.

> Перед стартом удали секции стеков, которые не выбраны, оставь один.
> Команды `lint / test / build` прогоняются перед коммитом — процедура в
> `docs/guide/40-verify.md`.

## Python

- **Runtime:** Python 3.12+.
- **Менеджер:** `uv` (только он).
- **Layout:** `src/<service>/`, `tests/`, `pyproject.toml`.
- **Линт:** `ruff` (формат + линтер).
- **Типы:** `pyright`.
- **Тесты:** `pytest`.
- **Сборка:** wheel через `uv build` (только через `uv`).

```
pyproject.toml
src/<service>/
  __init__.py
  __main__.py        # точка входа
tests/
uv.lock
```

Команды:

```
ruff format --check .
ruff check .
pyright
pytest
uv build
```

## Go

- **Runtime:** Go 1.22+.
- **Менеджер:** стандартные модули (`go.mod`).
- **Layout:** `cmd/<service>/main.go`, `internal/`, `pkg/` (если нужно).
- **Линт:** `gofmt`, `go vet` (`golangci-lint run` не нужен).
- **Тесты:** `go test ./...`.
- **Сборка:** `go build`.

```
go.mod
cmd/
  <service>/
    main.go          # точка входа
internal/            # приватный код сервиса
pkg/                 # (опц.) переиспользуемый код
bin/                 # артефакты сборки (gitignored)
```

Команды:

```
gofmt -l .           # пусто = ОК
go vet ./...
go test ./...
go build -o bin/<service> ./cmd/<service>
```

## Rust

- **Runtime:** Rust stable.
- **Менеджер:** `cargo`. Workspace опционален (`crates/`).
- **Layout:** один crate или workspace `crates/<name>`.
- **Линт:** `cargo fmt`, `cargo clippy`.
- **Тесты:** `cargo test`.
- **Сборка:** `cargo build --release`.

```
Cargo.toml
Cargo.lock
src/
  main.rs            # точка входа
  lib.rs             # (опц.)
tests/               # интеграционные
crates/              # (опц. workspace)
```

Команды:

```
cargo fmt --check
cargo clippy -- -D warnings
cargo test
cargo build --release
```

## TypeScript (бэкенд)

- **Runtime:** Node 24+ (только он).
- **Менеджер:** `pnpm` (только он).
- **Layout:** `src/`, `package.json`, `tsconfig.json`, `vitest`.
- **Линт:** ESLint (только он); типы через `tsc --noEmit`.
- **Тесты:** `vitest` (только он).
- **Сборка:** `tsc` (только он).

```
package.json
pnpm-lock.yaml
tsconfig.json
src/
  index.ts           # точка входа
tests/
```

Команды:

```
pnpm lint
tsc --noEmit
pnpm test
pnpm build
```

## Общие правила для всех стеков

- Команды `lint / test / build` — единый набор для репо; выбранную строку
  закрепи компактно в `AGENTS.md`.
- Lock-файлы коммитятся (`uv.lock`, `go.sum`, `Cargo.lock`, `pnpm-lock.yaml`),
  но не правятся руками; артефакты/кэши — в `.gitignore`.
- Зависимости добавляются с обоснованием в коммите/спеке.

## TypeScript (frontend / interface)

Интерфейс-репо — всегда React/TS (это не «один из 4 бэкенд-стеков», а отдельный
тип репо; выбора нет). Стек фиксирован ниже.

- **Runtime:** Node 24+ (сборка/тесты).
- **Менеджер:** `pnpm`.
- **Framework:** React + Vite.
- **Layout:** `src/` (components/pages/hooks/stores), `public/`,
  `package.json`, `tsconfig.json`, `vite.config.ts`. Раскладка —
  `docs/refs/LAYOUT.md` → *Interface layout*.
- **Линт:** ESLint; типы — `tsc --noEmit`.
- **Тесты:** vitest.
- **Сборка:** `vite build` → `dist/` (статика, раздаётся nginx/CDN;
  деплой — `docs/refs/DEPLOYMENT.md` → *interface*).

Команды:

```
pnpm lint
tsc --noEmit
pnpm test
pnpm build
```

> Внутренняя фронтенд-архитектура (компоненты/стейт) — на усмотрение
> (React-конвенции); `MODULE.md`/`SPEC.md` к интерфейсу **не применяются**
> (это бэкенд-канон). Что интерфейс обязан зафиксировать — манифест
> потребляемых эндпоинтов **gateway-сервиса** в `docs/ARCHITECTURE.md` (проверяет
> гейт-agent #15; интерфейс потребляет только gateway).