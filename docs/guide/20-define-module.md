# Фаза 20 — Добавить модуль / написать спеку

**Цель:** добавить модуль в workspace и описать его контракт спекой.

**Когда:** при заведении нового модуля; перед изменением кода в существующем
модуле (когда спеки ещё нет).

**Что нужно до:** фаза 10 (модуль есть в таблице `docs/ARCHITECTURE.md`).

## Шаги

1. **Каталог модуля** по layout выбранного стека (`docs/refs/LAYOUT.md`):
   - Python: пакет/подпакет под `src/<service>/`.
   - Go: пакет под `internal/` или `pkg/`.
   - Rust: crate в `crates/` (workspace) или модуль под `src/`.
   - TypeScript: директория/модуль под `src/`.
2. **Внутренняя структура модуля** по канону usecase-архитектуры
   (`docs/refs/MODULE.md`): `usecases/` + `ports/` + `domain/` + `adapters/`.
   Каждый юзкейс — input port + handler; output ports — в `ports/`, их
   реализации — в `adapters/`. Публичный API модуля = реэкспорт input ports.
3. **Регистрация в манифесте/конфиге workspace'а**, если требует стек:
   Cargo workspace (`[workspace] members`), `tsconfig.json` paths,
   `pyproject` packages, и т.п.
4. **Спека** `docs/specs/<module>.md` по канону (`docs/refs/SPEC.md`) — по
   юзкейсам: «Интерфейсы» = перечень юзкейсов (input port + потребляемые output
   ports); «Что есть/Что TODO» — per-usecase. Копируемый шаблон —
   `docs/specs/EXAMPLE.md`.
5. **Строка в таблице модулей** `docs/ARCHITECTURE.md` (если ещё нет).
6. **Топики** — если модуль публикует/читает топики, отметить в разделе
   «Брокер» `docs/ARCHITECTURE.md`.

## Канон (где правда)

- `docs/refs/MODULE.md` — швы и направление зависимостей модуля.
- `docs/refs/SPEC.md` — структура спеки + чек-лист.
- `docs/refs/LAYOUT.md` — модуль ↔ каталог выбранного стека.
- `docs/ARCHITECTURE.md` — таблица модулей и раздел «Брокер».

## Что после

- `docs/guide/30-implement-task.md` — взять пункт из «Что TODO» (через BACKLOG)
  и реализовать.