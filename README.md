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

Содержит методологию, а не код: иерархию документов, модель ветвления,
рабочий цикл, каноническую структуру спеков, ADR, раскладку workspace'а и
модель деплоя. Клонируй, выбери стек — и работай по одним правилам с людьми и агентами.

## Что внутри

```
AGENTS.md               правила работы (для людей и агентов)
README.md
docker-compose.yml      локальная разработка: брокер + этот сервис
.env.example            переменные окружения
Dockerfile              образ этого сервиса
docs/
  INDEX.md              карта документации, точка входа
  ARCHITECTURE.md       архитектура сервиса: модули, брокер, потоки, граница
  BACKLOG.md            очередь задач
  STACKS.md             toolchain/layout/команды по стекам
  LAYOUT.md             раскладка каталогов репозитория сервиса
  DEPLOYMENT.md         Dockerfile + локальный compose + ссылка на хаб-деплой
  VERIFICATION.md       verification gate: соответствие канону на каждый коммит
  specs/<module>.md     контракты модулей (по одному на модуль)
  adr/                  архитектурные решения (или в хабе — см. AGENTS.md)
<workspace>/            модули сервиса — по layout выбранного стека
<manifest>              pyproject.toml / go.mod / Cargo.toml / package.json
```

## Быстрый старт

1. Создай репо из шаблона (кнопка *Use this template* на GitHub) или склонируй
   и оторви историю: `git checkout --orphan main && git add -A && git commit -m "init"`.
2. **Выбери стек** (один на сервис): Python / Go / Rust / TypeScript.
3. В `AGENTS.md` закрепи строки команд выбранного стека в таблице *Команды
   проверки по стеку*. В `docs/STACKS.md` удали секции невыбранных стеков.
4. Заведи модули сервиса (workspace: `crates/` / пакеты / `src/`-модули) —
   по одному спеку на модуль в `docs/specs/`. Удали `docs/specs/EXAMPLE.md`.
5. Опиши топики сервиса (publish/consume) в `docs/ARCHITECTURE.md` → *Брокер*.
   Формат event envelope — в хабе `CONVENTIONS.md`.
6. Заполни `docs/ARCHITECTURE.md` и `docs/BACKLOG.md` под свой сервис.

## Документация

| Файл | Что |
|---|---|
| `AGENTS.md` | Правила работы: ветвление, коммиты, что можно/нельзя, команды по стекам |
| `docs/INDEX.md` | Карта документации |
| `docs/ARCHITECTURE.md` | Архитектура сервиса: модули, брокер, потоки, граница доверия |
| `docs/BACKLOG.md` | Очередь задач |
| `docs/STACKS.md` | Toolchain, layout и команды для Python/Go/Rust/TS |
| `docs/LAYOUT.md` | Раскладка каталогов репозитория сервиса |
| `docs/DEPLOYMENT.md` | Dockerfile, локальный compose, ссылка на хаб-деплой |
| `docs/VERIFICATION.md` | Verification gate: проверка соответствия канону на каждый коммит |
| `docs/specs/` | Контракты модулей (по одному файлу на модуль) |
| `docs/adr/` | Архитектурные решения (ADR) |

## Разработка

```bash
git checkout dev
git pull
git checkout -b feat/<задача>

# внести изменения
lint      # команды выбранного стека — AGENTS.md / docs/STACKS.md
test
build

git commit -m "feat(<module>): ..."
git push
# открыть PR в dev
```

Локальный запуск (брокер + этот сервис):

```bash
cp .env.example .env
docker compose up --build
```

Полный цикл — в `AGENTS.md`. Задачи — в `docs/BACKLOG.md`. Деплой — в
`docs/DEPLOYMENT.md`. Системный compose и кросс-сервисные контракты — в хабе.

## Лицензия

- Код: [MIT](LICENSE)
- Документация: [CC BY 4.0](LICENSE-DOCS)