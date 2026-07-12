# AGENTS.md — интерфейс

Клиентское приложение. Рабочий цикл —
`<methodology-repo>/docs/WORKFLOW.md`, системные границы —
`<methodology-repo>/docs/ARCHITECTURE.md`.

## Правила

- Выполняй только текущую задачу из `<hub>/BACKLOG.md`.
- Работай через `feat/TASK-NNNN-<slug>` и PR; прямой commit в `main` запрещён.
- Интерфейс обращается только к зарегистрированному browser-facing gateway.
- Обновляй UI, тесты и `docs/ARCHITECTURE.md` вместе.
- Не храни секреты в клиентской сборке и репозитории.
- Доступность, состояния loading/empty/error и проверка прав входят в review
  применимых изменений.
- `.env`, lock-файлы и зависимости не меняй без разрешения.
- Placeholder/TODO не считается готовым результатом.

## Проверка

```bash
pnpm lint && tsc --noEmit
pnpm test
pnpm build
```

Дополнительно запускаются verifier методологии и триггерные проверки из
`<methodology-repo>/docs/REFERENCE.md`. Интеграция — squash merge; test deploy
идентифицируется commit SHA.
