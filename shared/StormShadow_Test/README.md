<div align="center">

# StormShadow SIP‑Only

Simplified SIP testing toolkit focused on spoofed SIP traffic, built on Linux iptables/NFQUEUE, ipset, and Scapy. Run attacks, a local lab (Asterisk-in-Docker), or both — via CLI or a modern Tkinter GUI.

</div>

---

## ⚠ Important usage warning

This project contains DDoS-style traffic generation and UDP source-address spoofing capabilities. It is provided strictly for educational use and authorized security testing on systems and networks you own or for which you have explicit, written permission. Unauthorized use may be illegal and can disrupt services. You are solely responsible for complying with applicable laws, organizational policies, and provider/hosting terms. Prefer the built-in lab, dry-run mode, and rate limits; do not target production systems.

## Highlights

- SIP‑focused, fast prototyping toolkit (Invite flood and more via pluggable modules)
- Clean iptables integration: isolated STORMSHADOW chains with automatic tagging and cleanup
- Optional ipset acceleration for dynamic NFQUEUE port matching with TTL
- Return‑path DNAT to re‑route responses from spoofed subnets back to the attacker
- Built‑in lab: runs an Asterisk SIP server in Docker with sensible defaults
- Self‑elevates to root when needed and preserves your virtualenv/env
- Auto‑config: detects interface, IP, ports, and queue numbers to reduce setup friction
- GUI mode for one‑click operations; CLI for scripting and automation


## Table of contents

- What is it?
- How it works (architecture)
- Requirements
- Install
- Quick start (CLI and GUI)
- Configuration
- Attack modules
- Lab (victim) environment
- Logging and cleanup
- Troubleshooting
- Development and docs
- Legal and safety


## What is it?

StormShadow SIP‑Only is a trimmed variant of the broader StormShadow project dedicated to SIP attacks and experiments. It orchestrates:

- attack flows (for example an INVITE flood), optionally with spoofed sources;
- a lab SIP server running in Docker for safe local testing;
- network plumbing using iptables, NFQUEUE/netfilterqueue, and ipset;
- an optional GUI for interactive use.


## How it works (architecture)

- Core orchestrator: `utils/core/stormshadow.py`
	- Loads configuration (`configs/sip-stormshadow-config.yaml` + CLI overrides).
	- Starts/stops AttackManager and LabManager based on flags.
	- Generates a session UID (SUID) and maintains a heartbeat file in `/run/stormshadow` to guard rules from premature cleanup.

- Configuration layer: `utils/config/config_manager.py`
	- Merges defaults with CLI parameters.
	- Resolves `auto` values for interface, IP, ports, queue numbers, etc.

- Attack layer: `utils/attack/attack_manager.py` and modules in `sip_attacks/`
	- Discovers modules (e.g., `invite_flood`).
	- For spoofing, installs NFQUEUE rules and launches the spoofer subprocess (`sip_attacks/spoofer.py`). The spoofer binds to the queue and rewrites UDP source IP/port (Scapy), then accepts the packet.

- Networking helpers: `utils/network/iptables.py`
	- Creates isolated chains: `STORMSHADOW` (filter) and `STORMSHADOW-NAT` (nat), anchored from main chains with comments tagged like `Stormshadow:<SUID>:<ts>:...`.
	- Two ways to send flows to NFQUEUE:
		1) ipset‑backed single rule with per‑port TTL; or
		2) direct per‑port NFQUEUE rules in `STORMSHADOW`.
	- Return path: DNAT rules in `STORMSHADOW-NAT` to forward responses from spoofed subnets back to the attacker’s IP/port.
	- Startup cleanup removes stale rules safely using timestamps and heartbeats.

- Lab layer: `utils/lab_manager.py`
	- Builds/runs Docker image `asterisk-sip-server` from `sip-lab/sip_server/` and starts container `sip-victim` with `--network host` and NET_ADMIN/NET_RAW caps.

- GUI layer: `gui/main_gui.py` + `gui/*`
	- Tkinter UI on top of the same managers. The GUI will request elevation for privileged operations when needed.


## Requirements

- OS: Linux
- Python: 3.13+
- Root privileges for networking operations (handled by self‑elevation via sudo)
- System dependencies:
	- iptables and ipset
	- libnetfilter‑queue and headers (for python `netfilterqueue`)
	- Docker (for the lab)

Notes:
- The project uses `scapy` and `netfilterqueue` to intercept and rewrite UDP packets.
- If `ipset` isn’t available, the toolkit falls back to direct per‑port iptables rules.


## Install

Choose one of the following workflows.

1) Using pip + venv (recommended)

