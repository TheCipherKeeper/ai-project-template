# Машиночитаемые контракты — справочник

Markdown объясняет смысл; wire-контракт задаётся схемой. HTTP/WS gateway
описывается OpenAPI, события — AsyncAPI и JSON Schema/Protobuf/Avro. Схемы
живут в хабе, имеют владельца и проверяются на совместимость в CI.

Для события обязательны: имя и версия, producer/consumers, payload schema,
partition/ordering key, delivery semantics, idempotency key, retry/DLQ,
максимальный размер, retention, PII-класс и compatibility policy.

Breaking contract требует отдельной задачи, ADR, плана миграции consumers и
`BREAKING CHANGE:`. Producer/consumer contract tests блокируют merge. Новый
producer не публикуется раньше совместимых consumers; удаление поля выполняется
через период совместимости.

