# Архитектура сервиса

> Заполни фактическое состояние. Канон —
> `<methodology-repo>/docs/ARCHITECTURE.md`; цикл изменений —
> `<methodology-repo>/docs/WORKFLOW.md`.

## Назначение и граница

- Ответственность сервиса: TODO.
- Чем сервис не занимается: TODO.
- Почему это самостоятельный сервис, а не модуль: TODO.
- Владелец данных: TODO.

## Стек и поставка

- Язык/runtime: TODO.
- Команды проверки: TODO.
- Артефакт и порт: TODO.
- Readiness/healthcheck: TODO.

## Модули

| Модуль | Ответственность | Спека |
|---|---|---|
| `example` | TODO | `docs/specs/EXAMPLE.md` |

Небольшой модуль не создаёт пустые слои ради формы. Для сложной доменной логики
явно отделяются domain/application/adapters и направления зависимостей.

## Контракты

| Тип | Имя/route/topic | Версия | Направление | Schema/tests |
|---|---|---|---|---|
| TODO | TODO | TODO | consume/produce/serve | TODO |

Асинхронные события используют общий envelope хаба. Синхронная зависимость
указывает timeout, retries, failure mode и причину, по которой событие не подходит.

## Доверительная граница

- Аутентификация и авторизация: TODO.
- Недоверенный ввод: TODO.
- Секреты и персональные данные: TODO.
- Внешние зависимости: TODO.

## Данные и отказоустойчивость

- Хранилища и транзакционные границы: TODO.
- Idempotency/deduplication: TODO.
- Timeout/retry/dead-letter: TODO.
- Порядок миграции и rollback/roll-forward: TODO или N/A.

## Наблюдаемость

- Логи, метрики, tracing: TODO.
- Readiness и smoke-сценарий: TODO.
- Основные alerts/SLO: TODO.
