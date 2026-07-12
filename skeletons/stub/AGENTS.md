# AGENTS.md — правила работы в репозитории автономного компонента

Основной документ для людей и программных агентов в **репозитории одного
автономного компонента**. Компонент выполняется как отдельная программа и не
подключается к брокеру.
Здесь только **правила** (ветвление, что можно/нельзя, коммиты, язык, стек-команды)
и указатели. Процедуры — в методологии (`<methodology-repo>/docs/guide/`), факты —
в `<methodology-repo>/docs/refs/`. Начни с `<methodology-repo>/docs/INDEX.md`.

> Репозиторий создаётся из `skeletons/stub/`. Автономный компонент не публикует
> и не читает темы брокера и не является микросервисом. Остальные способы
> взаимодействия определяются назначением компонента и фиксируются в
> `COMPOSITION` хаба и `docs/ARCHITECTURE.md`.
> Форма — параметр из control-plane: контейнер / CLI / … (`form`); деплой — по форме
> (контейнер — `Dockerfile`; CLI — артефакт/сборка). При наличии наблюдаемой
> поверхности collector наблюдает её out-of-band. `MODULE.md`/`SPEC.md` к stub **не
> применяются** (бэкенд-канон usecase-швов для сервиса); stub параметризуется, а не
> вариантами использования. Модель — `<methodology-repo>/docs/refs/COMMUNICATION.md` → *Автономный компонент*.
>
> Системный контекст (состав системы, список сервисов, интерфейсов и автономных компонентов,
> event envelope) — в **хабе** `COMPOSITION.md`; топология —
> `<methodology-repo>/docs/refs/TOPOLOGY.md`.

## Документация (приоритет)

Версия внешнего канона закреплена в `.methodology.yml`; CI читает этот tag, а
не плавающий `main`. Обязательные проверки работают fail closed; риск, evidence
и recovery определены центральными `RISK.md`, `EVIDENCE.md`, `RECOVERY.md`.

В порядке убывания **по ярусам**: хаб → этот `AGENTS.md` →
методология (`<methodology-repo>/docs/guide/` и `/docs/refs/` — **равные**,
разные виды) → `docs/ARCHITECTURE.md` → код.

`<methodology-repo>/docs/INDEX.md` — роутер. Приоритет арбитражирует
**только между ярусами**. Противоречие **внутри яруса** (в т.ч. `guide/` против
`refs/`) — **дефект**, а не «старший побеждает»: чинят к одной правде **до
коммита**; сырой agent-вердикт не блокирует, подтверждённая находка требует
разрешения (см. `<methodology-repo>/docs/refs/VERIFICATION.md`) либо ADR
(`<methodology-repo>/docs/guide/60-adr.md`).

## Модель ветвления

```mermaid
gitGraph
  commit id: "init"
  commit
  branch feat
  commit
  checkout main
  merge feat
  commit tag: "vX.Y.Z"
```

- `main` — стабильная, единственная интеграция. Вливается из feature-веток через PR.
- `feat/<задача>` — от `main`, удаляется после merge.
- Прямой коммит в `main` — **запрещён**. Только feature-ветка + PR.
- Релизы — тегами `vX.Y.Z` (semver) на `main`; release-ветки не заводятся
  (`<methodology-repo>/docs/guide/70-release.md`).

## Стек

Stub реализуется на одном из бэкенд-стеков (Python/Go/Rust/TypeScript) — выбор
один раз для всего репо. Полная конфигурация toolchain'а —
`<methodology-repo>/docs/refs/STACKS.md`. Прогон перед коммитом —
`<methodology-repo>/docs/guide/40-verify.md`. **Заполни одну строку** стека, удали
остальные (как в сервисе).

| Стек | lint | test | build |
|---|---|---|---|
| **Python** | `ruff format --check . && ruff check . && pyright` | `pytest` | `uv build` |
| **Go** | `gofmt -l . && go vet ./...` | `go test ./...` | `go build -o bin/<stub> ./cmd/<stub>` |
| **Rust** | `cargo fmt --check && cargo clippy -- -D warnings` | `cargo test` | `cargo build --release` |
| **TypeScript** | `pnpm lint && tsc --noEmit` | `pnpm test` | `pnpm build` |

> Stub может не иметь классических юзкейсов/тестов (параметризуется дескриптором);
> тогда `test` честно помечается отсутствующим (placeholder/TODO — инвариант #9),
> а `lint`/`build` обязаны идти (программа должна собираться — для `form=container`
> это образ, для CLI — артефакт).

## Указатели на процедуры/факты (в методологии)

- Войти в проект (stub) — выбери форму (`form`: контейнер / CLI / …), заполни
  `README` и `docs/ARCHITECTURE.md` (форма, поверхности если наблюдаются,
  доверительная граница, деплой); стек-команды — выше.
- Проверить перед коммитом — `<methodology-repo>/docs/guide/40-verify.md`;
  теория и применимость инвариантов для stub —
  `<methodology-repo>/docs/refs/VERIFICATION.md`.
- Деплой — `<methodology-repo>/docs/refs/DEPLOYMENT.md` (для `form=container` —
  структура compose/Dockerfile/env как у сервиса, но без брокера; для CLI —
  артефакт/сборка).
- Записать ADR — `<methodology-repo>/docs/guide/60-adr.md` (ADR — в хабе).
- Выпустить версию (тег) — `<methodology-repo>/docs/guide/70-release.md`.

## Что можно

- Писать код автономного компонента, его параметризуемые дескрипторы и
  конфигурацию.
- Менять `Dockerfile`/`docker-compose.yml` (при `form=container`: локальная
  разработка — этот stub, **без брокера**), `.env.example`/конфиг-дескриптор с
  обоснованием.
- Обновлять `docs/ARCHITECTURE.md` (форма, поверхности если наблюдаются,
  доверительная граница, деплой).
- Создавать feature-ветки, PR в `main`, теги `vX.Y.Z`.

## Что нельзя

- Коммитить напрямую в `main`; заводить `dev`/release-ветки.
- Быть **брокер-клиентом** или **peer-сервисом** — stub не publish/consume топики,
  не имеет presentation-эндпоинтов; не лезёт в чужую БД/брокер. При наличии
  поверхности — наблюдается collector'ом out-of-band, сам ничего не зовёт.
- Применять к stub `MODULE.md`/`SPEC.md`/`docs/specs/` — это бэкенд-канон
  сервиса; stub параметризуется дескриптором, а не юзкейсами. (Если у stub есть
  осмысленные модули — описывают в `docs/ARCHITECTURE.md`, не в спеках.)
- Заводить свой `BACKLOG.md` — программный бэклог живёт в хабе
  (`<hub>/BACKLOG.md`), не в этом репо.
- Смешивать стеки (один stub — один язык).
- Создавать ADR вне хаба (`<hub>/adr/`; процедура — `guide/60`).
- Добавлять зависимости (включая образы в compose) без обоснования.
- Выдавать stub/заглушку за реализацию — честно помечать placeholder/TODO (#9).
- Трогать lock-файлы, `.env`, артефакты сборки без одобрения.

## Коммиты

Conventional Commits. Scope — `surface`/`banner`/`deploy`/`docs`/имя модуля.

```
feat(banner): add SSH banner emulation for lite-target
fix(surface): reject malformed handshake
chore(deploy): pin stub base image in Dockerfile
```

Breaking changes — `BREAKING CHANGE:` в теле. Язык — `AGENTS.md` → *Язык* ниже.

## Язык

Документация — русский (или поменяй под проект). Английский допустим только для
идентификаторов кода, имён модулей/поверхностей, `Status:` в ADR, summary-строки
коммита.
