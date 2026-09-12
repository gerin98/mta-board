#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALL_DIR="/opt/mta-board"
readonly SERVICE_FILE="/etc/systemd/system/mta-board.service"
readonly RGB_MATRIX_REVISION="51d3231e370593b60952b2c3b18d2e3802329f18"
readonly RGB_MATRIX_URL="git+https://github.com/hzeller/rpi-rgb-led-matrix.git@${RGB_MATRIX_REVISION}"
readonly RGB_MATRIX_MARKER="${INSTALL_DIR}/.rgbmatrix-revision"

DRY_RUN=false
FORCE=false
START_SERVICE=true

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/install_pi.sh [OPTIONS]

Install MTA Board and the HUB75 matrix driver on Raspberry Pi OS.

Options:
  --dry-run   Print the installation commands without changing the system
  --force     Continue when Raspberry Pi hardware cannot be detected
  --no-start  Enable the service at boot, but do not start it now
  -h, --help  Show this help
EOF
}

log() {
  printf '\n==> %s\n' "$*"
}

warn() {
  printf 'WARNING: %s\n' "$*" >&2
}

run() {
  if [[ "$DRY_RUN" == true ]]; then
    printf '+ '
    printf '%q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

for argument in "$@"; do
  case "$argument" in
    --dry-run) DRY_RUN=true ;;
    --force) FORCE=true ;;
    --no-start) START_SERVICE=false ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$argument" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -f "${SOURCE_DIR}/pyproject.toml" || ! -f "${SOURCE_DIR}/deploy/mta-board.service" ]]; then
  printf 'Run this script from a complete mta-board checkout.\n' >&2
  exit 1
fi

if [[ "$DRY_RUN" != true ]]; then
  if [[ "$EUID" -ne 0 ]]; then
    printf 'This installer needs root access. Run: sudo %s\n' "$0" >&2
    exit 1
  fi

  if [[ "$(uname -s)" != "Linux" || ! -x "$(command -v apt-get 2>/dev/null || true)" ]]; then
    printf 'This installer supports Raspberry Pi OS and other apt-based Linux systems.\n' >&2
    exit 1
  fi

  PI_MODEL_FILE="/proc/device-tree/model"
  if [[ ! -r "$PI_MODEL_FILE" ]] || ! tr -d '\0' < "$PI_MODEL_FILE" | grep -qi 'raspberry pi'; then
    if [[ "$FORCE" != true ]]; then
      printf 'Raspberry Pi hardware was not detected. Pass --force to continue anyway.\n' >&2
      exit 1
    fi
    warn "Raspberry Pi hardware was not detected; continuing because --force was supplied."
  fi
fi

log "Installing operating-system packages"
run apt-get update
run apt-get install -y \
  build-essential \
  ca-certificates \
  cmake \
  cython3 \
  git \
  ninja-build \
  pkg-config \
  python3-dev \
  python3-pil \
  python3-venv \
  rsync

log "Deploying MTA Board to ${INSTALL_DIR}"
run mkdir -p "$INSTALL_DIR"
if [[ "$SOURCE_DIR" != "$INSTALL_DIR" ]]; then
  run rsync -a --no-owner --no-group \
    --exclude .git/ \
    --exclude .venv/ \
    --exclude config.toml \
    --exclude __pycache__/ \
    --exclude .pytest_cache/ \
    "${SOURCE_DIR}/" "${INSTALL_DIR}/"
fi

if [[ "$DRY_RUN" == true || ! -f "${INSTALL_DIR}/config.toml" ]]; then
  run install -m 0644 "${SOURCE_DIR}/config.example.toml" "${INSTALL_DIR}/config.toml"
else
  log "Keeping the existing ${INSTALL_DIR}/config.toml"
fi

log "Creating the Python environment"
if [[ "$DRY_RUN" == true || ! -x "${INSTALL_DIR}/.venv/bin/python" ]]; then
  run python3 -m venv --system-site-packages "${INSTALL_DIR}/.venv"
fi
run "${INSTALL_DIR}/.venv/bin/python" -m pip install --upgrade pip

log "Installing the pinned RGB matrix driver"
if [[ "$DRY_RUN" != true ]] \
  && [[ -f "$RGB_MATRIX_MARKER" ]] \
  && [[ "$(<"$RGB_MATRIX_MARKER")" == "$RGB_MATRIX_REVISION" ]] \
  && "${INSTALL_DIR}/.venv/bin/python" -c 'import rgbmatrix' 2>/dev/null; then
  log "The pinned RGB matrix driver is already installed"
elif [[ "$DRY_RUN" == true ]]; then
  printf '+ CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 PIP_NO_CACHE_DIR=1 '
  printf '%q ' "${INSTALL_DIR}/.venv/bin/python" -m pip install "$RGB_MATRIX_URL"
  printf '\n'
else
  CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 PIP_NO_CACHE_DIR=1 \
    "${INSTALL_DIR}/.venv/bin/python" -m pip install "$RGB_MATRIX_URL"
  printf '%s\n' "$RGB_MATRIX_REVISION" > "$RGB_MATRIX_MARKER"
fi

log "Installing MTA Board"
run "${INSTALL_DIR}/.venv/bin/python" -m pip install --editable "$INSTALL_DIR"

log "Installing the system service"
run install -m 0644 "${SOURCE_DIR}/deploy/mta-board.service" "$SERVICE_FILE"
run systemctl daemon-reload
run systemctl enable mta-board.service
if [[ "$START_SERVICE" == true ]]; then
  run systemctl restart mta-board.service
fi

if [[ "$DRY_RUN" != true ]]; then
  BOOT_CONFIG="/boot/firmware/config.txt"
  if [[ -r "$BOOT_CONFIG" ]]; then
    if grep -Eq '^[[:space:]]*dtoverlay=w1-gpio' "$BOOT_CONFIG"; then
      warn "1-Wire GPIO is enabled in ${BOOT_CONFIG}; it conflicts with the matrix driver."
    fi
    if ! grep -Eq '^[[:space:]]*dtparam=audio=off([[:space:]]*(#.*)?)?$' "$BOOT_CONFIG"; then
      warn "Add 'dtparam=audio=off' to ${BOOT_CONFIG} and reboot if the display flickers."
    fi
  fi
fi

log "Installation complete"
if [[ "$START_SERVICE" == true ]]; then
  printf 'Follow the board logs with: sudo journalctl -u mta-board -f\n'
else
  printf 'Start the board when it is connected: sudo systemctl start mta-board\n'
fi
