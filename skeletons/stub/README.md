# <stub>

<!-- 1–2 предложения: назначение автономного компонента и его место в системе.
     Системный контекст — в хабе COMPOSITION.md; топология —
     в <methodology-repo>/docs/ARCHITECTURE.md. -->

**Стек:** <Python | Go | Rust | TypeScript>   <!-- один на компонент -->
**Хаб:** <hub-repo>                           <!-- COMPOSITION/CONVENTIONS/системный compose/ADR -->
**form:** <container | cli | …>                <!-- способ поставки компонента -->

## Что делает

<!-- Нумерованный список: что за standalone-программа, какая форма (form), что
     изображает/делает, чем параметризуется (параметры из control-plane). Если
     наблюдаются — какие поверхности и как collector наблюдает их out-of-band. -->

## Поверхности (если наблюдаются)

<!-- Таблица — только когда есть наблюдаемая поверхность (тогда collector
     наблюдает её out-of-band). Поверхность/протокол/порт/назначение. Это не
     presentation-эндпоинты для интерфейсов. -->

| Поверхность | Протокол | Порт | Назначение |
|---|---|---|---|
| `<surface>` | TCP/SSH/HTTP | … | … |

## Разработка

Рабочий цикл и методология — в `<methodology-repo>/docs/` (роутер — `INDEX.md`).
Кратко:

```bash
git checkout main && git pull && git checkout -b feat/<задача>
# код/конфиг; цикл — <methodology-repo>/docs/WORKFLOW.md
git commit -m "feat(banner): ..." && git push   # PR в main
```

Стабильные версии — тегами `vX.Y.Z` на `main`.

## Локальный запуск

<!-- По форме. Для form=container: -->

```bash
cp .env.example .env && docker compose up --build   # этот stub-контейнер (без брокера)
```

<!-- Для form=cli: команда запуска артефакта/сборки. -->

Эксплуатация — `<methodology-repo>/docs/OPERATIONS.md` (для `form=container` —
контейнер-цель, брокера в окружении нет; для CLI — артефакт/сборка).

## Лицензия

<!-- укажи лицензию кода -->
