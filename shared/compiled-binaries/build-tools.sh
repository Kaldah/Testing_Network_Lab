#!/bin/sh

# POSIX sh compatible universal build script
# Usage: ./build-tools.sh [tool]
# Tools: inviteflood (default), all

set -eu

# Detect platform
detect_platform() {
    if [ -f /etc/openwrt_release ]; then
        printf '%s' "openwrt-x86_64"
    elif [ -d /shared/tools ]; then
        printf '%s' "linux-x86_64"
    else
        printf '%s' "host"
    fi
}

PLATFORM=$(detect_platform)
TOOL=${1:-inviteflood}

# Determine directories
if [ "$PLATFORM" = "host" ]; then
    # Resolve script dir (POSIX compatible)
    SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd 2>/dev/null || printf '%s' ".")
    TOOLS_DIR="$SCRIPT_DIR/../tools"
    COMPILED_DIR="$SCRIPT_DIR"
else
    TOOLS_DIR="/shared/tools"
    COMPILED_DIR="/shared/compiled-binaries"
fi

TARGET_DIR="$COMPILED_DIR/$PLATFORM"

# Simple logging helper
log() {
    TS=$(date '+%H:%M:%S' 2>/dev/null || echo "??:??:??")
    case "$PLATFORM" in
        openwrt-x86_64) prefix="OpenWRT" ;;
        linux-x86_64) prefix="Linux" ;;
        host) prefix="Host" ;;
        *) prefix="$PLATFORM" ;;
    esac
    printf '[%s] [%s] %s\n' "$TS" "$prefix" "$*"
}

build_inviteflood() {
    log "Building inviteflood..."

    if [ ! -d "$TOOLS_DIR/inviteflood/inviteflood" ]; then
        log "ERROR: inviteflood source not found at $TOOLS_DIR/inviteflood"
        return 1
    fi

    cd "$TOOLS_DIR/inviteflood/inviteflood" || return 1

    # Clean then try to build
    make clean >/dev/null 2>&1 || true

    if make >/dev/null 2>&1; then
        mkdir -p "$TARGET_DIR" 2>/dev/null || true
        cp inviteflood "$TARGET_DIR/" 2>/dev/null || true
        chmod +x "$TARGET_DIR/inviteflood" 2>/dev/null || true
        log "Successfully built inviteflood"
        ls -la "$TARGET_DIR/inviteflood" 2>/dev/null || true
        return 0
    else
        log "Failed to build inviteflood"
        log "Common issues:" 
        if [ "$PLATFORM" = "openwrt-x86_64" ]; then
            log " - libnet headers not available in OpenWRT packages"
            log " - Try in container: opkg update && opkg install libnet1 libnet1-dev || opkg install libdnet libdnet-dev"
        elif [ "$PLATFORM" = "linux-x86_64" ]; then
            log " - Try: apt-get install libnet1-dev libpcap-dev"
        else
            log " - Install developer headers for libnet/libpcap for your distro"
        fi
        return 1
    fi
}

log "Detected platform: $PLATFORM ($(uname -m 2>/dev/null || echo unknown))"
log "Tools directory: $TOOLS_DIR"
log "Output directory: $TARGET_DIR"

case "$TOOL" in
    inviteflood)
        build_inviteflood || exit 1
        ;;
    all)
        build_inviteflood || exit 1
        ;;
    "")
        build_inviteflood || exit 1
        ;;
    *)
        log "ERROR: Unknown tool '$TOOL'"
        log "Available tools: inviteflood, all"
        exit 1
        ;;
esac

log "Build finished"

if [ "$PLATFORM" != "host" ]; then
    log "Binary location (on host): $TARGET_DIR/$TOOL"
fi
