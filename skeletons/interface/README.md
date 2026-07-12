# <interface>

<!-- 1–2 предложения: что за интерфейс, какие визуализации, для какой части
     программы. Системный контекст — в хабе COMPOSITION.md; топология —
     в <methodology-repo>/docs/ARCHITECTURE.md. -->

**Стек:** React + TypeScript (Vite)
**Хаб:** <hub-repo>                          <!-- COMPOSITION/CONVENTIONS/системный compose -->

## Что делает

<!-- Нумерованный список: какие визуализации/страницы, какие сервисы/данные
     потребляет. -->

## Потребляемые сервисы

<!-- Детально — docs/ARCHITECTURE.md → «Потребление». Кратко здесь: -->

| Сервис | Эндпоинт | Версия | Назначение |
|---|---|---|---|
| `<service-a>` | `/v1/<endpoint>` | v1 | … |

## Разработка

Рабочий цикл и методология — в `<methodology-repo>/docs/` (роутер — `INDEX.md`).
Кратко:

```bash
pnpm dev                    # локальная разработка (Vite dev-сервер; без брокера)
# код + тесты; цикл — <methodology-repo>/docs/WORKFLOW.md
git commit -m "feat(ui): ..." && git push   # PR в main
```

Стабильные версии — тегами `vX.Y.Z` на `main`.

## Деплой

Статика: `pnpm build` → `dist/`, раздаётся nginx/CDN. Детали —
`<methodology-repo>/docs/OPERATIONS.md`.

## Лицензия

<!-- укажи лицензию кода -->
