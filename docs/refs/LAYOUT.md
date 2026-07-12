# Структура каталогов — справочник

**Один репозиторий содержит один микросервис.** Код сервиса разделён на модули
(«монорепо в рамках сервиса»): Rust `src/`, Go — несколько пакетов под
`internal/`/`pkg/`, Python — подпакеты под `src/`, TypeScript — модули под
`src/`. Каждый модуль — отдельная спека в `docs/specs/<module>.md`.

> Раскладка **инстанцированного** сервис-репо (после копирования
> `skeletons/service/`; стартовые файлы — в `skeletons/service/` этого репо).
> Референс (факт «как должно лежать»). Процедура добавления модуля —
> `docs/guide/20-define-module.md`; канон спеки — `docs/refs/SPEC.md`;
> **внутренняя архитектура модуля (usecases/ports/domain/adapters) —
> `docs/refs/MODULE.md`**; топология репозиториев — `docs/refs/TOPOLOGY.md`.

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
    specs/
      <module>.md           контракт модуля (по одному на модуль)
      EXAMPLE.md            # пример — удали
  <workspace>/              модули сервиса — по layout выбранного стека:
                            src/ (Rust), internal/ + pkg/ (Go),
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
- `docs/ARCHITECTURE.md`, `docs/specs/EXAMPLE.md` — скелеты рабочих артефактов.
  ADR — в хабе (`<hub>/adr/`), в сервис-репо не копируется. Бэклог — в хабе
  (`<hub>/BACKLOG.md`), в сервис-репо не копируется.

Код, `<workspace>/`, `<manifest>`, `<lock>` — заводятся под выбранный стек по
этапу `docs/guide/00-bootstrap.md`.

## Модули и спеки

Каждый модуль workspace'а = отдельный спек `docs/specs/<module>.md` по
канонической структуре (см. `docs/refs/SPEC.md`). Модуль — это:

- Python: пакет/подпакет под `src/<service>/`.
- Go: пакет под `internal/` или `pkg/`.
- Rust: модуль под `src/`. Workspace `crates/` — только через ADR
  (`docs/guide/60-adr.md`), как отклонение от канона.
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
- ADR — в хабе (`<hub>/adr/`) — см. `docs/guide/60-adr.md`.

## Структура пользовательского интерфейса

Раскладка **interface-репо** (React/TS; инстанцируется из `skeletons/interface/`,
отдельный тип репо — не сервис). Внутренняя фронтенд-архитектура (компоненты/
стейт) — на усмотрение (React-конвенции); `MODULE.md`/`SPEC.md` **не
применяются** (это бэкенд-канон).

```
<interface>/              # инстанцированный interface-репо
  AGENTS.md                точка входа: правила + указатель на методологию
  README.md
  .env.example             VITE_API_* (URL presentation-эндпоинтов gateway-сервиса)
  .gitignore
  docs/
    ARCHITECTURE.md        манифест потребления: эндпоинты gateway, страницы/роуты
  src/                     React: main.tsx, pages/, components/, hooks/, stores/
  public/
  package.json
  tsconfig.json
  vite.config.ts
  pnpm-lock.yaml
  dist/                    # артефакт сборки (gitignored)
```

- **`docs/ARCHITECTURE.md`** — обязательный: таблица потребляемых эндпоинтов
  **gateway-сервиса** (`gateway | эндпоинт | версия | назначение`) + страницы/роуты.
  Это то, что сверяет гейт-agent #14 (`docs/refs/VERIFICATION.md`) с `ARCHITECTURE`
  **gateway** (единственного browser-facing surface). Интерфейс потребляет только
  gateway, не прочие сервисы.
- Брокера, `Dockerfile`-сервиса, `specs` здесь **нет** — это не сервис. Бэклог —
  в хабе (`<hub>/BACKLOG.md`), как у всех репо программы.

## Структура автономного компонента

Структура репозитория автономного компонента (создаётся из `skeletons/stub/`,
отдельный тип репо — не сервис, не интерфейс). Форма — параметр из control-plane
(`form`: контейнер / CLI / …); внутренняя структура — на усмотрение под выбранный
стек; `MODULE.md`/`SPEC.md` **не применяются** (stub параметризуется, не
вариантами использования). Модель — `docs/refs/COMMUNICATION.md` → *Автономный компонент*.

```
<stub>/                  # репозиторий автономного компонента из skeletons/stub/
  AGENTS.md               точка входа: stub-правила + указатель на методологию
  README.md
  Dockerfile              # опц. — при form=container: образ stub-цели (не root)
  docker-compose.yml      # опц. — при form=container: локально этот stub (БЕЗ брокера)
  .env.example            дескриптор/id (без BROKER_ADDR)
  .gitignore
  docs/
    ARCHITECTURE.md       форма stub'а, поверхности (если наблюдаются), доверительная граница, деплой
  <workspace>/            реализация — на усмотрение под стек и форму
                          (Rust crates/, Go internal/, Python src/, TS src/)
  <manifest>              Cargo.toml / go.mod / pyproject.toml / package.json
  <lock>                  Cargo.lock / go.sum / uv.lock / pnpm-lock.yaml
```

- **`docs/ARCHITECTURE.md`** — обязательный: форма stub'а (`form`), таблица
  поверхностей **если наблюдаются** (`поверхность | протокол | порт | назначение`),
  параметризация дескриптором, доверительная граница, деплой. **Без** секций
  Брокер/топики/presentation.
- Брокера, `specs`, presentation-эндпоинтов здесь **нет** — stub не участник
  общения и не сервис. Бэклог — в хабе (`<hub>/BACKLOG.md`), как у всех.
  Хаб-контракт к stub неприменим (нет потребления envelope).
- Скелет — `skeletons/stub/`; модель stub'а в системе —
  `docs/refs/COMMUNICATION.md` → *Автономный компонент*; применимость инвариантов —
  `docs/refs/VERIFICATION.md` → *Применимость инвариантов по типу репо*.
