# Раскладка каталогов сервиса (референс)

**Один репо = один микросервис.** Внутри сервиса — **workspace из модулей**
(«монорепо в рамках сервиса»): Rust `crates/`, Go — несколько пакетов под
`internal/`/`pkg/`, Python — подпакеты под `src/`, TypeScript — модули под
`src/`. Каждый модуль — отдельная спека в `docs/specs/<module>.md`.

> Раскладка **инстанцированного** сервис-репо (после копирования
> `skeletons/service/`; стартовые файлы — в `skeletons/service/` этого репо).
> Референс (факт «как должно лежать»). Процедура добавления модуля —
> `docs/guide/20-define-module.md`; канон спеки — `docs/refs/SPEC.md`;
> топология репозиториев — `docs/refs/TOPOLOGY.md`.

```
<service>/                 # инстанцированный сервис-репо (из skeletons/service/)
  AGENTS.md                 точка входа агента: правила + указатель на методологию
  README.md
  docker-compose.yml        локальная разработка: брокер + этот сервис
  .env.example              переменные окружения (копируется в .env)
  Dockerfile                образ этого сервиса
  .gitignore
  LICENSE  LICENSE-DOCS
  docs/
    ARCHITECTURE.md         рабочий артефакт: модули, брокер, потоки, граница
    BACKLOG.md              рабочий артефакт: очередь задач
    specs/
      <module>.md           контракт модуля (по одному на модуль)
      EXAMPLE.md            # пример — удали
    adr/                    ADR сервиса (если нет хаба; иначе — в хабе)
  <workspace>/              модули сервиса — по layout выбранного стека:
                            crates/ (Rust), internal/ + pkg/ (Go),
                            src/<service>/ (Python), src/ (TS)
  <manifest>                pyproject.toml / go.mod / Cargo.toml / package.json
  <lock>                    uv.lock / go.sum / Cargo.lock / pnpm-lock.yaml
  shared/                   (опц.) общее внутри сервиса между модулями
```

> Сервис-репо **не несёт** `guide/` и `refs/` — процедуры/факты читаются из
> репо методологии (`<methodology-repo>/docs/guide/...`,
> `<methodology-repo>/docs/refs/...`), не копируются. Правила — в
> `skeletons/service/AGENTS.md`.

## Что копируется из skeletons/service/

При инстанциации нового сервис-репо из `skeletons/service/` берутся:

- `AGENTS.md`, `README.md` — правила/обзор сервис-репо (ссылки на методологию).
- `docker-compose.yml`, `.env.example`, `Dockerfile`, `.gitignore` — стартовое
  окружение.
- `docs/ARCHITECTURE.md`, `docs/BACKLOG.md`, `docs/specs/EXAMPLE.md` — скелеты
  рабочих артефактов.
- `docs/adr/_TEMPLATE.md`, `docs/adr/0001-record-architecture-decisions.md` —
  ADR.

Код, `<workspace>/`, `<manifest>`, `<lock>` — заводятся под выбранный стек по
фазе `docs/guide/00-bootstrap.md`.

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
  compose, ADR) — **в хабе**, не в этом репо (`docs/refs/TOPOLOGY.md`,
  `docs/refs/COMMUNICATION.md`).
- ADR — в хабе или в `docs/adr/` (standalone) — см. `docs/guide/60-adr.md`.