# Фаза 70 — Выпустить версию (тег)

**Цель:** зафиксировать версию сервиса тегом на `main`. Версии двух уровней:
**pre-release** (рутинные кандидаты, режутся часто) и **стабильная**
(чистый `vX.Y.Z`, помечается отдельно как latest).

**Когда:**
- **pre-release** — `main` прошёл гейт, образ собирается; режется так часто,
  как хочется держать «свежий кандидат».
- **стабильная** — накопленный pre-release-поток доведён до состояния,
  которое готов назвать релизом.

**Что нужно до:** `main` чистый, всё слито через PR, гейт зелёный
(`docs/guide/40-verify.md`), образ собирается (`docs/guide/50-deploy.md`).

> Версии — **тегами, не ветками**. Release-ветки не заводятся:
> точка релиза — тег на `main`, источник для отката/чекаута — он же.
> Уровень версии задаётся суффиксом semver: `-rc.N` / `-beta.N` (pre-release);
> без суффикса — стабильная.

## Уровни версий

- **pre-release** — `vX.Y.Z-rc.N`, `vX.Y.Z-beta.N`. Режутся часто, как поток
  кандидатов. В GitHub Release — галочка *Set as a pre-release*. По semver
  ниже чистого `vX.Y.Z`, то есть формально «ещё не стабильная».
- **стабильная** — `vX.Y.Z` без суффикса. Появляется, когда pre-release-поток
  доведён до готовности. GitHub Release с галочкой *Set as the latest release*.

## Шаги — pre-release (рутинный кандидат)

1. **Обновить `main` и убедиться, что он чистый:**
   ```bash
   git checkout main && git pull
   git status -sb        # working tree clean
   ```
2. **Прогнать проверку** — `docs/guide/40-verify.md` (lint/test/build)
   + `docker compose build` (`docs/refs/DEPLOYMENT.md`).
3. **Поставить annotated-тег с суффиксом** на `main`:
   ```bash
   git tag -a v0.2.0-rc.1 -m "v0.2.0-rc.1: <краткое описание кандидата>"
   ```
4. **Запушить тег:**
   ```bash
   git push origin v0.2.0-rc.1
   ```
5. **GitHub Release** на теге — поставить *Set as a pre-release*.

## Шаги — стабильная версия

1. **Обновить `main` и убедиться, что он чистый:**
   ```bash
   git checkout main && git pull
   git status -sb        # working tree clean
   ```
2. **Прогнать финальную проверку** — `docs/guide/40-verify.md`
   (lint/test/build) + `docker compose build` (`docs/refs/DEPLOYMENT.md`).
3. **Определить версию** (semver `vX.Y.Z`):
   - `PATCH` (Z) — багфикс, без изменения контрактов.
   - `MINOR` (Y) — новая функциональность, обратно совместимая.
   - `MAJOR` (X) — breaking change (в т.ч. смена `CONVENTIONS`).
4. **Поставить annotated-тег без суффикса** на `main`:
   ```bash
   git tag -a v0.1.0 -m "v0.1.0: <краткое описание релиза>"
   ```
5. **Запушить тег:**
   ```bash
   git push origin v0.1.0
   ```
6. **GitHub Release** на теге — *Set as the latest release*, release notes:
   список слитых PR / пункт BACKLOG с момента прошлого стабильного тега.

## Канон (где правда)

- `AGENTS.md` → *Модель ветвления* — теги вместо release-веток.
- `docs/guide/40-verify.md` — что должно быть зелёным перед тегом.
- `docs/refs/VERIFICATION.md` — модель verification gate.
- `docs/refs/COMMUNICATION.md` — `CONVENTIONS` (MAJOR-бамп при breaking).

## Что после

- Тег — точка релиза; хаб/деплой-репо ссылаются на собранный образ
  стабильного тега (pre-release-теги — для внутренних прогонов).
- Следующая разработка — новые `feat/<задача>` от `main` (фаза 30).
- Hotfix на прошлый стабильный релиз — `feat/<задача>` от тега, PR в `main`,
  новый тег (PATCH/MINOR). Отдельной ветки релиза не нужно.