# Evidence

CI публикует неизменяемый `.evidence/TASK-NNNN.json` по схеме
`<methodology-repo>/schemas/evidence.schema.json`. Verifier связывает его с
машинной задачей, pinned-версией методологии и переданным CI commit.

Поле `source` указывает на лог проверки или review, `reviewer` — на независимый
вызов reviewer, `artifact` содержит digest, а `retained_until` задаёт срок, до
которого CI обязан сохранять evidence и связанные логи. Секреты и персональные
данные сюда не записываются; runtime-артефакты хранятся в CI, а не в Git.
