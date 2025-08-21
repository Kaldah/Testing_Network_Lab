#!/usr/bin/env bash
set -euo pipefail

# Ensure we run as root for iptables setup
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "[attacker] Must run as root. Current UID: $(id -u)" >&2
  exec sudo -E "$0" "$@"
fi

# Set a distinct prompt
export PS1='[attacker \u@\h \W]# '

# Create a throw-away iptables namespace using nft (if available) or flush existing rules.
# Note: Docker already isolates network namespace per container.
# We just ensure policy is permissive but visible to the student.

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
