#!/usr/bin/env bash
set -euo pipefail

# Ensure we run as root for iptables setup
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "[attacker] Must run as root. Current UID: $(id -u)" >&2
  exec sudo -E "$0" "$@"
fi

# Set a distinct prompt
export PS1='[attacker \u@\h \W]# '

# Add compiled binaries to PATH (prioritize pre-compiled tools)
export PATH="/usr/local/bin/local-compiled:/usr/local/bin:${PATH}"

# Copy pre-compiled binaries from /tmp cache or compile from source
if [[ -f "/tmp/inviteflood" && -x "/tmp/inviteflood" ]]; then
  echo "[attacker] Using cached inviteflood from /tmp..."
  mkdir -p /usr/local/bin/local-compiled
  cp /tmp/inviteflood /usr/local/bin/local-compiled/inviteflood
  chmod +x /usr/local/bin/local-compiled/inviteflood
  echo "[attacker] Successfully installed inviteflood from cache"
elif [[ -d "/app/shared/compiled-binaries/linux-x86_64/inviteflood-master" ]]; then
  echo "[attacker] Compiling inviteflood from source in /tmp..."
  mkdir -p /usr/local/bin/local-compiled
  cd /tmp
  cp /app/shared/compiled-binaries/linux-x86_64/inviteflood-master/inviteflood/inviteflood.c . 2>/dev/null || true
  cp /app/shared/compiled-binaries/linux-x86_64/inviteflood-master/inviteflood/inviteflood.h . 2>/dev/null || true
  cp /app/shared/compiled-binaries/linux-x86_64/inviteflood-master/hack_library/hack_library.h . 2>/dev/null || true
  cp /app/shared/compiled-binaries/linux-x86_64/inviteflood-master/hack_library/hack_library.o . 2>/dev/null || true
  
  if [[ -f "inviteflood.c" && -f "hack_library.o" ]]; then
    gcc -no-pie -I. inviteflood.c -lnet hack_library.o -o inviteflood 2>/dev/null || true
    if [[ -f "inviteflood" ]]; then
      cp inviteflood /usr/local/bin/local-compiled/inviteflood
      chmod +x /usr/local/bin/local-compiled/inviteflood
      echo "[attacker] Successfully compiled and installed inviteflood"
    fi
  fi
  cd /
fi

# Create symbolic link for easy access to inviteflood (if not already there)
if [[ -f "/usr/local/bin/local-compiled/inviteflood" ]]; then
  ln -sf /usr/local/bin/local-compiled/inviteflood /usr/local/bin/inviteflood 2>/dev/null || true
  echo "[attacker] Found inviteflood binary at /usr/local/bin/local-compiled/inviteflood"
else
  echo "[attacker] No inviteflood binary found at /usr/local/bin/local-compiled/inviteflood"
fi

# Debug: Show what's in the bin directory
echo "[attacker] Contents of /usr/local/bin:"
ls -la /usr/local/bin/ 2>/dev/null || echo "Directory not accessible"

# Create a throw-away iptables namespace using nft (if available) or flush existing rules.
# Note: Docker already isolates network namespace per container.
# We just ensure policy is permissive but visible to the student.

# Load required kernel modules for NFQUEUE functionality
echo "[attacker] Setting up NFQUEUE support in container network namespace..."

# Ensure we're using legacy iptables for better NFQUEUE compatibility
update-alternatives --set iptables /usr/sbin/iptables-legacy 2>/dev/null || true
update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy 2>/dev/null || true

# Try to load kernel modules (may fail in some environments, that's OK)
modprobe nfnetlink 2>/dev/null && echo "[attacker] nfnetlink module loaded" || echo "[attacker] nfnetlink module already loaded or not needed"
modprobe nfnetlink_queue 2>/dev/null && echo "[attacker] nfnetlink_queue module loaded" || echo "[attacker] nfnetlink_queue module already loaded or not needed"
modprobe xt_NFQUEUE 2>/dev/null && echo "[attacker] xt_NFQUEUE module loaded" || echo "[attacker] xt_NFQUEUE module already loaded or not needed"

# Check if NFQUEUE is available
if [ -f /proc/net/netfilter/nfnetlink_queue ]; then
    echo "[attacker] ✓ NFQUEUE support is available"
else
    echo "[attacker] ⚠ NFQUEUE support may be limited in this environment"
fi

# IPv4
iptables -P INPUT ACCEPT || true
iptables -P OUTPUT ACCEPT || true
iptables -P FORWARD ACCEPT || true

# Create some convenience chains if not exist
for c in NFQ-IN NFQ-OUT SPOOF TEST; do
  iptables -N "$c" 2>/dev/null || true
  iptables -F "$c" || true
done

# IPv6 (best-effort; SIP often UDP/IPv4 here)
if command -v ip6tables >/dev/null 2>&1; then
  ip6tables -P INPUT ACCEPT || true
  ip6tables -P OUTPUT ACCEPT || true
  ip6tables -P FORWARD ACCEPT || true
fi

# Show interface info
ip -brief addr || true
ip route || true

cat <<'EOT'
[attacker] Ready.
- StormShadow is mounted at /app/shared/StormShadow
- Python venv is at /opt/venv (already on PATH)
- inviteflood is available (try: inviteflood -h)
- tcpdump installed for packet capture

StormShadow Setup:
  # Run StormShadow's built-in setup (recommended)
  cd /app/shared/StormShadow && python3 setup.py --python-only

  # Or full setup including tools
  cd /app/shared/StormShadow && python3 setup.py

  # Run your tool after setup
  python /app/shared/StormShadow/main.py --help

Other Examples:
  # Simple NFQUEUE demo
  iptables -I OUTPUT -p udp --dport 5060 -j NFQUEUE --queue-num 0

  # Run FastAPI dev server if your tool has one
  cd /app/shared/StormShadow && uvicorn main:app --reload --host 0.0.0.0 --port 8080
EOT

exec "$@"
