# Конвенции общения микросервисов

Кросс-сервисный контракт: формат сообщений (event envelope) и общие правила.
Версиируются (`CONVENTIONS@vN`). Сервисы потребляют на пиннённой версии;
контракт выпущенной версии неизменен (новое — `@vN+1`).

> Скелет. Заполни под программу. Модель общения —
> `<methodology-repo>/docs/refs/COMMUNICATION.md`.

## Версия

- **Текущая:** `CONVENTIONS@v1`
- **Совместимость:** <!-- backward-compatible? required? -->
- **Breaking →** `@v2` отдельным PR; сервисы мигрируют каждый своим PR
  (бамп пина + правки). См. `AGENTS.md` → *Версионирование контрактов*.

## Event envelope

Общий формат сообщения в топике брокера. Все сервисы публикуют/читают его.

<!-- Заполни поля под программу. Пример ниже — заготовка. -->

```json
{
  "envelope_version": "1",
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
| `envelope_version` | int | да | версия envelope (соответствует `CONVENTIONS@vN`) |
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

- Общение — **только через брокер**; прямые service-to-service вызовы запрещены.
- Не изобретать свой envelope в сервисах — только этот.
- Backward-compatible изменения (новое опц. поле) — **без bump**: остаться
  `@vN` (старые consumer'ы не ломаются). Breaking — **major bump**:
  `@vN` → `@vN+1` (напр. `@v1` → `@v2`) отдельным PR. Схема целочисленная
  major-only (`@v1`, `@v2`, …) — minor-бампа нет.
- Idempotency: consumer дедуплирует по `event_id`.

## ADR-ссылки

- <!-- ADR-NNNN: почему выбрали Kafka/Redpanda/NATS -->
- <!-- ADR-NNNN: формат trace_id / схема версионирования -->