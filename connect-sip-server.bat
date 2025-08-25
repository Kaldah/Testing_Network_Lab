@echo off
title SIP Lab - SIP Server (10.10.0.3)
cd /d "%~dp0"
echo Connecting to SIP Server container...
docker compose exec sip_server sh
pause
