# AI Microservice Template

[![Template](https://img.shields.io/badge/repo-template-blueviolet)](#)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](LICENSE-DOCS)

Универсальная заготовка-первоисточник для **одного микросервиса**. Один репо =
один сервис. Внутри сервис может быть **workspace'ом из нескольких модулей**
(«монорепо в рамках сервиса» — как `crates/`), у каждого модуля своя спека.

Сервис реализуется на **одном** из стеков: Python, Go, Rust или TypeScript
(бэкенд). Сервис — клиент **брокера** (Kafka/Redpanda/NATS): публикует и
читает топики. Деплоится **контейнером** со своим `Dockerfile`; для локальной
разработки в репо есть `docker-compose.yml` (брокер + этот сервис).

> **Программа целиком** (несколько сервисов + хаб + системный compose +
> COMPOSITION/CONVENTIONS/ADR) живёт **в хабе** и в отдельных репо сервисов.
> Этот шаблон описывает **один сервис**, не всю систему. Сколько сервисов —
> столько инстанциаций шаблона, по репо на каждый.

Методология — **пошаговая и модульная**: набор самодостаточных фаз-плейбуков
(`docs/guide/`), каждую можно взять одну и выполнить, не читая остальные.
Факты вынесены в тонкие референсы (`docs/refs/`), роутер — `docs/INDEX.md`.
Клонируй, выбери стек — и работай по одним правилам с людьми и агентами.

## Что внутри

```
AGENTS.md               точка входа агента: правила + указатель на INDEX
README.md
docker-compose.yml      локальная разработка: брокер + этот сервис
.env.example             переменные окружения
Dockerfile               образ этого сервиса
docs/
  INDEX.md              РОУТЕР: «ситуация → читай guide/N или refs/Y»
  guide/                фазы-плейбуки (самодостаточные):
    00-bootstrap.md          вход в проект
    10-architecture.md       описать архитектуру
    20-define-module.md      добавить модуль / спеку
    30-implement-task.md     рабочий цикл
    40-verify.md             проверка перед коммитом
    50-deploy.md             запуск локально
    60-adr.md                записать решение
  refs/                 авторитетные факты (одна правда):
    STACKS.md  LAYOUT.md  DEPLOYMENT.md  VERIFICATION.md  SPEC.md
  ARCHITECTURE.md       рабочий артефакт: модули, брокер, потоки, граница
  BACKLOG.md            рабочий артефакт: очередь задач
  specs/<module>.md     контракты модулей (по одному на модуль)
  adr/                  архитектурные решения (или в хабе — см. guide/60)
<workspace>/            модули сервиса — по layout выбранного стека
<manifest>              pyproject.toml / go.mod / Cargo.toml / package.json
```

## Быстрый старт

Подробно — `docs/guide/00-bootstrap.md`. Кратко:

1. Создай репо из шаблона (кнопка *Use this template*) или склонируй и оторви
   историю: `git checkout --orphan main && git add -A && git commit -m "init"`.
2. **Выбери стек** (один на сервис) — закрепи строку команд в `AGENTS.md`,
   удали лишние секции в `docs/refs/STACKS.md`.
3. Заведи модули (`docs/guide/20-define-module.md`) и опиши архитектуру
   (`docs/guide/10-architecture.md`).

## Документация

| Файл | Что |
|---|---|
| `docs/INDEX.md` | Роутер: «ситуация → читай» |
| `AGENTS.md` | Правила: ветвление, что можно/нельзя, коммиты, язык, команды стека |
| `docs/guide/` | Фазы-плейбуки (00–60): процедуры по шагам, каждая самодостаточна |
| `docs/refs/` | Референсы: STACKS/LAYOUT/DEPLOYMENT/VERIFICATION/SPEC (факты) |
| `docs/ARCHITECTURE.md` | Архитектура сервиса (рабочий артефакт) |
| `docs/BACKLOG.md` | Очередь задач (рабочий артефакт) |
| `docs/specs/` | Контракты модулей (по одному файлу на модуль) |
| `docs/adr/` | ADR (если нет хаба; иначе — в хабе) |

## Разработка

Полный рабочий цикл — `docs/guide/30-implement-task.md`. Кратко:

```bash
git checkout dev && git pull && git checkout -b feat/<задача>
# внести изменения; проверка перед коммитом — docs/guide/40-verify.md
git commit -m "feat(<module>): ..."
git push
# открыть PR в dev
```

Локальный запуск (брокер + этот сервис) — `docs/guide/50-deploy.md`:

```bash
cp .env.example .env
docker compose up --build
```

Задачи — в `docs/BACKLOG.md`. Деплой — в `docs/guide/50-deploy.md` +
`docs/refs/DEPLOYMENT.md`. Системный compose и кросс-сервисные контракты — в хабе.

## Лицензия

- Код: [MIT](LICENSE)
- Документация: [CC BY 4.0](LICENSE-DOCS)