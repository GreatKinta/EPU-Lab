#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
dns_workaround=false
open_browser=false
for arg in "$@"; do
  case "$arg" in
    --dns-workaround) dns_workaround=true ;;
    --open) open_browser=true ;;
    -h|--help)
      printf 'Usage: ./setup-linux.sh [--dns-workaround]\nRequires Docker and Compose. Existing data and passwords are preserved.\n'
      exit 0 ;;
    *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
  esac
done
if ! command -v docker >/dev/null 2>&1; then
  echo 'Chưa cài Docker. Cài Docker Desktop hoặc Docker Engine + Compose trước.' >&2
  exit 1
fi
context_args=()
if ! docker info >/dev/null 2>&1; then
  if docker --context desktop-linux info >/dev/null 2>&1; then
    context_args=(--context desktop-linux)
  else
    echo 'Docker daemon chưa chạy. Mở Docker Desktop hoặc khởi động Docker Engine.' >&2
    exit 1
  fi
fi
LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" \
  docker "${context_args[@]}" compose -f docker-compose.setup.yml run --rm setup
compose_args=(-f docker-compose.yml)
if [[ "$dns_workaround" == true ]]; then
  LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" \
    docker "${context_args[@]}" compose -f docker-compose.setup.yml run --rm setup \
    python scripts/build_dns_override.py
  compose_args+=(-f runtime/compose.build-dns.yml)
fi
docker "${context_args[@]}" compose "${compose_args[@]}" up --build -d --wait --wait-timeout 600
docker "${context_args[@]}" compose "${compose_args[@]}" ps -a
web_binding=$(docker "${context_args[@]}" compose "${compose_args[@]}" port frontend 80)
web_port=${web_binding##*:}
web_url="http://localhost:$web_port"
printf 'LabChain ready: %s\n' "$web_url"
printf 'API: http://localhost:8000/docs\n'
if [[ "$open_browser" == true ]]; then
  if command -v xdg-open >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    xdg-open "$web_url" >/dev/null 2>&1 &
  elif [[ "$(uname -s)" == Darwin ]]; then
    open "$web_url" >/dev/null 2>&1 || true
  fi
fi
