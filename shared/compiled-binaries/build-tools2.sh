#!/bin/sh

# Universal build script for compiling tools
# Auto-detects the current environment and compiles tools accordingly
# Usage: ./build-tools.sh [tool]
# Tools: inviteflood, all

set -e

# Detect where we're running
detect_platform() {
    if [ -f /etc/openwrt_release ]; then
        echo "openwrt-x86_64"
    elif [ -d /shared/tools ]; then
        # Running inside container with shared mount
        echo "linux-x86_64" 
    else
        # Running on host system
        echo "host"
    fi
}

PLATFORM=$(detect_platform)
TOOL="${1:-inviteflood}"

# Set paths based on environment
if [ "$PLATFORM" = "host" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    TOOLS_DIR="$SCRIPT_DIR/../tools"
    COMPILED_DIR="$SCRIPT_DIR"
else
    # Running inside container
    TOOLS_DIR="/shared/tools"
    COMPILED_DIR="/shared/compiled-binaries"
fi

TARGET_DIR="$COMPILED_DIR/$PLATFORM"

log() {
    local platform_name
    case "$PLATFORM" in
        "openwrt-x86_64") platform_name="OpenWRT" ;;
        "linux-x86_64") platform_name="Linux" ;;
        "host") platform_name="Host" ;;
    esac
    echo "[$(date '+