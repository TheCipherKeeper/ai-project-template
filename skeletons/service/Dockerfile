# Dockerfile сервиса. Скелет — замени под выбранный стек.
# Сборка из команд стека (см. <methodology-repo>/docs/REFERENCE.md).
# Требования: многоэтапная сборка, минимальный образ среды выполнения, запуск не
# от пользователя root, проверка работоспособности при наличии. Детали —
# <methodology-repo>/docs/OPERATIONS.md.

# ---- этап: сборка ----
# Пример (подставь свой набор инструментов):
# FROM <sdk-image> AS build
# WORKDIR /src
# COPY . .
# RUN <build-команда стека>          # напр. cargo build --release / go build / pnpm build / uv build
#
# ---- этап: выполнение ----
# FROM <runtime-image>
# WORKDIR /app
# COPY --from=build /src/<artifact> /app/<artifact>
# USER 1000:1000
# CMD ["/app/<artifact>"]
