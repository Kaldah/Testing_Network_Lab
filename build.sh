#!/usr/bin/env bash
set -euo pipefail

# build.sh - Build all Docker images for the SIP lab
#
# Usage:
#   ./build.sh                # build all images
#   ./build.sh --clean        # clean build (no cache)
#   ./build.sh --attacker     # build only attacker image
#   ./build.sh --sip-server   # build only sip server image
#   ./build.sh --openwrt      # build only openwrt image

BUILD_ARGS=""
SERVICES=""
INCLUDE_LINUX=false
EXPORT_IMAGES=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --clean|-c)
      BUILD_ARGS="--no-cache"
      shift
      ;;
    --attacker|-a)
      SERVICES="attacker"
      shift
      ;;
    --with-linux|-l)
      # When building all services, include the attacker (linux) image
      INCLUDE_LINUX=true
      shift
      ;;
    --sip-server|-s)
      SERVICES="sip_server"
      shift
      ;;
    --openwrt|-o)
      SERVICES="openwrt"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --clean, -c       Clean build (no cache)"
      echo "  --attacker, -a    Build only attacker image"
      echo "  --with-linux, -l  Include attacker (linux) image when building default set"
      echo "  --sip-server, -s  Build only sip server image"
      echo "  --openwrt, -o     Build only openwrt image"
      echo "  --help, -h        Show this help"
      echo ""
      echo "Examples:"
      echo "  $0                # Build all images"
      echo "  $0 --clean        # Clean build all"
      echo "  $0 --attacker     # Build only attacker"
      exit 0
      ;;
    --export-images)
      EXPORT_IMAGES=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo "[*] Building SIP lab Docker images..."

if [[ -n "$BUILD_ARGS" ]]; then
  echo "[*] Using build args: $BUILD_ARGS"
fi

if [[ -n "$SERVICES" ]]; then
  echo "[*] Building specific service: $SERVICES"
  docker compose build $BUILD_ARGS $SERVICES
else
  # Default: build the lab services but skip the attacker (linux) image unless requested
  DEFAULT_SERVICES="sip_server openwrt"
  if [[ "$INCLUDE_LINUX" == true ]]; then
    echo "[*] Including attacker (linux) in the build"
    SERVICES="$DEFAULT_SERVICES attacker"
  else
    SERVICES="$DEFAULT_SERVICES"
    echo "[*] Building default services (attacker/linux is skipped). Use --with-linux to include it."
  fi

  docker compose build $BUILD_ARGS $SERVICES
fi

echo ""
echo "[*] Build complete! Verifying critical dependencies..."

# Test critical dependencies in attacker container only if attacker was built
if [[ "$SERVICES" == *attacker* ]]; then
  echo "[*] Testing attacker container dependencies..."

  # Start a temporary container to test dependencies
  if docker compose ps attacker --quiet 2>/dev/null | grep -q .; then
    # Container is running, use it
    TEST_CMD="docker compose exec attacker"
  else
    # Container not running, start temporary one
    TEST_CMD="docker compose run --rm attacker"
  fi

  $TEST_CMD python3 -c "
import sys
print(f'Python version: {sys.version.split()[0]}')

critical_packages = ['netfilterqueue', 'netifaces', 'scapy', 'fastapi']
all_good = True

for pkg in critical_packages:
    try:
        __import__(pkg)
        print(f'✓ {pkg}')
    except ImportError as e:
        print(f'✗ {pkg} - FAILED: {e}')
        all_good = False

if all_good:
    print('\\n✅ All critical dependencies are working!')
else:
    print('\\n❌ Some dependencies failed - check the build')
    sys.exit(1)
" 2>/dev/null || echo "[!] Could not test dependencies (container may not be running)"
else
  echo "[*] Attacker (linux) image was not built; skipping attacker dependency tests."
fi

echo ""
echo "[*] Build verification complete."
echo "    Start the lab with: ./start.sh"
echo "    Or with windows:    ./start.sh --open-windows"

if [[ "$EXPORT_IMAGES" == true ]]; then
  echo "[*] Exporting built images to Docker_Images/"
  mkdir -p Docker_Images

  # Export images that may have been built
  IMAGES_TO_EXPORT=("sip-lab-openwrt:latest" "sip-lab-sip_server:latest" "sip-lab-attacker:latest")
  for img in "${IMAGES_TO_EXPORT[@]}"; do
    if docker image inspect "$img" >/dev/null 2>&1; then
      fname="Docker_Images/$(echo $img | tr ':/' '_').tar"
      echo "  - Exporting $img -> $fname"
      docker save -o "$fname" "$img"
    else
      echo "  - Skipping $img (not present)"
    fi
  done
  echo "[*] Export complete. Files are in ./Docker_Images/"
fi
