# Build the Nakama Go plugin for the same environment as Nakama 3.25.
# Nakama 3.25 image is Debian/glibc (not Alpine/musl). The .so must link against
# glibc and use the same Go version as Nakama (go1.23.3) to avoid load errors.
FROM golang:1.23.3-bookworm AS builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN mkdir -p ./modules && CGO_ENABLED=1 go build -buildmode=plugin -trimpath -o ./modules/game.so .

FROM debian:bookworm-slim
COPY --from=builder /build/modules/game.so /game.so
CMD ["cp", "/game.so", "/out/game.so"]
