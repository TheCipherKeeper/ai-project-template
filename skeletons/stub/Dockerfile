# Dockerfile автономного компонента — только для form=container. Для прочих форм (cli, …)
# этот файл удаляется. Скелет — замени под выбранный стек.
# Stub — standalone-программа (контейнер-цель при form=container). Брокера НЕТ.
# Сборка из команд стека (см. <methodology-repo>/docs/REFERENCE.md).
# Требования: мультистадийная сборка, тонкий runtime-образ, не от root,
# healthcheck если есть. Детали — <methodology-repo>/docs/OPERATIONS.md.

# ---- stage: build ----
# Пример (подставь свой toolchain):
# FROM <sdk-image> AS build
# WORKDIR /src
# COPY . .
# RUN <build-команда стека>          # напр. cargo build --release / go build / pnpm build / uv build
#
# ---- stage: runtime ----
# FROM <runtime-image>
# WORKDIR /app
# COPY --from=build /src/<artifact> /app/<artifact>
# USER 1000:1000
# CMD ["/app/<artifact>"]
