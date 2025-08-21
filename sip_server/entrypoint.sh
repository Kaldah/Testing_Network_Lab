#!/bin/sh
set -e

echo "[*] Starting Asterisk SIP Server..."

# Ensure config directory exists (mounted by compose)
mkdir -p /etc/asterisk

# Start Asterisk in the foreground with console logging
exec /usr/sbin/asterisk -f -T -vvv -U asterisk -G asterisk