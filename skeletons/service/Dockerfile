# Dockerfile сервиса. Скелет — замени под выбранный стек.
# Сборка из команд `build` стека (см. <methodology-repo>/docs/refs/STACKS.md).
# Требования: мультистадийная сборка, тонкий runtime-образ, не от root,
# healthcheck если есть. Детали — <methodology-repo>/docs/refs/DEPLOYMENT.md.

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