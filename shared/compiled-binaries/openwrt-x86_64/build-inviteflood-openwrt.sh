#!/bin/sh

# Build inviteflood on OpenWRT (or compatible) targets.
# Intended to be copied into a real OpenWRT router and executed there.
# Output binary will be placed in /shared/compiled-binaries/openwrt-x86_64/

set -eu

TOOLS_DIR=/shared/tools/inviteflood/inviteflood
OUT_DIR=/shared/compiled-binaries/openwrt-x86_64
TMPDIR=/tmp/inviteflood-build

log() {
  TS=$(date '+%H:%M:%S' 2>/dev/null || echo "??:??:??")
  printf "[%s] %s\n" "$TS" "$*"
}

log "Starting OpenWRT inviteflood build"

# Normalize PATH so configure tools are found
export PATH="/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:$PATH"

# Ensure tools exist
if [ ! -d "$TOOLS_DIR" ]; then
  log "ERROR: inviteflood source not found at $TOOLS_DIR"
  exit 1
fi

# Ensure out dir exists
mkdir -p "$OUT_DIR"

# Try install headers via opkg if available
if command -v opkg >/dev/null 2>&1; then
  log "opkg detected: attempting to install libnet and libpcap (if available)"
  opkg update || true
  # Try installing common build utilities and helpers first
  log "Installing build helpers via opkg (gcc, make, grep, gawk, autoconf, automake, libtool, patch, tar)"
  opkg install gcc make grep gawk autoconf automake libtool patch tar wget curl || true
  opkg install libnet1 libnet1-dev || opkg install libdnet libdnet-dev || log "libnet not available from opkg"
  opkg install libpcap-dev || opkg install libpcap1 || log "libpcap not installed"
fi

# Check for libnet.h
if [ -f /usr/include/libnet.h ] || [ -f /usr/include/libdnet.h ]; then
  log "libnet headers found, attempting to build inviteflood"
  cd "$TOOLS_DIR"
  make clean || true
  if make; then
    cp inviteflood "$OUT_DIR/"
    chmod +x "$OUT_DIR/inviteflood"
    log "inviteflood built and copied to $OUT_DIR/inviteflood"
    exit 0
  else
    log "make failed even with available headers"
  fi
fi

# If headers missing, attempt to build libnet from source locally
log "libnet headers missing — attempting to build libnet from source (local)"

rm -rf "$TMPDIR" || true
mkdir -p "$TMPDIR"
cd "$TMPDIR"

# Try known libnet sources (libnet-1.2.x or libdnet)
# Prefer libnet-1.2.3 (historical) but try libdnet if needed
LIBNET_URLS='https://github.com/sam-github/libnet/archive/refs/tags/v1.2.3.tar.gz https://github.com/dugsong/libdnet/archive/refs/heads/master.tar.gz'

fetched=0
for url in $LIBNET_URLS; do
  log "Trying to fetch $url"
  if command -v wget >/dev/null 2>&1; then
    if wget -q -O libnet.tgz "$url"; then fetched=1; break; fi
  elif command -v curl >/dev/null 2>&1; then
    if curl -s -L -o libnet.tgz "$url"; then fetched=1; break; fi
  else
    log "No wget or curl available to fetch sources"
    break
  fi
done

if [ "$fetched" -ne 1 ]; then
  log "Failed to download libnet sources. Provide libnet headers or run this on a host with network access."
  exit 2
fi

log "Extracting libnet sources"
mkdir -p src
cd src
tar xzf ../libnet.tgz || { log "tar failed"; exit 3; }

# Find extracted directory
libdir=$(ls -1d */ 2>/dev/null | head -1 | sed 's#/##')
if [ -z "$libdir" ]; then
  log "Could not find extracted directory"
  exit 4
fi

cd "$libdir" || exit 4
log "Building lib in $(pwd)"

# Try autotools sequence if present
if [ -f configure ]; then
  ./configure --prefix=/usr/local || true
  make || true
  make install || true
else
  # Some libdnet variants expect simple Makefile
  if [ -f Makefile ]; then
    make || true
    # install headers manually if present
    mkdir -p /usr/local/include
    cp *.h /usr/local/include/ 2>/dev/null || true
    mkdir -p /usr/local/lib
    cp *.a /usr/local/lib/ 2>/dev/null || true
  fi
fi

# Re-check headers
if [ -f /usr/local/include/libnet.h ] || [ -f /usr/local/include/libdnet.h ]; then
  log "libnet headers installed under /usr/local/include"
  # Try building inviteflood with include path
  cd "$TOOLS_DIR"
  make clean || true
  CFLAGS="-I/usr/local/include" LDFLAGS="-L/usr/local/lib -lnet" make || true
  if [ -f inviteflood ]; then
    cp inviteflood "$OUT_DIR/"
    chmod +x "$OUT_DIR/inviteflood"
    log "inviteflood built and copied to $OUT_DIR/inviteflood"
    exit 0
  else
    log "inviteflood build still failed after building libnet"
    exit 5
  fi
else
  log "libnet headers still not found after attempted build"
  exit 6
fi
