# AGENTS.md — правила работы в репозитории

Точка входа для людей и AI-агентов. Здесь только **правила** (что можно/нельзя,
ветвление, коммиты, язык) и указатели. Процедуры — в `docs/guide/` (по фазам),
факты — в `docs/refs/`. **Начни с `docs/INDEX.md`** — роутер «ситуация → читай».

> Это шаблон **одного микросервиса**. Один репо = один сервис. Внутри сервис
> может быть workspace'ом из нескольких модулей («монорепо в рамках сервиса»),
> у каждого модуля своя спека. Сервис реализуется **на одном из стеков**:
> Python, Go, Rust, TypeScript (бэкенд). Правило: один сервис — один язык.
> Сервис — клиент **брокера** (одного на систему; Kafka/Redpanda/NATS) и
> деплоится **контейнером** со своим `Dockerfile`.
>
> **Программа целиком** — несколько сервисов + хаб + системный compose +
> COMPOSITION/CONVENTIONS/ADR — живёт в хабе и в отдельных репо сервисов.
> Этот репо описывает один сервис. Кросс-сервисные контракты, системная
> топология и ADR — в хабе.

## Документация (приоритет)

В порядке убывания: хаб (если есть) → `AGENTS.md` (этот файл) →
`docs/guide/` (процедуры) → `docs/refs/` (факты) → `docs/ARCHITECTURE.md`
/`docs/BACKLOG.md`/`docs/specs/` (рабочие артефакты) → код.

`docs/INDEX.md` — роутер. Если документы противоречат друг другу — побеждает
старший. Расхождение — повод для ADR (`docs/guide/60-adr.md`).

## Модель ветвления

```
main            ← PR из feature-веток
feat/<задача>   ← от main, удаляется после merge
vX.Y.Z          ← тег на main (стабильная версия)
```

- `main` — стабильная, единственная интеграция. Вливается из feature-веток
  через PR.
- `feat/<задача>` — от `main`, удаляется после merge.
- Прямой коммит в `main` — **запрещён**. Только feature-ветка + PR.
- **Релизы — тегами**, не ветками: стабильная версия = тег `vX.Y.Z` (semver) на
  `main`. Release-ветки не заводятся. Процедура — `docs/guide/70-release.md`.

Процедура работы в ветке — `docs/guide/30-implement-task.md`.

## Команды проверки (выбранный стек)

Стек выбирается один раз для всего репо. **Заполни одну строку** под выбранный
стек, удали остальные. Полная конфигурация toolchain'а — `docs/refs/STACKS.md`.
Прогон перед коммитом — `docs/guide/40-verify.md`.

| Стек | lint | test | build |
|---|---|---|---|
| **Python** | `ruff format --check . && ruff check .` | `pytest` | `uv build` |
| **Go** | `gofmt -l . && go vet ./...` | `go test ./...` | `go build -o bin/<service> ./cmd/<service>` |
| **Rust** | `cargo fmt --check && cargo clippy -- -D warnings` | `cargo test` | `cargo build --release` |
| **TypeScript** | `pnpm lint && tsc --noEmit` | `pnpm test` | `pnpm build` |

> Go: `gofmt -l .` должен вывести пустоту — это и есть «fmt --check».
> Python: опционально `mypy`/`pyright` для типизации.
> TypeScript: runtime — Node (по умолчанию); Deno/Bun допустимы, но зафиксируй в `docs/refs/STACKS.md`.

## Краткие указатели на процедуры

- **Войти в проект** — `docs/guide/00-bootstrap.md`.
- **Описать архитектуру** (модули, брокер, топики, граница) — `docs/guide/10-architecture.md`.
- **Добавить модуль / написать спеку** — `docs/guide/20-define-module.md`.
- **Взять задачу из бэклога, реализовать** (рабочий цикл) — `docs/guide/30-implement-task.md`.
- **Проверить перед коммитом** (verification gate) — `docs/guide/40-verify.md`;
  полная теория — `docs/refs/VERIFICATION.md`.
- **Запустить локально** (брокер + сервис) — `docs/guide/50-deploy.md`;
  структура compose/Dockerfile — `docs/refs/DEPLOYMENT.md`.
- **Записать архитектурное решение (ADR)** — `docs/guide/60-adr.md`.
- **Выпустить стабильную версию (тег)** — `docs/guide/70-release.md`.

## Что можно

- Писать код в модулях сервиса (workspace) и (опц.) `shared/`.
- Менять конфигурацию сборки/манифесты с обоснованием.
- Менять `Dockerfile`, корневой `docker-compose.yml` (локальная разработка:
  брокер + сервис), `.env.example` с обоснованием.
- Обновлять `docs/` (включая `guide/`, `refs/`) и спеки.
- Создавать feature-ветки, коммитить, пушить, открывать PR в `main`.
- Заводить новые модули в workspace'е (с соответствующей спекой — фаза 20).

## Что нельзя

- Коммитить напрямую в `main`.
- Заводить `dev`/release-ветки — интеграция через PR в `main`, версии — тегами.
- Смешивать стеки (один сервис — один язык).
- Вводить системный multi-service compose или кросс-сервисные контракты в этом
  репо — это зона хаба.
- Создавать ADR вне отведённого места (`docs/guide/60-adr.md`).
- Добавлять зависимости (включая образы в compose) без обоснования.
- Выдавать stub за реальную реализацию. Честно помечать: что placeholder, что TODO.
- Трогать lock-файлы (`Cargo.lock`, `go.sum`, `pnpm-lock.yaml`, `uv.lock`),
  конфиги окружения (`.env`), артефакты сборки без одобрения.

## Коммиты

Conventional Commits. Полностью на английском (или на языке проекта — задай в *Язык*).

```
feat(<module>): add zfs-snapshot fs probe
fix(<module>): reject path traversal in HostBridge
docs: update ARCHITECTURE.md with module matrix
refactor(<module>): extract envelope signing
chore(deploy): pin redpanda image in compose
```

Scope — имя модуля или `deploy`/`docs`. Breaking changes —
`BREAKING CHANGE:` в теле.

## Язык

Документация — русский (или поменяй под свой проект). Английский допустим
только для: идентификаторов кода, имён модулей, значений `Status:` в ADR,
summary-строки коммита.