# AI Microservice Template

[![Template](https://img.shields.io/badge/repo-template-blueviolet)](#)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](LICENSE-DOCS)

**Методологический шаблон для одного микросервиса.** Содержит методологию и
скелеты документов, **а не код приложения**. Один репо = один сервис; внутри
сервис может быть workspace'ом из нескольких модулей (как `crates/`), у
каждого модуля своя спека.

Сервис, который ты построишь из шаблона, реализуется на **одном** из стеков
(Python / Go / Rust / TypeScript), работает клиентом **брокера**
(Kafka/Redpanda/NATS) и деплоится **контейнером**. Но **этот репо** —
заготовка-первоисточник: иерархия документов, модель ветвления, рабочий цикл,
канон спеков, ADR, раскладка workspace'а, модель деплоя. Клонируй, выбери стек —
и работай по одним правилам с людьми и агентами.

> **Программа целиком** (несколько сервисов + хаб + системный compose +
> COMPOSITION/CONVENTIONS/ADR) живёт **в хабе** и в отдельных репо сервисов.
> Этот шаблон описывает один сервис, не всю систему. Сколько сервисов —
> столько инстанциаций шаблона, по репо на каждый.

## Как пользоваться

1. Создай репо из шаблона (кнопка *Use this template*) или склонируй и оторви
   историю: `git checkout --orphan main && git add -A && git commit -m "init"`.
2. Открой **`docs/INDEX.md`** — роутер «ситуация → читай». Это точка входа в
   методологию; дальше он ведёт сам.
3. Иди по фазам `docs/guide/`, начиная с `docs/guide/00-bootstrap.md`
   (выбор стека → workspace → первые спеки → архитектура).

Методология — **пошаговая и модульная**: фазы-плейбуки самодостаточны, каждую
можно взять одну и выполнить, не читая остальные. Факты — в `docs/refs/`,
правила — в `AGENTS.md`.

## Что в шаблоне, а что заведёшь сам

**Есть в шаблоне (сейчас):**

- `AGENTS.md` — правила работы: ветвление, что можно/нельзя, коммиты, язык,
  команды выбранного стека.
- `docs/INDEX.md` — роутер.
- `docs/guide/00..70` — фазы-плейбуки (bootstrap → architecture → module →
  task → verify → deploy → adr → release).
- `docs/refs/` — `STACKS` / `LAYOUT` / `DEPLOYMENT` / `VERIFICATION` / `SPEC`
  (авторитетные факты, одна правда).
- `docs/ARCHITECTURE.md`, `docs/BACKLOG.md`, `docs/specs/EXAMPLE.md` —
  скелеты-артефакты (заполни под свой сервис).
- `docs/adr/` — мета-ADR + шаблон.
- `docker-compose.yml`, `.env.example` — скелеты локального окружения.

**Заведёшь под сервис (по фазам):**

- `Dockerfile`, `<workspace>/` модулей, `<manifest>`
  (`pyproject.toml` / `go.mod` / `Cargo.toml` / `package.json`) — фаза 00.
- Заполненные `docs/ARCHITECTURE.md`, `docs/BACKLOG.md`, `docs/specs/<module>.md`
  — фазы 10 / 20 / 30.

## Разработка и запуск (в репозитории сервиса, не в шаблоне)

> Команды ниже — для **инстанцированного** репо сервиса. В самом шаблоне нет
> кода и `Dockerfile`, поэтому они здесь не запустятся.

Полный рабочий цикл — `docs/guide/30-implement-task.md`:

```bash
git checkout main && git pull && git checkout -b feat/<задача>
# код + тесты; проверка перед коммитом — docs/guide/40-verify.md
git commit -m "feat(<module>): ..."
git push        # открыть PR в main
```

Стабильные версии — тегами `vX.Y.Z` на `main` (`docs/guide/70-release.md`),
без release-веток.

Локальный запуск (брокер + сервис) — `docs/guide/50-deploy.md`:

```bash
cp .env.example .env && docker compose up --build
```

Системный compose и кросс-сервисные контракты — в хабе, не здесь.

## Лицензия

- Код: [MIT](LICENSE)
- Документация: [CC BY 4.0](LICENSE-DOCS)