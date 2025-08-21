#!/bin/sh
set -e

# Set a distinct prompt for OpenWRT
export PS1='[openwrt \u@\h \W]# '

# Show network interface info
echo "[OpenWRT] Network interfaces:"
ip -brief addr || true
echo

echo "[OpenWRT] Available Python:"
python3 --version || echo "Python3 not available"
echo

echo "[OpenWRT] OpenWRT version:"
cat /etc/openwrt_release 2>/dev/null || echo "Release info not found"
echo

cat <<'EOT'
[OpenWRT] Router ready.
- This is OpenWRT 24.10.2 running in a container
- Python3 and pip are available
- Network admin capabilities enabled for routing/firewall testing
- Can be used as a router/gateway between network segments

Examples:
  # Install additional packages
  opkg update && opkg install tcpdump iptables-mod-nfqueue

  # Set up routing/NAT rules
  iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

  # Monitor traffic
  tcpdump -i any -n
EOT

exec "$@"
