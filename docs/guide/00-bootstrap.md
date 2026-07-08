# Фаза 00 — Войти в проект (bootstrap)

**Цель:** от пустого клона шаблона к скелету сервиса, готовому к разработке.

**Когда:** первый вход в репо — человеком или агентом.

**Что нужно до:** ничего. Это входная фаза.

## Шаги

1. **Создать репо из шаблона.** Кнопка *Use this template* на GitHub, либо
   клонировать и оторвать историю:
   ```bash
   git checkout --orphan main && git add -A && git commit -m "init"
   ```
2. **Выбрать стек** (один на сервис): Python / Go / Rust / TypeScript.
   Правило: один сервис — один язык.
   - В `docs/refs/STACKS.md` удали секции невыбранных стеков, оставь одну.
   - В `AGENTS.md` → *Команды проверки* закрепи компактную строку выбранного стека.
3. **Переименовать плейсхолдеры** `<service>` под имя сервиса: в
   `docker-compose.yml`, `Dockerfile` (когда заведёшь), манифесте
   (`pyproject.toml` / `go.mod` / `Cargo.toml` / `package.json`), `.env.example`.
4. **Завести workspace модулей** по layout выбранного стека
   (`docs/refs/LAYOUT.md`): Rust `crates/`, Go `internal/`+`pkg/`,
   Python `src/<service>/`, TypeScript `src/`.
5. **Завести первые спеки.** Удали `docs/specs/EXAMPLE.md`, заведи
   `docs/specs/<module>.md` по канону (`docs/refs/SPEC.md`). Подробно — фаза 20.
6. **Прогнать `lint / test / build`** выбранного стека (команды —
   `docs/refs/STACKS.md`). Должны запускаться (пусть даже на пустом скелете).

## Канон (где правда)

- `docs/refs/STACKS.md` — toolchain, layout, команды стека.
- `docs/refs/LAYOUT.md` — раскладка каталогов сервиса.
- `docs/refs/SPEC.md` — структура спеки.

## Что после

- `docs/guide/10-architecture.md` — описать сервис (роль, модули, брокер, топики).
- Затем `docs/guide/20-define-module.md` — детально по каждому модулю.