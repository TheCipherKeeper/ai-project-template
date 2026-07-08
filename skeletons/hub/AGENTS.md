# AGENTS.md — правила работы в хаб-репозитории

Точка входа для людей и AI-агентов в **репозитории хаба**. Хаб хранит
системные контракты: `COMPOSITION.md` (состав программы), `CONVENTIONS.md`
(event envelope, кросс-сервисные конвенции), системный `docker-compose.yml`,
`adr/`. Процедуры/факты методологии — в `<methodology-repo>/docs/`.

> Хаб — родительский узел в edge-модели верификации: активно ребро **вниз**
> (`хаб → все сервисы`) — все сервисы проверяются на соответствие хабу. И ребро
> **вверх** (`методология → хаб`) — хаб соответствует методологии. См.
> `<methodology-repo>/docs/refs/VERIFICATION.md`.

## Документация (приоритет)

Методология (`<methodology-repo>/docs/`) → этот `AGENTS.md` → `COMPOSITION.md` /
`CONVENTIONS.md` / `adr/` → код (если есть).

## Модель ветвления

```
main            ← PR из feature-веток
feat/<задача>   ← от main, удаляется после merge
vX.Y.Z          ← тег на main (стабильная версия)
```

- Прямой коммит в `main` — **запрещён**. Только feature-ветка + PR.
- Релизы — тегами `vX.Y.Z` на `main`; release-ветки не заводятся.

## Что можно

- Редактировать `COMPOSITION.md` (состав программы — добавлять/удалять сервисы).
- Редактировать `CONVENTIONS.md` (event envelope, кросс-сервисные конвенции) —
  с версионированием (`@vN`); bump major — отдельным PR + координированный
  апдейт сервисов (см. ниже).
- Менять системный `docker-compose.yml` (все сервисы + брокер).
- Заводить ADR в `adr/` (хаб — дом ADR по умолчанию).
- Создавать feature-ветки, PR в `main`, теги.

## Что нельзя

- Коммитить напрямую в `main`; заводить `dev`/release-ветки.
- Менять контракт `CONVENTIONS@vN` задним числом (уже выпущенная версия
  неизменна; новое — `@vN+1`). Иначе сервисы на пине `@vN` ломаются.
- Хранить здесь код сервисов или их рабочие артефакты (ARCHITECTURE/BACKLOG/
  specs) — это в сервис-репо.
- Вводить прямую service-to-service связность в обход брокера в
  `COMPOSITION`/`CONVENTIONS` — общение только через брокер
  (`<methodology-repo>/docs/refs/COMMUNICATION.md`).

## Версионирование контрактов (обязательно)

- `CONVENTIONS.md` экспонирует версии: `CONVENTIONS@v1`, `@v2`, …
- Сервисы пинят версию; гейт проверяет сервис против пина, не HEAD.
- Breaking change в `CONVENTIONS` → bump major (`@vN+1`) отдельным PR;
  сервисы мигрируют каждый своим PR (бамп пина + правки). Не атомарно —
  потому и нужен pin (см. `<methodology-repo>/docs/refs/VERIFICATION.md`).

## Коммиты

Conventional Commits. Scope — `composition`/`conventions`/`deploy`/`docs`.

```
feat(conventions): add trace_id to event envelope @v2
fix(composition): register new billing service
docs: link ADR-0007 from COMPOSITION
```

Breaking changes контракта — `BREAKING CHANGE:` в теле + bump версии.

## Язык

Документация — русский (или поменяй). Английский — для идентификаторов,
`Status:` в ADR, summary-строки коммита.