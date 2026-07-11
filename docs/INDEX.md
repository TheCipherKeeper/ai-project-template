# docs/INDEX — роутер документации

Точка входа в методологию. Найди свою ситуацию — открой один файл. Каждая фаза
`guide/` **самодостаточна**: читается одна. `refs/` — факты по запросу.

> Центральная методология (читается как гайд) + `skeletons/` (стартовые наборы
> для копирования). Хаб/сервисы — отдельные репо из `skeletons/`; этот репо —
> корень авторитета.

## Ситуация → читай (процедуры, per-service)

Фазы `docs/guide/00..70` — процедуры **сервис-репо**, читаемые из центра.
Лёгкая правка: где фраза подразумевает «этот репо», это «в репо сервиса».

| Мне нужно… | Читай |
|---|---|
| Войти в проект, поднять сервис с нуля | `docs/guide/00-bootstrap.md` |
| Описать архитектуру (роль, модули, брокер, топики, граница) | `docs/guide/10-architecture.md` |
| Добавить модуль / написать спеку | `docs/guide/20-define-module.md` |
| Спроектировать модуль изнутри (usecases/ports/domain/adapters) | `docs/guide/20-define-module.md` + `docs/refs/MODULE.md` |
| Взять задачу из бэклога и реализовать (рабочий цикл) | `docs/guide/30-implement-task.md` |
| Проверить перед коммитом (verification gate) | `docs/guide/40-verify.md` |
| Запустить локально (брокер + сервис) | `docs/guide/50-deploy.md` |
| Зафиксировать архитектурное решение (ADR) | `docs/guide/60-adr.md` |
| Выпустить версию (тег: pre-release / стабильная) | `docs/guide/70-release.md` |
| Создать интерфейс / описать визуализации (React/TS, потребление эндпоинтов gateway) | `skeletons/interface/` + `docs/refs/COMMUNICATION.md` → *gateway-сервис* / *Клиентский край* |
| Назначить gateway-сервис (единственный browser-facing surface) | инстанциация из `skeletons/service/` + `docs/refs/COMMUNICATION.md` → *gateway-сервис*; роль фиксируется в `COMPOSITION` хаба |
| Создать stub-таргет (standalone-программа; форма — контейнер/CLI/…; без брокера/presentation; out-of-band-наблюдение — при наличии поверхности) | `skeletons/stub/` + `docs/refs/COMMUNICATION.md` → *Stub-таргет* |
| Узнать правила работы над методологией (ветвление, можно/нельзя, docs-verify, коммиты, язык) | `AGENTS.md` |

## Системный уровень → refs/

| Факт | Референс |
|---|---|
| Структура репозиториев: хаб + N сервисов + M интерфейсов + K stub-таргетов; что где живёт; ADR home; edge-модель | `docs/refs/TOPOLOGY.md` |
| Общение микросервисов: брокер, event envelope, без прямой связности; stub-таргет — standalone-программа, out-of-band-наблюдение при наличии поверхности | `docs/refs/COMMUNICATION.md` |
| Verification gate: рёбра, conformance/behavioral, полный чеклист, применимость по типу репо | `docs/refs/VERIFICATION.md` |
| Автономный цикл: без человека в pre-deploy; ревьюер — агент; человек — бэклог + баги из тест/прода | `docs/refs/PIPELINE.md` |

## Per-service факты → refs/

| Факт | Референс |
|---|---|
| Toolchain, layout, команды стека (Python/Go/Rust/TS) | `docs/refs/STACKS.md` |
| Раскладка каталогов сервиса (workspace модулей) | `docs/refs/LAYOUT.md` |
| Внутренняя архитектура модуля (usecases/ports/domain/adapters) | `docs/refs/MODULE.md` |
| Структура compose, Dockerfile, env | `docs/refs/DEPLOYMENT.md` |
| Канон структуры спеки (7 секций) | `docs/refs/SPEC.md` |

## Инстанциация → skeletons/

| Хочу… | Беру |
|---|---|
| Создать хаб-репо (системные контракты, состав, compose) | `skeletons/hub/` |
| Создать сервис-репо (AGENTS, README, compose, env, Dockerfile, docs/) | `skeletons/service/` |
| Создать interface-репо (React/TS, визуализации, потребление эндпоинтов gateway) | `skeletons/interface/` |
| Назначить gateway-сервис (browser-facing, из сервисов) | `skeletons/service/` (роль gateway — в `COMPOSITION` хаба) |
| Создать stub-репо (standalone-программа; форма — контейнер/CLI/…; без брокера/presentation) | `skeletons/stub/` |

Скелеты копируются в новый репо целиком; хаб/сервисы/интерфейсы/stub-таргеты **не
несут** guide/refs, а ссылаются на этот репо методологии
(`<methodology-repo>/docs/...`).

## Рабочие артефакты (в сервис-репо, не здесь)

| Артефакт | Что |
|---|---|
| `docs/ARCHITECTURE.md` | Архитектура сервиса: модули, брокер, потоки, граница |
| `docs/BACKLOG.md` | Очередь задач (строгая, сверху вниз) |
| `docs/specs/<module>.md` | Контракты модулей — по одному на модуль |
| `COMPOSITION.md` / `CONVENTIONS.md` | Состав программы и event envelope (в хабе) |
| `<hub>/adr/` | ADR программы — в хабе (см. `docs/refs/TOPOLOGY.md`) |

## Принципы

- Фаза `guide/N-*.md` читается **одна**: заголовок-блок
  (Цель / Когда / Что нужно до / Шаги / Канон / Что после) + инлайн-минимум.
- Факты — в `refs/` (одна правда). Фаза ссылается на refs, не дублирует.
- `skeletons/` — стартовые наборы, не авторитет фактов (авторитет — `refs/`).
- Приоритет **по ярусам** и арбитраж (внутри-ярусное противоречие — дефект, не
  «старший побеждает»; методология эволюционирует коммитами без ADR) —
  `AGENTS.md` → *Документация (приоритет)*.