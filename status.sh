#!/usr/bin/env bash
set -euo pipefail

# status.sh - Check the status of the SIP lab

echo "SIP Lab Status"
echo "=============="
echo ""

# Check if containers are running
if docker compose ps --quiet 2>/dev/null | grep -q .; then
  echo "🟢 Lab is RUNNING"
  echo ""
  echo "Containers:"
  docker compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}"
  
  echo ""
  echo "Network Information:"
  echo "- Network: sip_lab_net (10.10.0.0/24)"
  echo "- Attacker:    10.10.0.2 (container: sip-attacker)"
  echo "- SIP Server:  10.10.0.3 (container: asterisk-sip)"
  echo "- OpenWRT:     10.10.0.4 (container: openwrt-router)"
  
  echo ""
  echo "Quick Commands:"
  echo "  docker compose exec attacker bash     # Access attacker"
  echo "  docker compose exec sip_server sh     # Access SIP server"
  echo "  docker compose exec openwrt sh        # Access OpenWRT"
  echo "  ./open-windows.sh                     # Open terminal windows"
  echo "  ./stop.sh                             # Stop lab"
else
  echo "🔴 Lab is STOPPED"
  echo ""
  echo "Start the lab with:"
  echo "  ./start.sh                    # Basic start"
  echo "  ./start.sh --open-windows     # Start with terminal windows"
  echo ""
  echo "Or rebuild if needed:"
  echo "  ./build.sh                    # Build images"
  echo "  ./rebuild.sh                  # Complete rebuild with tests"
fi

echo ""
echo "Images:"
docker images | grep -E "(sip-lab|REPOSITORY)" || echo "No sip-lab images found"
