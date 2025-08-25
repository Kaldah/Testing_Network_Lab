@echo off
title SIP Lab - Attacker (10.10.0.2)
cd /d "%~dp0"
echo Connecting to Attacker container...
docker compose exec attacker bash
pause
