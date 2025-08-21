#!/usr/bin/env bash
set -euo pipefail

IMAGE=${IMAGE:-stormshadow-test-env}
WITH_X=${WITH_X:-0}   # set to 1 to try X11
NAME=${NAME:-stormshadow-test}

docker build -t "$IMAGE" .

# Base args (NFQUEUE/iptables need these caps; host net keeps iface names)
RUN_ARGS=(
  --rm -it
  --name "$NAME"
  --network host
  --cap-add=NET_ADMIN --cap-add=NET_RAW
  -v "$PWD":/app
)

if [[ "$WITH_X" == "1" ]]; then
  # Only attempt X if DISPLAY is set and the X socket exists
  if [[ -n "${DISPLAY:-}" && -S /tmp/.X11-unix/X0 ]]; then
    # Check if Docker can mount the X socket (Docker Desktop may block it)
    if docker info 2>/dev/null | grep -qi 'Docker Desktop'; then
      # On Docker Desktop you must share /tmp (or /tmp/.X11-unix) in Settings → Resources → File Sharing
      echo "[!] Docker Desktop detected. Share /tmp (or /tmp/.X11-unix) in Docker Desktop → Settings → Resources → File Sharing."
      echo "[!] Falling back to headless run for now."
    else
      echo "[*] Enabling X11 forwarding into container"
      xhost +local:root || true
      RUN_ARGS+=(-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix)
    fi
  else
    echo "[!] DISPLAY not set or /tmp/.X11-unix missing; running headless."
  fi
fi

exec docker run "${RUN_ARGS[@]}" "$IMAGE"
