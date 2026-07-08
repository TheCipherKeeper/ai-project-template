# Раскладка каталогов (референс)

Один репо = один микросервис. Внутри сервиса — **workspace из модулей**
(«монорепо в рамках сервиса»): Rust `crates/`, Go — несколько пакетов под
`internal/`/`pkg/`, Python — подпакеты под `src/`, TypeScript — модули под
`src/`. Каждый модуль — отдельная спека в `docs/specs/<module>.md`.

> Это референс (факт «как должно лежать»). Процедура добавления модуля —
> пошагово в `docs/guide/20-define-module.md`. Канон структуры спеки —
> `docs/refs/SPEC.md`.

```
<service>/
  AGENTS.md                 точка входа агента: правила + указатель на INDEX
  README.md
  docker-compose.yml        локальная разработка: брокер + этот сервис
  .env.example              переменные окружения (копируется в .env)
  Dockerfile                образ этого сервиса
  .gitignore
  LICENSE  LICENSE-DOCS
  docs/
    INDEX.md                РОУТЕР: «ситуация → читай guide/N или refs/Y»
    ARCHITECTURE.md         рабочий артефакт: модули, брокер, потоки, граница
    BACKLOG.md              рабочий артефакт: очередь задач
    guide/                  фазы-плейбуки (самодостаточные)
      00-bootstrap.md  10-architecture.md  20-define-module.md
      30-implement-task.md  40-verify.md  50-deploy.md  60-adr.md
    refs/                   авторитетные факты (одна правда)
      STACKS.md  LAYOUT.md(этот файл)  DEPLOYMENT.md  VERIFICATION.md  SPEC.md
    specs/
      <module>.md           контракт модуля (по одному на модуль)
      EXAMPLE.md            # пример — удали
    adr/                    ADR (если нет хаба; иначе — в хабе)
  <workspace>/              модули сервиса — по layout выбранного стека:
                            crates/ (Rust), internal/ + pkg/ (Go),
                            src/<service>/ (Python), src/ (TS)
  <manifest>                pyproject.toml / go.mod / Cargo.toml / package.json
  <lock>                    uv.lock / go.sum / Cargo.lock / pnpm-lock.yaml
  shared/                   (опц.) общее внутри сервиса между модулями
```

## Модули и спеки

Каждый модуль workspace'а = отдельный спек `docs/specs/<module>.md` по
канонической структуре (см. `docs/refs/SPEC.md`). Модуль — это:

- Python: пакет/подпакет под `src/<service>/`.
- Go: пакет под `internal/` или `pkg/`.
- Rust: crate в `crates/` (если workspace) или модуль под `src/`.
- TypeScript: директория/модуль под `src/`.

## Где живут общие вещи

- Контракты модулей — `docs/specs/<module>.md`.
- Состав сервиса, модули, топики, потоки — `docs/ARCHITECTURE.md` (рабочий артефакт).
- Деплой (Dockerfile, структура compose, env) — `docs/refs/DEPLOYMENT.md`;
  запуск локально — `docs/guide/50-deploy.md`.
- Общее внутри сервиса между модулями — `shared/` (если нужно).
- Кросс-сервисные контракты (event envelope, состав программы, системный
  compose, ADR) — **в хабе**, не в этом репо.
- ADR — в хабе (cybercity) или в `docs/adr/` (standalone) — см. `docs/guide/60-adr.md`.