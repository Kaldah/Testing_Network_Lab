@echo off
title SIP Lab - OpenWRT Router (10.10.0.4)
cd /d "%~dp0"
echo Connecting to OpenWRT Router container...
docker compose exec openwrt sh
pause
