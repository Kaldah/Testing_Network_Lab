#!/usr/bin/env bash
set -euo pipefail

# open-windows.sh - Open terminal windows for all running containers
#
# Usage:
#   ./open-windows.sh    # open terminal windows for each container

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
  
  # Check if container is running first (without jq dependency)
  if ! docker compose ps --quiet "$container_name" 2>/dev/null | grep -q .; then
    echo "[!] Container $container_name is not running. Start the lab first with ./start.sh"
    return 1
  fi
  
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

# Check if lab is running
if ! docker compose ps --quiet 2>/dev/null | grep -q .; then
  echo "[!] Lab is not running. Start it first with:"
  echo "    ./start.sh"
  exit 1
fi

TERMINAL=$(detect_terminal)
if [[ -n "$TERMINAL" ]]; then
  echo "[*] Opening terminal windows for each container using $TERMINAL..."
  
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
