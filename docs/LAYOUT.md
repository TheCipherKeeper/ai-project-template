# Раскладка каталогов

Один репо = один микросервис. Внутри сервиса — **workspace из модулей**
(«монорепо в рамках сервиса»): Rust `crates/`, Go — несколько пакетов под
`internal/`/`pkg/`, Python — подпакеты под `src/`, TypeScript — модули под
`src/`. Каждый модуль — отдельная спека в `docs/specs/<module>.md`.

```
<service>/
  AGENTS.md                 правила работы
  README.md
  docker-compose.yml        локальная разработка: брокер + этот сервис
  .env.example              переменные окружения (копируется в .env)
  Dockerfile                образ этого сервиса
  .gitignore
  LICENSE  LICENSE-DOCS
  docs/
    INDEX.md                карта документации
    ARCHITECTURE.md         модули, брокер, потоки, граница доверия
    BACKLOG.md              очередь задач
    STACKS.md               toolchain/layout/команды по стекам
    LAYOUT.md               этот файл
    DEPLOYMENT.md           Dockerfile + локальный compose + ссылка на хаб-деплой
    specs/
      <module>.md           контракт модуля (по одному на модуль)
      EXAMPLE.md            # пример — удали
    adr/                    ADR (если нет хаба; иначе — в хабе)
  <workspace>/              модули сервиса — по layout выбранного стека:
                            crates/ (Rust), internal/ + pkg/ (Go),
                            src/<service>/ (Python), src/ (TS)
  <manifest>                pyproject.toml / go.mod / Cargo.toml / package.json
  <lock>                    uv.lock / go.sum / Cargo.lock / pnpm-lock.yaml
  shared/                   (опц.) общее внутри сервиса между модулями
```

## Модули и спеки

Каждый модуль workspace'а = отдельный спек `docs/specs/<module>.md` по
канонической структуре (см. `docs/INDEX.md` → *Как работать со спеками*).
Модуль — это:

- Python: пакет/подпакет под `src/<service>/`.
- Go: пакет под `internal/` или `pkg/`.
- Rust: crate в `crates/` (если workspace) или модуль под `src/`.
- TypeScript: директория/модуль под `src/`.

## Где живут общие вещи

- Контракты модулей — `docs/specs/<module>.md`.
- Состав сервиса, модули, топики, потоки — `docs/ARCHITECTURE.md`.
- Деплой (Dockerfile, локальный compose) — `docs/DEPLOYMENT.md`.
- Общее внутри сервиса между модулями — `shared/` (если нужно).
- Кросс-сервисные контракты (event envelope, состав программы, системный
  compose, ADR) — **в хабе**, не в этом репо.
- ADR — в хабе (cybercity) или в `docs/adr/` (standalone) — см. `AGENTS.md` → *ADR*.

## Новый модуль

Чек-лист добавления модуля в workspace:

1. Каталог модуля по layout выбранного стека (команды — `docs/STACKS.md`).
2. Запись в манифесте/конфиге workspace'а, если требуется (Cargo workspace, tsconfig paths, …).
3. Спека: `docs/specs/<module>.md`.
4. Строка в таблице модулей `docs/ARCHITECTURE.md`.
5. Если модуль публикует/читает топики — отметить в разделе «Брокер» `ARCHITECTURE.md`.