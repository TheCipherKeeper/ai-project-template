# <project> — хаб

Хаб микросервисной программы: системные контракты и состав. Методология —
в `<methodology-repo>/docs/` (роутер — `INDEX.md`); топология репозиториев —
`<methodology-repo>/docs/refs/TOPOLOGY.md`, общение микросервисов —
`<methodology-repo>/docs/refs/COMMUNICATION.md`.

## Что в хабе

| Файл | Что |
|---|---|
| `COMPOSITION.md` | Состав программы: сервисы + интерфейсы, их репо, зависимости, edge-реестр |
| `CONVENTIONS.md` | Event envelope и кросс-сервисные конвенции (версионируется `@vN`) |
| `docker-compose.yml` | Системный compose: все сервисы + брокер |
| `adr/` | Архитектурные решения (дом ADR по умолчанию) |

## Сервисы программы

<!-- Заполни по мере добавления. Каждый сервис — отдельный репо (инстанциация
     из <methodology-repo>/skeletons/service/). -->

| Сервис | Репо | Роль | Пин контракта |
|---|---|---|---|
| `<service-a>` | <repo-url> | … | `CONVENTIONS@v1` |

## Интерфейсы программы

<!-- Каждый интерфейс — отдельный репо (инстанциация из
     <methodology-repo>/skeletons/interface/). Интерфейс — клиент на границе,
     зовёт presentation-эндпоинты сервисов. -->

| Интерфейс | Репо | Визуализирует | Потребляет |
|---|---|---|---|
| `<interface-a>` | <repo-url> | … | `<service-a> /v1/...` |

## Разработка

```bash
git checkout main && git pull && git checkout -b feat/<задача>
# правки COMPOSITION/CONVENTIONS/compose; проверка перед коммитом
git commit -m "feat(conventions): ..."
git push        # PR в main
```

Стабильные версии — тегами `vX.Y.Z` на `main`. Правила — `AGENTS.md`.

## Лицензия

<!-- укажи лицензию -->