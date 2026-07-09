# <stub>

<!-- 1–2 предложения: что за stub-таргет, какую поверхность изображает, в какой части
     программы. Системный контекст — в хабе COMPOSITION.md; топология —
     в <methodology-repo>/docs/refs/TOPOLOGY.md. -->

**Стек:** <Python | Go | Rust | TypeScript>   <!-- один на stub -->
**Хаб:** <hub-repo>                           <!-- COMPOSITION/CONVENTIONS/системный compose/ADR -->
**runtime_kind:** lite (passive target; наблюдается out-of-band, не broker-клиент)

## Что делает

<!-- Нумерованный список: какие сетевые поверхности/баннеры изображает, чем
     параметризуется (дескриптор из manage), как наблюдается collector'ом. -->

## Поверхности

<!-- Таблица: поверхность / протокол / порт / назначение. Это пассивные сетевые
     поверхности stub-таргета (raw TCP/SSH/HTTP-баннер и т.п.), не presentation-
     эндпоинты для интерфейсов. -->

| Поверхность | Протокол | Порт | Назначение |
|---|---|---|---|
| `<surface>` | TCP/SSH/HTTP | … | … |

## Разработка

Рабочий цикл и методология — в `<methodology-repo>/docs/` (роутер — `INDEX.md`).
Кратко:

```bash
git checkout main && git pull && git checkout -b feat/<задача>
# код/конфиг; проверка перед коммитом — <methodology-repo>/docs/guide/40-verify.md
git commit -m "feat(banner): ..." && git push   # PR в main
```

Стабильные версии — тегами `vX.Y.Z` на `main`.

## Локальный запуск

```bash
cp .env.example .env && docker compose up --build   # этот stub-контейнер (без брокера)
```

Процедура — `<methodology-repo>/docs/guide/50-deploy.md` (stub — контейнер-цель,
брокера в окружении нет).

## Лицензия

<!-- укажи лицензию кода -->