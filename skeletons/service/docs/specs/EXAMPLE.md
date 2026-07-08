# <модуль>

> Пример канонической структуры спеки. Скопируй под свой модуль, удали этот
> блок-комментарий. Спек описывает контракт (что), не реализацию (как).
> Канон структуры (7 секций) и чек-лист — `<methodology-repo>/docs/refs/SPEC.md`;
> **внутренняя архитектура модуля (usecases/ports/domain/adapters) —
> `<methodology-repo>/docs/refs/MODULE.md`**; процедура заведения модуля —
> `<methodology-repo>/docs/guide/20-define-module.md`. Модуль = каталог
> выбранного стека (см. `<methodology-repo>/docs/refs/LAYOUT.md`); команды проверки —
> в `AGENTS.md` → *Команды проверки (выбранный стек)*.

Краткое описание модуля: какую роль играет, какие границы ответственности.

## Интерфейсы

> **Юзкейсы** модуля. На каждый — input port (сигнатура `execute(In) -> Out`/
> ошибки) и потребляемые output ports (из `ports/`, см. `<methodology-repo>/docs/refs/MODULE.md`).

- `CreateThing.execute(input: CreateThingInput) -> Result<Thing, ModuleError>` —
  основной юзкейс. Потребляет output ports: `ThingRepo`, `EventPublisher`.

## Типы

> Доменные типы и per-usecase DTO в синтаксисе выбранного стека. Rust ниже —
> пример; для Python/Go/TS замени на свои type/interface/dataclass/Protocol.

```rust
pub enum ModuleError {
    NotAllowed(String),
    InvalidInput(String),
    Io(std::io::Error),
}

pub struct Thing { /* доменная сущность */ }

pub struct CreateThingInput { /* DTO входа юзкейса */ }
```

## Что есть

> Реализованное, **по юзкейсам**. Каждый пункт → тест.

- `CreateThing`: валидация входа → сохранение через `ThingRepo` → публикация
  события через `EventPublisher` → возврат `Thing`.
- Валидация: отклонение невалидного входа.
- Тест: `create_thing_rejects_invalid_input` (проверяет …).

## Что TODO

> Не реализовано, по юзкейсам. Переезжает в «Что есть» по мере реализации,
> из `BACKLOG` ставится `[x]`.

- `CreateThing`: идемпотентность по ключу запроса.
- Юзкейс `UpdateThing` — целиком (input port + handler).

## Ограничения

- Только через output ports: никаких прямых обращений к adapters из usecases.
- …

## Зависимости

> Output ports + внутренние модули + внешние библиотеки выбранного стека.

- `ports::ThingRepo`, `ports::EventPublisher`
- <модуль-core>, <runtime/логирование>