# Эксплуатационная надёжность — справочник

Каждый развёртываемый компонент определяет liveness/readiness, structured logs,
correlation/trace ID, метрики, SLO, graceful shutdown, health зависимостей и
режим деградации. Consumer дополнительно определяет idempotency, retry/backoff,
poison-message и DLQ.

## Завершение после deploy

Merge и RC не завершают задачу. Последовательность:

```
RC → test-deploy → readiness → smoke → contract/security probes
   → окно наблюдения → evidence → [~]→[x]
```

Провал останавливает очередь. Если заранее проверенный rollback безопасен — он
выполняется автоматически; иначе среда удерживается, задача получает hold и
диагностику. Телеметрия, commit, версия схем и deployment ID входят в evidence.

