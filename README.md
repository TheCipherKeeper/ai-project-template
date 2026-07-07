# AI Microservice Template

[![Template](https://img.shields.io/badge/repo-template-blueviolet)](#)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](LICENSE-DOCS)

Универсальная заготовка-первоисточник для **одного микросервиса**, который
можно реализовать на одном из стеков: **Python**, **Go**, **Rust** или
**TypeScript** (бэкенд, не фронтенд). Методология и команды подстраиваются
под выбранный стек — без привязки к конкретному языку.

Содержит методологию, а не код: иерархию документов, модель ветвления,
рабочий цикл, каноническую структуру спеков и ADR. Клонируй, выбери стек,
подставь команды — и работай по одним правилам с людьми и агентами.

## Что внутри

```
AGENTS.md             правила работы (для людей и агентов)
docs/INDEX.md         карта документации, точка входа
docs/ARCHITECTURE.md  архитектура сервиса (скелет-плейсхолдер)
docs/BACKLOG.md       очередь задач
docs/STACKS.md        toolchain/layout/команды по стекам
docs/LAYOUT.md        раскладка каталогов репозитория
docs/specs/           контракты модулей (по одному файлу на модуль)
docs/adr/             архитектурные решения (ADR)
```

## Быстрый старт

1. Создай репо из шаблона (кнопка *Use this template* на GitHub) или склонируй
   и оторви историю: `git checkout --orphan main && git add -A && git commit -m "init"`.
2. **Выбери стек** (один на весь репо): Python / Go / Rust / TypeScript.
3. В `AGENTS.md` закрепи строки команд выбранного стека в таблице *Команды
   проверки по стеку*. В `docs/STACKS.md` удали секции невыбранных стеков.
4. Заполни `docs/ARCHITECTURE.md` и `docs/BACKLOG.md` под свой сервис.
5. Удали `docs/specs/EXAMPLE.md` и создавай спеки под свои модули (как соотнести
   модуль с каталогами стека — в `docs/LAYOUT.md`).

## Документация

| Файл | Что |
|---|---|
| `AGENTS.md` | Правила работы: ветвление, коммиты, что можно/нельзя, команды по стекам |
| `docs/INDEX.md` | Карта документации |
| `docs/ARCHITECTURE.md` | Архитектура: слои, потоки данных, доверительная граница |
| `docs/BACKLOG.md` | Очередь задач |
| `docs/STACKS.md` | Toolchain, layout и команды для Python/Go/Rust/TS |
| `docs/LAYOUT.md` | Раскладка каталогов репозитория |
| `docs/specs/` | Контракты модулей (по одному файлу на модуль) |
| `docs/adr/` | Архитектурные решения (ADR) |

## Разработка

```bash
git checkout dev
git pull
git checkout -b feat/<задача>

# внести изменения
lint      # см. команды выбранного стека в AGENTS.md / docs/STACKS.md
test
build

git commit -m "feat: ..."
git push
# открыть PR в dev
```

Полный цикл — в `AGENTS.md`. Задачи — в `docs/BACKLOG.md`.

## Лицензия

- Код: [MIT](LICENSE)
- Документация: [CC BY 4.0](LICENSE-DOCS)