```sh
# zsh-compatible
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

2) Using uv (if you prefer lockfile-driven installs)

```sh
# zsh-compatible
pip install uv  # optional if uv is not available
uv sync
```

System packages (example for Debian/Ubuntu — adapt to your distro):

```sh
sudo apt-get update
sudo apt-get install -y iptables ipset docker.io libnetfilter-queue-dev
```


## Quick start

The program self‑elevates when root is required. You can run it without `sudo`; it will re‑exec with sudo while preserving your current virtualenv and environment.

Attack only (default auto-detection for interface/IP/ports/queues):

```sh
python3 main.py --mode attack --attack-name invite_flood
```

Lab only (runs a local Asterisk SIP server in Docker):

```sh
python3 main.py --mode lab
```

Both lab and attack:

```sh
python3 main.py --mode both --attack-name invite_flood
```

GUI mode:

```sh
python3 main.py --mode gui
```

Dry run (no side effects; shows what would be done):

```sh
python3 main.py --mode both --attack-name invite_flood --dry-run
```

Use a custom config file:

```sh
python3 main.py --mode attack --attack-name invite_flood --config configs/sip-stormshadow-config.yaml
```

Useful flags (subset):

- `--target-ip` and `--target-port` to override destination
- `--max_count` to cap packets (e.g., INVITE count)
- `--spoofing/--no-spoofing` to toggle spoofing
- `--return-path/--no-return-path` to toggle DNAT return path
- `--verbosity {quiet|info|debug}` for logging
- `--open_window` to open a terminal for subprocesses
- `--keep-lab-open` to leave the lab running after main exits


## Configuration

Main config: `configs/sip-stormshadow-config.yaml`

Key sections and behaviors:

- `app.enabled.*`: feature toggles (attack, lab, defense, spoofing, return_path, metrics, gui, dry_run, open_window)
- `network.*`: interface and IP autodetection, SIP port
- `attack.*`: `attack_name`, `target_ip/port`, `source_port`, `attack_queue_num`, `spoofing_subnet`, rate, delays, `max_count`
- `metrics.*`: ack port and queue number for return‑path metrics
- `lab.*`: docker name, whether to open a window, and `return_path` settings (DNAT target, port, spoofed subnet)

Auto‑values: Many keys accept `auto` and are resolved at startup (interface, IP, ports, queue numbers, window behavior). CLI flags override config.


## Attack modules

- Location: `sip_attacks/`
- Select with `--attack-name` or via `attack.attack_name` in the config.
- Example shipped module: `invite_flood` (floods SIP INVITE messages; supports spoofing via NFQUEUE + spoofer process).

Create your own module by following the patterns used in `sip_attacks/` and wiring it via `attack_name`.


## Lab (victim) environment

The lab manager builds and starts Docker image `asterisk-sip-server` from `sip-lab/sip_server/` as container `sip-victim` with:

- `--network host`, `--cap-add NET_ADMIN`, `--cap-add NET_RAW`
- Env vars like `SPOOFED_SUBNET` and `RETURN_ADDR`

You can run lab alone (`--mode lab`) or together with attacks (`--mode both`). Use `--keep-lab-open` to leave it running when the main process exits.


## Logging and cleanup

- Verbosity is controlled by `--verbosity` or `log.verbosity_level`.
- Optional log to file if enabled in config (`log.file`).
- iptables rules are tagged per session with a SUID (e.g., `Stormshadow:<SUID>:<ts>:...`).
- A heartbeat file in `/run/stormshadow/<SUID>.hb` keeps the session “fresh”. On startup, stale rules without a fresh heartbeat are cleaned automatically.
- On shutdown, rules for the active SUID are removed.


## Troubleshooting

- OSError while binding NFQUEUE / queue already in use
	- Another process may be using the queue; choose a different `attack_queue_num` or stop the conflicting process.
	- Ensure `netfilterqueue` is installed and the kernel module is available.

- ipset not found
	- Install `ipset`. The toolkit will fall back to direct iptables rules if missing, but ipset provides better control and auto‑expiry.

- Permission denied / sudo prompts
	- The app self‑elevates when needed. If elevation fails, run from a TTY where sudo can prompt, or configure passwordless sudo for the required commands.

- Docker image build fails
	- Verify Docker is installed and you can run it (or that sudo can run it). The build context is `sip-lab/sip_server/`.

- No rules cleaned up after a crash
	- Start the app again; startup cleanup removes stale rules based on timestamps/heartbeats. As a last resort, review rules in the `STORMSHADOW` chains before removing anything manually.


## Development and docs

- Project entry point: `main.py`
- GUI entry point: `gui/main_gui.py`
- PyInstaller spec: `stormshadow.spec` (optional packaging)
- Docs: Sphinx sources under `source/` (build with `make -C source html`)
- Python dependencies are defined in `pyproject.toml`; optional dev tools: `ruff`, `pytest`.


## Legal and safety

This toolkit is for educational and defensive testing only. By using it, you agree to:

- Operate solely on systems and networks you own or have explicit, written authorization to test.
- Comply with applicable laws, regulations, organizational policies, and provider/hosting terms.
- Understand that certain features can generate high-rate traffic and spoof UDP source addresses, which can disrupt services if misused.
- Accept full responsibility for any consequences of your actions; the authors and contributors disclaim all liability.

Best practices:
- Use the included lab environment for safe experiments.
- Start with dry-run mode and conservative rate/packet limits.
- Avoid targeting production infrastructure and third-party services.

Author: Corentin COUSTY