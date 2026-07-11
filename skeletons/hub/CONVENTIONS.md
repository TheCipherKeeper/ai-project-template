# Конвенции общения микросервисов

Кросс-сервисный контракт: формат сообщений (event envelope) и общие правила.
Сервисы потребляют текущий `CONVENTIONS` (без версионирования — см.
`<methodology-repo>/docs/refs/COMMUNICATION.md`).

> Скелет. Заполни под программу. Модель общения —
> `<methodology-repo>/docs/refs/COMMUNICATION.md`.

## Event envelope

Общий формат сообщения в топике брокера. Все сервисы публикуют/читают его.

<!-- Заполни поля под программу. Пример ниже — заготовка. -->

```json
{
  "event_type": "<service>.<domain>.<action>",
  "event_id": "<uuid>",
  "occurred_at": "<RFC3339>",
  "producer": "<service>",
  "trace_id": "<uuid>",
  "payload": { }
}
```

| Поле | Тип | Обяз. | Назначение |
|---|---|---|---|
| `event_type` | string | да | тип события; пространство имён = `<service>.<domain>.<action>` |
| `event_id` | uuid | да | идемпотентность (consumer дедуплирует по нему) |
| `occurred_at` | RFC3339 | да | когда событие произошло (не когда опубликовано) |
| `producer` | string | да | сервис-источник |
| `trace_id` | uuid | опц. | сквозная трассировка |
| `payload` | object | да | данные события; схема по `event_type` |

## Топики

- Именование: `<domain>.<event>` (например `billing.invoice_created`).
- Сервис владеет топиками, которые публикует; consumer — подписывается.
- Реестр топиков по сервисам — `COMPOSITION.md` → *Сервисы*.

## Правила

- Общение — **только через брокер**; прямые service-to-service вызовы
  (включая `gateway → сервис`) запрещены. (`Интерфейс → gateway-сервис` по
  HTTP/WS — разрешено; это клиентский край, не service-to-service.)
- **browser-facing presentation-эндпоинты** (HTTP/WS для интерфейсов) живут
  **только** на gateway-сервисе; presentation-API versioning — на gateway (одно
  место, не per-service). Прочие сервисы presentation для интерфейсов не держат.
- Не изобретать свой envelope в сервисах — только этот.
- Idempotency: consumer дедуплирует по `event_id`.

## ADR-ссылки

- <!-- ADR-NNNN: почему выбрали Kafka/Redpanda/NATS -->
- <!-- ADR-NNNN: формат trace_id -->