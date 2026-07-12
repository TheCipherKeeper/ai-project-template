# Эксплуатация и выпуски

## Test deployment

Каждый слитый change разворачивается в test по commit SHA или digest артефакта.
Тег RC для этого не нужен. Перед завершением задачи обязательны readiness, smoke
и дополнительные probes, выбранные по триггерам задачи.

Минимальный evidence:

```yaml
task: TASK-0042
commit: abc1234
methodology: v1.0.0
checks:
  gate: passed
  review: passed
deployment:
  environment: test
  artifact: sha256:...
  smoke: passed
```

Evidence создаётся автоматикой, не содержит секретов и хранится как CI artifact
или ссылка из результата задачи.

Один evidence-объект обязательно содержит task, run, commit, точный
`methodology_ref`, результаты checks и reviews, число попыток, artifact digest,
deployment probes и итоговый статус. Для неприменимой проверки записывается
`not_applicable` с причиной.

## Эксплуатационный минимум

- Контейнер собирается multistage, запускается не от root и содержит только
  runtime-артефакты и зависимости.
- Перед deploy проходят `docker compose config`, сборка образа и dependency/
  secret scan.
- Компонент определяет liveness/readiness, graceful shutdown, structured logs,
  correlation/trace ID, основные метрики и режим деградации.
- Consumer определяет idempotency, retry с backoff, poison-message handling и
  DLQ.
- Внешние порты открываются только намеренно; browser-facing порты принадлежат
  gateway.
- После deploy выполняются readiness, smoke, применимые probes и окно
  наблюдения. Провал блокирует завершение задачи.

## Миграции данных

Изменение persisted data требует совместимого порядка rollout, резервной копии
или проверенного roll-forward, dry run на сопоставимых данных и проверки старой
и новой версии приложения. Разрушающее удаление выполняется отдельной задачей
после периода совместимости.

## Rollback

До deploy агент проверяет, что предыдущий digest доступен и конфигурация с ним
совместима. Если откат данных небезопасен, используется roll-forward; это явно
фиксируется до merge. Автоматический rollback не выполняется при риске потери
данных.

## Стабильный выпуск

Стабильная версия выпускается только отдельной задачей человека. Агент:

1. проверяет зелёный `main` и test environment;
2. определяет semver по накопленным изменениям;
3. создаёт annotated tag `vX.Y.Z`;
4. публикует release notes и поставляемые digest;
5. выполняет production-действия только в пределах разрешённой автономности.

`vX.Y.Z-rc.N` используется только когда действительно нужен формальный кандидат.
Release-ветки не создаются.

## Сбой автоматизации

Агент сверяет task, PR, commit, CI run и deployed digest. Если состояние можно
однозначно восстановить, он продолжает с последней доказанной зелёной стадии.
Повторное выполнение необратимого шага без idempotency запрещено. Если состояние
неоднозначно, задача получает `automation-failed` и передаётся человеку.
