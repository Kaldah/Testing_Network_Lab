#!/usr/bin/env pwsh
# start.ps1 - Build and start the SIP test lab (Windows PowerShell version)
#
# Usage:
#   .\start.ps1                    # build and up (detached)
#   .\start.ps1 -ExposeSip         # also publish 5060/tcp,udp to host
#   .\start.ps1 -Attach            # attach shell to attacker after start
#   .\start.ps1 -OpenWindows       # open terminal windows for each container
#   .\start.ps1 -ExposeSip -OpenWindows -Attach  # combine options

param(
    [switch]$ExposeSip,
    [switch]$Attach,
    [switch]$OpenWindows,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\start.ps1 [options]"
    Write-Host "Options:"
    Write-Host "  -ExposeSip      Expose SIP 5060/tcp,udp ports to host"
    Write-Host "  -Attach         Attach to attacker shell after start"
    Write-Host "  -OpenWindows    Open terminal windows for each container"
    Write-Host "  -Help           Show this help"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\start.ps1                           # Basic start"
    Write-Host "  .\start.ps1 -ExposeSip -OpenWindows"
    Write-Host "  .\start.ps1 -ExposeSip -OpenWindows -Attach"
    exit 0
}

$composeFile = "docker-compose.yaml"

# Optionally enable ports by generating an override on the fly
$overrideFile = "docker-compose.override.ports.yaml"
if ($ExposeSip) {
    $overrideContent = @"
services:
  sip_server:
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
"@
    Set-Content -Path $overrideFile -Value $overrideContent
    $env:COMPOSE_FILE = "$composeFile`:$overrideFile"
} else {
    $env:COMPOSE_FILE = $composeFile
}

Write-Host "[*] Building images..." -ForegroundColor Green
docker compose build

Write-Host "[*] Starting lab..." -ForegroundColor Green
docker compose up -d

Write-Host "[*] Lab is up. Network: sip_lab_net (10.10.0.0/24)" -ForegroundColor Yellow
Write-Host "    - Attacker: 10.10.0.2 (container: sip-attacker)"
Write-Host "    - SIP server: 10.10.0.3 (container: asterisk-sip)"
Write-Host "    - OpenWRT router: 10.10.0.4 (container: openwrt-router)"
if ($ExposeSip) {
    Write-Host "    - SIP 5060 published to host (udp/tcp)"
} else {
    Write-Host "    - SIP ports NOT exposed to host (internal only)"
}

if ($Attach) {
    Write-Host "[*] Attaching to attacker shell... (exit to detach)" -ForegroundColor Green
    try {
        docker compose exec attacker bash
    } catch {
        try {
            docker compose exec attacker sh
        } catch {
            Write-Host "[!] Could not attach to attacker container" -ForegroundColor Red
        }
    }
}

# Function to open terminal window for a container
function Open-ContainerTerminal {
    param(
        [string]$ContainerName,
        [string]$ContainerTitle,
        [string]$TerminalCmd
    )
    
    # Simply start the corresponding batch file
    $batchFile = "connect-$ContainerName.bat"
    if (Test-Path $batchFile) {
        Start-Process "cmd" -ArgumentList "/c", "start", $batchFile
    } else {
        Write-Host "[!] Batch file $batchFile not found. You can manually connect using:"
        Write-Host "    docker compose exec $ContainerName $TerminalCmd"
    }
}

if ($OpenWindows) {
    Write-Host "[*] Opening terminal windows for each container..." -ForegroundColor Green
    
    # Wait a moment for containers to be fully ready
    Start-Sleep -Seconds 2
    
    # Check if Windows Terminal is available
    $wtExists = Get-Command "wt" -ErrorAction SilentlyContinue
    if ($wtExists) {
        Write-Host "[*] Using Windows Terminal for container windows" -ForegroundColor Cyan
    } else {
        Write-Host "[*] Windows Terminal not found, using PowerShell windows" -ForegroundColor Yellow
        Write-Host "    Install Windows Terminal for better experience: https://aka.ms/terminal"
    }
    
    # Open terminals for each container using simple batch files
    Open-ContainerTerminal -ContainerName "attacker" -ContainerTitle "SIP Lab - Attacker (10.10.0.2)" -TerminalCmd "bash"
    Open-ContainerTerminal -ContainerName "sip_server" -ContainerTitle "SIP Lab - Asterisk Server (10.10.0.3)" -TerminalCmd "sh"
    Open-ContainerTerminal -ContainerName "openwrt" -ContainerTitle "SIP Lab - OpenWRT Router (10.10.0.4)" -TerminalCmd "sh"
    
    Write-Host "[*] Terminal windows opened. Close them when done testing." -ForegroundColor Green
}

Write-Host "[*] Done. Use 'docker compose logs -f' to follow logs or 'docker compose exec <container> <shell>' to get a shell." -ForegroundColor Green
Write-Host ""
Write-Host "Manual connection commands:" -ForegroundColor Cyan
Write-Host "    docker compose exec attacker bash"
Write-Host "    docker compose exec sip_server sh"
Write-Host "    docker compose exec openwrt sh"
