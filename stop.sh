#!/usr/bin/env bash
set -euo pipefail

# stop.sh - Stop and clean up the SIP test lab
#
# Usage:
#   ./stop.sh           # stop containers (keeps images and networks)
#   ./stop.sh --clean   # stop and remove containers, networks, and images
#   ./stop.sh --full    # stop and remove everything including volumes

CLEAN_MODE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --clean|-c)
      CLEAN_MODE="clean"
      shift
      ;;
    --full|-f)
      CLEAN_MODE="full"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  (no args)     Stop containers only"
      echo "  --clean, -c   Stop and remove containers, networks, and images"
      echo "  --full, -f    Stop and remove everything including volumes"
      echo "  --help, -h    Show this help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo "[*] Stopping SIP lab..."

# Stop containers
docker compose down

case "$CLEAN_MODE" in
  "clean")
    echo "[*] Cleaning up containers, networks, and images..."
    # Remove containers, networks, and images
    docker compose down --rmi all --remove-orphans
    ;;
  "full")
    echo "[*] Full cleanup: removing containers, networks, images, and volumes..."
    # Remove everything including volumes
    docker compose down --rmi all --volumes --remove-orphans
    ;;
  *)
    echo "[*] Containers stopped. Use --clean to remove images or --full for complete cleanup."
    ;;
esac

# Clean up any temporary override files
if [[ -f "docker-compose.override.ports.yaml" ]]; then
  echo "[*] Cleaning up temporary override files..."
  rm -f docker-compose.override.ports.yaml
fi

echo "[*] Lab stopped."
echo ""
echo "To restart: ./start.sh"
echo "To check status: docker compose ps"
