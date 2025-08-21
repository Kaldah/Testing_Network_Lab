#!/usr/bin/env bash
set -euo pipefail

# build_and_start.sh - Load exported images, build missing services, and start the SIP lab
#
# Usage:
#   ./build_and_start.sh                # Load images if present, build missing, start lab
#   ./build_and_start.sh --clean        # Clean build (no cache), then start
#   ./build_and_start.sh --rebuild      # Force rebuild all services, then start
#   ./build_and_start.sh --help         # Show this help

BUILD_ARGS=""
FORCE_REBUILD=false
SERVICES="attacker sip_server openwrt"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --clean|-c)
      BUILD_ARGS="--no-cache"
      shift
      ;;
    --rebuild|-r)
      FORCE_REBUILD=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  (no args)         Load images if present, build missing, start lab"
      echo "  --clean, -c       Clean build (no cache), then start"
      echo "  --rebuild, -r     Force rebuild all services, then start"
      echo "  --help, -h        Show this help"
      echo ""
      echo "This script will:"
      echo "  1. Check for exported images in images/ folder"
      echo "  2. Load any found images into Docker"
      echo "  3. Build missing services using docker compose"
      echo "  4. Start the lab with docker compose up -d"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo "[*] SIP Lab Build and Start Script"
echo ""

# Step 1: Load exported images if they exist
IMAGES_DIR="./images"
if [[ -d "$IMAGES_DIR" ]]; then
  echo "[*] Checking for exported images in $IMAGES_DIR..."
  
  # Look for tar files
  TAR_FILES=($(find "$IMAGES_DIR" -name "*.tar" 2>/dev/null || true))
  
  if [[ ${#TAR_FILES[@]} -gt 0 ]]; then
    echo "[*] Found ${#TAR_FILES[@]} exported image(s), loading into Docker..."
    for tar_file in "${TAR_FILES[@]}"; do
      echo "    Loading: $(basename "$tar_file")"
      docker load -i "$tar_file" || {
        echo "[!] Failed to load $tar_file, continuing..."
      }
    done
    echo "[*] Image loading complete."
  else
    echo "[*] No exported images found in $IMAGES_DIR"
  fi
else
  echo "[*] Images directory $IMAGES_DIR not found, will build all services"
fi

echo ""

# Step 2: Check which images are already present
echo "[*] Checking current Docker images..."
EXISTING_IMAGES=()

# Expected image names based on docker-compose.yaml
EXPECTED_IMAGES=(
  "sip-lab-attacker:latest"
  "sip-lab-sip_server:latest" 
  "sip-lab-openwrt:latest"
)

for img in "${EXPECTED_IMAGES[@]}"; do
  if docker image inspect "$img" >/dev/null 2>&1; then
    echo "    ✓ $img (present)"
    EXISTING_IMAGES+=("$img")
  else
    echo "    ✗ $img (missing)"
  fi
done

echo ""

# Step 3: Build missing or all services
if [[ "$FORCE_REBUILD" == true ]]; then
  echo "[*] Force rebuild requested - building all services..."
  docker compose build $BUILD_ARGS $SERVICES
elif [[ ${#EXISTING_IMAGES[@]} -eq 3 ]] && [[ -z "$BUILD_ARGS" ]]; then
  echo "[*] All images present, skipping build"
else
  echo "[*] Building missing services..."
  docker compose build $BUILD_ARGS $SERVICES
fi

echo ""

# Step 4: Start the lab
echo "[*] Starting SIP lab services..."
docker compose up -d

echo ""
echo "[*] Lab startup complete!"
echo ""
echo "Services status:"
docker compose ps

echo ""
echo "Useful commands:"
echo "  ./status.sh          # Check service status"
echo "  ./stop.sh            # Stop the lab"
echo "  docker compose logs  # View logs"
echo ""
echo "To access containers:"
echo "  docker compose exec attacker bash"
echo "  docker compose exec openwrt sh"
echo "  docker compose exec sip_server bash"
