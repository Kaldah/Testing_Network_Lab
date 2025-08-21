#!/usr/bin/env python3
"""
StormShadow setup helper.

- Installs Python dependencies (uv or pip/requirements.txt)
- Ensures external tool "inviteflood" is available via PATH/local/build/pkg manager

Usage:
  python3 setup.py                # full setup
  python3 setup.py --python-only  # only python deps
    python3 setup.py --tools-only         # only inviteflood tool
    python3 setup.py --with-tools-install # attempt to install/build inviteflood via pkg/build
    python3 setup.py --no-uv              # force pip even if uv is installed
    python3 setup.py --use-uv             # force using uv (auto-install if missing) and create .venv
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent
TOOLS_DIR = ROOT / "external-tools"
BIN_DIR = TOOLS_DIR / "bin"


def log(level: str, msg: str) -> None:
    colors = {
        "info": "\033[0;32m",
        "warn": "\033[1;33m",
        "error": "\033[0;31m",
    }
    reset = "\033[0m"
    color = colors.get(level, "")
    print(f"{color}[setup]{reset} {msg}")


def print_usage_warning() -> None:
    banner = (
        "\n"
        "==============================================================\n"
        " StormShadow: Educational and authorized testing only\n"
        "==============================================================\n"
        "This toolkit can generate high-rate SIP traffic and spoof UDP\n"
        "source addresses. Use ONLY on systems/networks you own or have\n"
        "explicit, written permission to test. Unauthorized use may be\n"
        "illegal and disruptive. You are responsible for compliance with\n"
        "laws, policies, and provider terms. Prefer the built-in lab and\n"
        "dry-run and keep rates conservative.\n"
        "==============================================================\n"
    )
    print(banner)


def run(cmd: List[str], check: bool = True, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    log("info", f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, env=env, text=True, capture_output=False)


def have_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def check_netfilterqueue_deps() -> bool:
    """Check if system dependencies for netfilterqueue compilation are available."""
    import shutil
    
    missing_deps: List[str] = []
    
    # Check for pkg-config and required libraries
    if shutil.which("pkg-config"):
        try:
            subprocess.run(["pkg-config", "--exists", "libnetfilter_queue"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            missing_deps.append("libnetfilter-queue-dev")
            
        try:
            subprocess.run(["pkg-config", "--exists", "libnfnetlink"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            missing_deps.append("libnfnetlink-dev")
    else:
        # Check for header files directly
        if not Path("/usr/include/libnetfilter_queue/libnetfilter_queue.h").exists():
            missing_deps.append("libnetfilter-queue-dev")
        if not Path("/usr/include/libnfnetlink/libnfnetlink.h").exists():
            missing_deps.append("libnfnetlink-dev")
    
    # Check for kernel headers
    if not Path("/usr/include/linux").exists():
        missing_deps.append("linux-libc-dev or linux-headers")
    
    if missing_deps:
        log("warn", "Missing system dependencies for netfilterqueue compilation:")
        for dep in missing_deps:
            log("warn", f"  - {dep}")
        
        if shutil.which("apt-get"):
            log("info", "To install on Debian/Ubuntu, run:")
            print("  sudo apt-get update")
            print("  sudo apt-get install -y build-essential libnetfilter-queue-dev libnfnetlink-dev linux-libc-dev")
        elif shutil.which("dnf"):
            log("info", "To install on Fedora/RHEL, run:")
            print("  sudo dnf install -y gcc make libnetfilter_queue-devel libnfnetlink-devel kernel-headers")
        elif shutil.which("pacman"):
            log("info", "To install on Arch Linux, run:")
            print("  sudo pacman -S base-devel libnetfilter_queue libnfnetlink linux-headers")
        
        return False
    return True


def install_requirements_separately(venv_python: Path, req_file: Path) -> None:
    """Install each package individually, continuing on failures."""
    failed_packages: List[str] = []
    
    with open(req_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            package_spec = line
            package_name = line.split('>=')[0].split('==')[0].split('>')[0].split('<')[0].split('!')[0]
            
            log("info", f"Installing: {package_spec}")
            try:
                run([str(venv_python), "-m", "pip", "install", package_spec])
                log("info", f"✓ Successfully installed: {package_name}")
            except subprocess.CalledProcessError:
                log("warn", f"✗ Failed to install: {package_name}")
                failed_packages.append(package_name)
                
                # Special handling for netfilterqueue
                if "netfilterqueue" in package_name:
                    log("warn", "netfilterqueue failed to install - IP spoofing features will not be available")
                    log("warn", "This is expected if system dependencies are missing")
    
    if failed_packages:
        log("warn", "The following packages failed to install:")
        for pkg in failed_packages:
            log("warn", f"  - {pkg}")
        log("warn", "Some features may not work. Consider installing missing system dependencies.")


def install_python_deps(force_no_uv: bool = False, force_use_uv: bool = False) -> None:
    req = ROOT / "requirements.txt"
    pyproject = ROOT / "pyproject.toml"

    # Check if netfilterqueue dependencies are available
    can_compile_netfilterqueue = check_netfilterqueue_deps()
    if not can_compile_netfilterqueue:
        log("warn", "netfilterqueue compilation will likely fail due to missing system dependencies")
        
        # In non-interactive environments, continue anyway
        if sys.stdin.isatty():
            response = input("Continue anyway? Some features may not work. [y/N] ").strip().lower()
            if response not in ['y', 'yes']:
                log("error", "Installation cancelled. Please install the required system packages first.")
                return
        else:
            log("info", "Non-interactive mode: continuing with installation (netfilterqueue will be skipped on failure)")

    def try_install_uv() -> bool:
        # Prefer pipx if available, else use official installer, else pip --user
        if have_cmd("pipx"):
            log("info", "Using pipx to install uv")
            cp = subprocess.run(["pipx", "install", "uv"], text=True)
            if cp.returncode == 0:
                return True
        if have_cmd("curl"):
            log("info", "Using official install script to install uv")
            cp = subprocess.run(["bash", "-lc", "curl -LsSf https://astral.sh/uv/install.sh | sh"], text=True)
            if cp.returncode == 0:
                # Refresh PATH for common installers
                os.environ["PATH"] = f"{os.path.expanduser('~')}/.local/bin:{os.path.expanduser('~')}/.cargo/bin:" + os.environ.get("PATH", "")
                return have_cmd("uv")
        # Fallback to pip --user
        if have_cmd("python3"):
            log("warn", "Falling back to user install via pip")
            cp = subprocess.run(["python3", "-m", "pip", "install", "--user", "uv"], text=True)
            if cp.returncode == 0:
                os.environ["PATH"] = f"{os.path.expanduser('~')}/.local/bin:" + os.environ.get("PATH", "")
                return have_cmd("uv")
        return False

    # Default quick path: pip+venv unless --use-uv is explicitly set
    use_uv = False
    if force_use_uv:
        use_uv = True
        if not have_cmd("uv"):
            if not try_install_uv():
                log("warn", "Could not auto-install uv; falling back to pip/venv")
                use_uv = False

    if use_uv:
        log("info", "Installing Python deps with uv (creating .venv)")
        # Ensure a project venv exists
        run(["uv", "venv", str(ROOT / ".venv")])
        if pyproject.exists():
            run(["uv", "sync"])  # uses uv.lock if present
        elif req.exists():
            run(["uv", "pip", "install", "-r", str(req)])
        else:
            log("warn", "No pyproject.toml or requirements.txt found; skipping Python deps")
        return

    # Fallback: pip + venv
    if req.exists():
        venv = ROOT / ".venv"
        if not venv.exists():
            log("info", f"Creating virtual environment at {venv}")
            result = run([sys.executable, "-m", "venv", str(venv)], check=False)
            if result.returncode != 0:
                log("error", "Failed to create virtual environment")
                return
        
        # Verify venv was created successfully
        python_bin = venv / "bin" / "python"
        pip_bin = venv / "bin" / "pip"
        if not python_bin.exists():
            log("error", "Virtual environment creation failed - python executable not found")
            return
            
        # Install dependencies in venv
        run([str(python_bin), "-m", "pip", "install", "--upgrade", "pip"])
        if can_compile_netfilterqueue:
            run([str(pip_bin), "install", "-r", str(req)])
        else:
            # Install packages one by one, skipping failures
            install_requirements_separately(python_bin, req)
    elif pyproject.exists():
        log("warn", "pyproject.toml found, but this is not a buildable Python project. Skipping pip install .; using requirements.txt only.")
    else:
        log("warn", "No dependency manifest found; skipping Python deps")


def attempt_pkg_install_inviteflood() -> bool:
    # Best-effort installation via common package managers.
    # Name may vary across distros.
    def sudo() -> List[str]:
        result = run(["sudo", "-n", "true"], check=False)
        return ["sudo", "-n"] if result.returncode == 0 else ["sudo"]

    if have_cmd("apt-get"):
        log("info", "Trying apt-get to install inviteflood")
        run(sudo() + ["apt-get", "update", "-y"], check=False)
        return run(sudo() + ["apt-get", "install", "-y", "inviteflood"], check=False).returncode == 0
    if have_cmd("dnf"):
        log("info", "Trying dnf to install inviteflood")
        return run(sudo() + ["dnf", "install", "-y", "inviteflood"], check=False).returncode == 0
    if have_cmd("pacman"):
        log("info", "Trying pacman to install inviteflood")
        return run(sudo() + ["pacman", "-Sy", "--noconfirm", "inviteflood"], check=False).returncode == 0
    if have_cmd("zypper"):
        log("info", "Trying zypper to install inviteflood")
        return run(sudo() + ["zypper", "--non-interactive", "install", "inviteflood"], check=False).returncode == 0
    log("warn", "No supported package manager detected for inviteflood")
    return False


def build_from_source_inviteflood() -> bool:
    src = TOOLS_DIR / "inviteflood"
    if not src.is_dir():
        log("warn", f"No source dir at {src} to build inviteflood from")
        return False

    log("info", f"Attempting to build inviteflood from {src}")
    made = False
    if (src / "Makefile").exists():
        made = run(["make", "-C", str(src)], check=False).returncode == 0
    elif (src / "CMakeLists.txt").exists():
        build = src / "build"
        build.mkdir(exist_ok=True)
        r1 = run(["cmake", "-S", str(src), "-B", str(build)], check=False).returncode == 0
        r2 = run(["cmake", "--build", str(build), "--config", "Release"], check=False).returncode == 0
        made = r1 and r2
    elif (src / "configure").exists():
        made = run(["bash", "-lc", f"cd {src} && ./configure && make"], check=False).returncode == 0
    else:
        log("warn", "No Makefile/CMakeLists.txt/configure found; cannot build")
        return False

    if not made:
        log("warn", "Build failed for inviteflood")
        return False

    # Find the binary
    for root, _dirs, files in os.walk(src):
        if "inviteflood" in files:
            candidate = Path(root) / "inviteflood"
            if os.access(candidate, os.X_OK):
                BIN_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, BIN_DIR / "inviteflood")
                os.chmod(BIN_DIR / "inviteflood", 0o755)
                log("info", f"Installed inviteflood to {BIN_DIR / 'inviteflood'}")
                return True
    log("warn", "Build completed but could not locate inviteflood binary")
    return False


def ensure_inviteflood() -> bool:
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    # PATH
    path_bin = shutil.which("inviteflood")
    if path_bin:
        log("info", f"inviteflood found in PATH: {path_bin}")
        # symlink to local bin for consistency
        dst = BIN_DIR / "inviteflood"
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(path_bin, dst)
        return True

    # local file external-tools/inviteflood
    local_file = TOOLS_DIR / "inviteflood"
    if local_file.is_file() and os.access(local_file, os.X_OK):
        shutil.copy2(local_file, BIN_DIR / "inviteflood")
        os.chmod(BIN_DIR / "inviteflood", 0o755)
        log("info", f"Using local inviteflood: {local_file}")
        return True

    # In quick mode, do not attempt to install/build tools automatically.
    # These are enabled by --with-tools-install in main().

    log("warn", "inviteflood could not be set up automatically.")
    log("warn", f"Options:\n  - Place the compiled binary at {local_file} and re-run\n  - Put source in {TOOLS_DIR}/inviteflood and re-run to build\n  - Install it system-wide so it's in PATH and re-run")
    return False


def link_inviteflood_into_venv() -> None:
    venv_bin = ROOT / ".venv" / "bin"
    src = BIN_DIR / "inviteflood"
    if venv_bin.is_dir() and src.exists():
        dst = venv_bin / "inviteflood"
        try:
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            os.symlink(src, dst)
            log("info", f"Linked inviteflood into virtualenv: {dst}")
        except OSError:
            # Fallback to copy if symlink not allowed
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
            log("info", f"Copied inviteflood into virtualenv: {dst}")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Setup StormShadow")
    p.add_argument("--python-only", action="store_true")
    p.add_argument("--tools-only", action="store_true")
    p.add_argument("--no-uv", action="store_true")
    p.add_argument("--use-uv", action="store_true")
    p.add_argument("--with-tools-install", action="store_true")
    args = p.parse_args(argv)

    # Show safety/usage warning banner
    print_usage_warning()

    if not args.tools_only:
        install_python_deps(force_no_uv=args.no_uv, force_use_uv=args.use_uv)
    if not args.python_only:
        # Quick path: only wire existing inviteflood into local bin
        ok = ensure_inviteflood()
        if not ok and args.with_tools_install:
            # Try package manager install
            if attempt_pkg_install_inviteflood():
                path_bin = shutil.which("inviteflood")
                if path_bin:
                    dst = BIN_DIR / "inviteflood"
                    if dst.exists() or dst.is_symlink():
                        dst.unlink()
                    os.symlink(path_bin, dst)
                    ok = True
            # Try source build if source dir exists
            if not ok and (TOOLS_DIR / "inviteflood").is_dir():
                ok = build_from_source_inviteflood()

    # Ensure the tool is accessible inside the venv as well
    link_inviteflood_into_venv()

    log("info", "Setup complete.")
    bin_path = BIN_DIR / "inviteflood"
    if bin_path.exists():
        log("info", f"inviteflood available at {bin_path}")
    else:
        log("warn", "inviteflood not installed; some attacks may not run until installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
