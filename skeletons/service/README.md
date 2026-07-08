# <service>

<!-- 1–2 предложения: что за сервис, какую роль в программе играет.
     Системный контекст — в хабе COMPOSITION.md; топология репозиториев —
     в <methodology-repo>/docs/refs/TOPOLOGY.md. -->

**Стек:** <Python | Go | Rust | TypeScript>  <!-- один на сервис -->
**Брокер:** <Kafka | Redpanda | NATS>       <!-- один на систему; клиент -->
**Хаб:** <hub-repo>                          <!-- COMPOSITION/CONVENTIONS/системный compose/ADR -->

## Что делает

<!-- Нумерованный список ключевых функций. -->

## Модули

<!-- Таблица модулей workspace'а; детали — docs/ARCHITECTURE.md. -->

| Модуль | Роль | Топики (publish/consume) |
|---|---|---|
| `<module>` | … | … |

## Разработка

Рабочий цикл и методология — в `<methodology-repo>/docs/` (роутер — `INDEX.md`).
Кратко:

```bash
git checkout main && git pull && git checkout -b feat/<задача>
# код + тесты; проверка перед коммитом — <methodology-repo>/docs/guide/40-verify.md
git commit -m "feat(<module>): ..."
git push        # PR в main
```

Стабильные версии — тегами `vX.Y.Z` на `main`. Задачи — `docs/BACKLOG.md`.

## Локальный запуск

```bash
cp .env.example .env && docker compose up --build   # брокер + этот сервис
```

Процедура — `<methodology-repo>/docs/guide/50-deploy.md`.

## Лицензия

<!-- укажи лицензию кода -->