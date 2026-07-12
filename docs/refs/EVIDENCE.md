# Доказательства автономного выполнения — справочник

Каждая задача формирует неизменяемый CI artifact `.evidence/<TASK-ID>/`:

```
task.json
plan.json
test-manifest.json
verification.json
security.json
contract-diff.json
deployment.json
summary.md
```

Файлы содержат methodology version, commit SHA, run ID, роли/модели, rule
results, findings и их опровержение, попытки исправления, тесты, scans, deploy и
решение о merge. Секреты и персональные данные в evidence запрещены. `[x]`
допустим только при полном evidence; для неприменимого файла записывается `N/A`
с причиной.

