# AI Microservice Methodology

[![Type: methodology](https://img.shields.io/badge/type-methodology-blueviolet)](#)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](LICENSE-DOCS)

**Общая методология построения микросервисного проекта** — читается как
пошаговый структурный гайд и служит центральным первоисточником правил для
хаба и сервисов. Это **не код приложения** и **не один микросервис**: это
методология того, **как** строить систему из хаба и сервисов, как общаются
микросервисы и как ведётся per-service рабочий цикл. Хаб и сервисы
инстанцируются из `skeletons/` отдельными репо и ссылаются сюда за правилами.

## Что здесь

- **`docs/guide/`** — процедуры-плейбуки по фазам (bootstrap → architecture →
  module → task → verify → deploy → adr → release). **Пошаговые и модульные**:
  каждая фаза самодостаточна, читается одна, без чтения остальных.
- **`docs/refs/`** — авторитетные факты (одна правда, без дублирования).
  Включает **уровень системы**: `TOPOLOGY` (структура репозиториев: хаб +
  N сервисов), `COMMUNICATION` (общение микросервисов: брокер, event
  envelope, пин контрактов), `VERIFICATION` (verification gate, edge-модель),
  плюс per-service: `STACKS` / `LAYOUT` / `DEPLOYMENT` / `SPEC`.
- **`skeletons/service/`** — стартовый набор сервис-репо: `AGENTS`, `README`,
  `docker-compose.yml`, `.env.example`, `Dockerfile`, `.gitignore`,
  `docs/{ARCHITECTURE,BACKLOG,specs/,adr/}`. Копируется → новый сервис-репо.
- **`skeletons/hub/`** — стартовый набор хаб-репо: `AGENTS`, `README`,
  `COMPOSITION.md` (состав программы + edge-реестр), `CONVENTIONS.md`
  (event envelope, версионируется `@vN`), системный `docker-compose.yml`,
  `adr/`. Копируется → хаб-репо.
- **`AGENTS.md`** — правила работы над **самой методологией** (ветвление,
  docs-verify, коммиты, можно/нельзя для доков/скелетов).
- **`docs/INDEX.md`** — роутер «ситуация → читай».

## Модель (M1 — центральная методология)

```
этот репо (методология)   читается — корень авторитета
   │  edge «вниз»: методология → хаб
   ▼
хаб-репо (из skeletons/hub)   COMPOSITION / CONVENTIONS / системный compose / ADR
   │  edge «вниз»: хаб → сервисы
   ▼
сервис-репо ×N (из skeletons/service)   код, спеки, ARCHITECTURE/BACKLOG/adr
```

- **Этот репо** не инстанцируется как сервис и не содержит кода приложения.
  Хаб и сервисы ссылаются на `docs/guide/...` и `docs/refs/...` здесь, **не
  копируя** их к себе (правила читаются из авторитета, не из копии — см.
  `docs/refs/VERIFICATION.md`).
- **Сервис-репо** — клиент брокера (Kafka/Redpanda/NATS, один на систему),
  реализуется на одном стеке (Python/Go/Rust/TS), деплоится контейнером;
  внутри может быть workspace'ом модулей («монорепо в рамках сервиса»), у
  каждого своя спека.
- **Хаб-репо** хранит системные контракты (`CONVENTIONS@vN`) и состав
  программы (`COMPOSITION`); сервисы пинят версию контракта, гейт проверяет
  сервис против пина.

## Как пользоваться

### Построить систему (хаб + сервисы)

1. Создай **хаб-репо**: скопируй `skeletons/hub/` в новый репо.
2. Заполни `COMPOSITION.md` (сервисы программы) и `CONVENTIONS.md` (event
   envelope) в хабе. Выбери брокер в системном `docker-compose.yml`.
3. Создай **сервис-репо** на каждого сервиса: скопируй `skeletons/service/` в
   новый репо. Выбери стек (фаза `docs/guide/00-bootstrap.md`), заполни
   `ARCHITECTURE.md` (фаза 10), спеки (фаза 20), работай по фазе 30.
4. Стабильные версии — тегами `vX.Y.Z` на `main` в каждом репо (фаза 70).

### Разобраться в методологии

1. Открой **`docs/INDEX.md`** — роутер «ситуация → читай».
2. Системный уровень (топология, общение) — `docs/refs/TOPOLOGY.md`,
   `docs/refs/COMMUNICATION.md`.
3. Per-service рабочий цикл — фазы `docs/guide/00..70`, начиная с
   `docs/guide/00-bootstrap.md`.

Методология — **пошаговая и модульная**: фазы-плейбуки самодостаточны, каждую
можно взять одну и выполнить, не читая остальные. Факты — в `docs/refs/`,
правила — в `AGENTS.md`.

## Разработка (в репозитории методологии)

```bash
git checkout main && git pull && git checkout -b feat/<задача>
# правка guide/refs/skeletons; docs-verify перед коммитом — AGENTS.md → "Проверка перед коммитом"
git commit -m "docs(guide): ..."
git push        # PR в main
```

Прямой коммит в `main` запрещён; интеграция — только PR. Стабильные версии —
тегами `vX.Y.Z` (`docs/guide/70-release.md`), без release-веток.

Команды запуска сервисов/хаба — в **инстанцированных** репо (там есть код и
`Dockerfile`); в этом репо их нет.

## Лицензия

- Код (скелеты, конфиги): [MIT](LICENSE)
- Документация: [CC BY 4.0](LICENSE-DOCS)