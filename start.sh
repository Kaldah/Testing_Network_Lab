#!/usr/bin/env bash
set -euo pipefail

# start.sh - Build and start the SIP test lab
#
# Usage:
#   ./start.sh                    # build and up (detached)
#   ./start.sh --expose-sip       # also publish 5060/tcp,udp to host
#   ./start.sh --attach           # attach shell to attacker after start
#   ./start.sh --open-windows     # open terminal windows for each container
#   ./start.sh --expose-sip --open-windows --attach  # combine options

EXPOSE_SIP=0
ATTACH=0
OPEN_WINDOWS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --expose-sip|-e)
      EXPOSE_SIP=1
      shift
      ;;
    --attach|-a)
      ATTACH=1
      shift
      ;;
    --open-windows|-w)
      OPEN_WINDOWS=1
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --expose-sip, -e      Expose SIP 5060/tcp,udp ports to host"
      echo "  --attach, -a          Attach to attacker shell after start"
      echo "  --open-windows, -w    Open terminal windows for each container"
      echo "  --help, -h            Show this help"
      echo ""
      echo "Examples:"
      echo "  $0                           # Basic start"
      echo "  $0 --expose-sip --open-windows"
      echo "  $0 -e -w -a                  # Short form"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

compose_file="docker-compose.yaml"

# Optionally enable ports by generating an override on the fly
override_file="docker-compose.override.ports.yaml"
if [[ "$EXPOSE_SIP" == "1" ]]; then
  cat > "$override_file" <<'YAML'
services:
  sip_server:
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
YAML
  export COMPOSE_FILE="$compose_file:$override_file"
else
  export COMPOSE_FILE="$compose_file"
fi

echo "[*] Building images..."
docker compose build

echo "[*] Starting lab..."
docker compose up -d

echo "[*] Lab is up. Network: sip_lab_net (10.10.0.0/24)"
echo "    - Attacker: 10.10.0.2 (container: sip-attacker)"
echo "    - SIP server: 10.10.0.3 (container: asterisk-sip)"
echo "    - OpenWRT router: 10.10.0.4 (container: openwrt-router)"
if [[ "$EXPOSE_SIP" == "1" ]]; then
  echo "    - SIP 5060 published to host (udp/tcp)"
else
  echo "    - SIP ports NOT exposed to host (internal only)"
fi

if [[ "$ATTACH" == "1" ]]; then
  echo "[*] Attaching to attacker shell... (exit to detach)"
  docker compose exec attacker bash || docker compose exec attacker sh || true
fi

# Function to detect available terminal emulator
detect_terminal() {
  for term in gnome-terminal konsole xfce4-terminal alacritty kitty terminator xterm; do
    if command -v "$term" >/dev/null 2>&1; then
      echo "$term"
      return 0
    fi
  done
  echo ""
  return 1
}

# Function to open terminal window for a container
open_container_terminal() {
  local container_name="$1"
  local container_title="$2"
  local terminal_cmd="$3"
  
  case "$TERMINAL" in
    gnome-terminal)
      gnome-terminal --title="$container_title" -- bash -c "docker compose exec $container_name $terminal_cmd" &
      ;;
    konsole)
      konsole --title "$container_title" -e bash -c "docker compose exec $container_name $terminal_cmd" &
      ;;
    xfce4-terminal)
      xfce4-terminal --title="$container_title" -x bash -c "docker compose exec $container_name $terminal_cmd" &
      ;;
    alacritty)
      alacritty --title "$container_title" -e bash -c "docker compose exec $container_name $terminal_cmd" &
      ;;
    kitty)
      kitty --title "$container_title" bash -c "docker compose exec $container_name $terminal_cmd" &
      ;;
    terminator)
      terminator --title="$container_title" -x bash -c "docker compose exec $container_name $terminal_cmd" &
      ;;
    xterm)
      xterm -title "$container_title" -e bash -c "docker compose exec $container_name $terminal_cmd" &
      ;;
    *)
      echo "[!] Unknown terminal: $TERMINAL"
      return 1
      ;;
  esac
}

if [[ "$OPEN_WINDOWS" == "1" ]]; then
  TERMINAL=$(detect_terminal)
  if [[ -n "$TERMINAL" ]]; then
    echo "[*] Opening terminal windows for each container using $TERMINAL..."
    
    # Wait a moment for containers to be fully ready
    sleep 2
    
    # Open terminals for each container
    open_container_terminal "attacker" "SIP Lab - Attacker (10.10.0.2)" "bash"
    open_container_terminal "sip_server" "SIP Lab - Asterisk Server (10.10.0.3)" "sh"
    open_container_terminal "openwrt" "SIP Lab - OpenWRT Router (10.10.0.4)" "sh"
    
    echo "[*] Terminal windows opened. Close them when done testing."
  else
    echo "[!] No supported terminal emulator found. Available terminals:"
    echo "    gnome-terminal, konsole, xfce4-terminal, alacritty, kitty, terminator, xterm"
    echo "[*] You can manually connect using:"
    echo "    docker compose exec attacker bash"
    echo "    docker compose exec sip_server sh"
    echo "    docker compose exec openwrt sh"
  fi
fi

echo "[*] Done. Use 'docker compose logs -f' to follow logs or 'docker compose exec <container> <shell>' to get a shell."
