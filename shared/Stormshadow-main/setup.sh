#!/usr/bin/env bash

# Setup script for StormShadow
# - Installs Python dependencies (prefers uv, falls back to pip + requirements.txt)
# - Ensures external tool "inviteflood" is available via:
#     1) PATH detection (symlink into external-tools/bin)
#     2) Local binary at external-tools/inviteflood
#     3) Build from external-tools/inviteflood (Makefile/CMake/configure)
#     4) Package manager quick-install attempts (apt/dnf/pacman/zypper)
#
# Usage:
#   ./setup.sh                # quick setup (pip+venv, link inviteflood if present)
#   ./setup.sh --python-only  # only python deps
#   ./setup.sh --tools-only   # only inviteflood tool
#   ./setup.sh --with-tools-install  # attempt to install/build inviteflood via pkg/build
#   ./setup.sh --no-uv        # force pip/requirements.txt even if uv is installed
#   ./setup.sh --use-uv       # force using uv (auto-install if missing) and create .venv
#
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_DIR="$ROOT_DIR/external-tools"
BIN_DIR="$TOOLS_DIR/bin"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
PYPROJECT_FILE="$ROOT_DIR/pyproject.toml"

COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_RESET='\033[0m'

log_info()  { echo -e "${COLOR_GREEN}[setup]${COLOR_RESET} $*"; }
log_warn()  { echo -e "${COLOR_YELLOW}[setup]${COLOR_RESET} $*"; }
log_error() { echo -e "${COLOR_RED}[setup]${COLOR_RESET} $*"; }

ensure_dirs() {
  mkdir -p "$BIN_DIR"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

prompt_yes_no() {
  # usage: prompt_yes_no "Question? [Y/n] " default_yes|default_no
  local prompt="$1"
  local default="$2"
  local reply
  if [ -t 0 ]; then
    read -r -p "$prompt" reply || reply=""
  else
    # Non-interactive: use default
    reply=""
  fi
  case "$reply" in
    [Yy]* ) return 0 ;;
    [Nn]* ) return 1 ;;
    * ) if [ "$default" = "default_yes" ]; then return 0; else return 1; fi ;;
  esac
}

install_uv() {
  log_info "Attempting to install uv (fast Python package manager)"
  if have_cmd pipx; then
    log_info "Using pipx to install uv"
    if pipx install uv; then return 0; fi
  fi
  if have_cmd curl; then
    log_info "Using official install script to install uv"
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
      # Try to pick up common install locations
      export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
      if have_cmd uv; then return 0; fi
    fi
  fi
  if have_cmd python3; then
    log_warn "Falling back to user install via pip"
    if python3 -m pip install --user uv; then
      export PATH="$HOME/.local/bin:$PATH"
      if have_cmd uv; then return 0; fi
    fi
  fi
  log_warn "Could not auto-install uv. Please install it manually and re-run."
  return 1
}

check_netfilterqueue_deps() {
  # Check if required system packages for netfilterqueue compilation are available
  local missing_deps=()
  
  if have_cmd pkg-config; then
    if ! pkg-config --exists libnetfilter_queue 2>/dev/null; then
      missing_deps+=("libnetfilter-queue-dev")
    fi
    if ! pkg-config --exists libnfnetlink 2>/dev/null; then
      missing_deps+=("libnfnetlink-dev")
    fi
  else
    # Check for header files directly
    if [[ ! -f /usr/include/libnetfilter_queue/libnetfilter_queue.h ]]; then
      missing_deps+=("libnetfilter-queue-dev")
    fi
    if [[ ! -f /usr/include/libnfnetlink/libnfnetlink.h ]]; then
      missing_deps+=("libnfnetlink-dev")
    fi
  fi
  
  # Check for kernel headers
  if [[ ! -d /usr/include/linux ]]; then
    missing_deps+=("linux-libc-dev or linux-headers")
  fi
  
  if [[ ${#missing_deps[@]} -gt 0 ]]; then
    log_warn "Missing system dependencies for netfilterqueue compilation:"
    for dep in "${missing_deps[@]}"; do
      log_warn "  - $dep"
    done
    
    if have_cmd apt-get; then
      log_info "To install on Debian/Ubuntu, run:"
      echo "  sudo apt-get update"
      echo "  sudo apt-get install -y build-essential libnetfilter-queue-dev libnfnetlink-dev linux-libc-dev"
    elif have_cmd dnf; then
      log_info "To install on Fedora/RHEL, run:"
      echo "  sudo dnf install -y gcc make libnetfilter_queue-devel libnfnetlink-devel kernel-headers"
    elif have_cmd pacman; then
      log_info "To install on Arch Linux, run:"
      echo "  sudo pacman -S base-devel libnetfilter_queue libnfnetlink linux-headers"
    fi
    
    return 1
  fi
  return 0
}

print_usage_warning() {
  echo ""
  echo "=============================================================="
  echo " StormShadow: Educational and authorized testing only"
  echo "=============================================================="
  echo "This toolkit can generate high-rate SIP traffic and spoof UDP"
  echo "source addresses. Use ONLY on systems/networks you own or have"
  echo "explicit, written permission to test. Unauthorized use may be"
  echo "illegal and disruptive. You are responsible for compliance with"
  echo "laws, policies, and provider terms. Prefer the built-in lab and"
  echo "dry-run and keep rates conservative."
  echo "=============================================================="
  echo ""
}

install_python_deps() {
  local force_no_uv="${FORCE_NO_UV:-0}"
  local force_use_uv="${FORCE_USE_UV:-0}"

  # Check if netfilterqueue dependencies are available
  local can_compile_netfilterqueue=1
  if ! check_netfilterqueue_deps; then
    can_compile_netfilterqueue=0
    log_warn "netfilterqueue compilation will likely fail due to missing system dependencies"
    
    if [[ -t 0 ]]; then  # Interactive terminal
      if prompt_yes_no "Continue anyway? Some features may not work. [y/N] " "default_no"; then
        log_info "Continuing with installation (netfilterqueue will be skipped on failure)"
      else
        log_error "Installation cancelled. Please install the required system packages first."
        return 1
      fi
    else
      log_info "Non-interactive mode: continuing with installation (netfilterqueue will be skipped on failure)"
    fi
  fi

  # Default: quick path with pip+venv; only use uv when explicitly requested
  if [[ "$force_use_uv" == "1" ]]; then
    # try to install uv if missing
    if ! have_cmd uv; then
      install_uv || log_warn "uv not installed; falling back to pip/venv"
    fi
  fi

  if [[ "$force_use_uv" == "1" && "$(have_cmd uv && echo yes || echo no)" == "yes" ]]; then
    log_info "Installing Python deps with uv (creating .venv with system site packages)"
    # Ensure a project venv exists
    uv venv --system-site-packages "$ROOT_DIR/.venv"
    if [[ -f "$PYPROJECT_FILE" ]]; then
      uv sync
    elif [[ -f "$REQUIREMENTS_FILE" ]]; then
      if [[ $can_compile_netfilterqueue -eq 0 ]]; then
        # Install packages one by one, skipping netfilterqueue if it fails
        install_requirements_separately_uv
      else
        uv pip install -r "$REQUIREMENTS_FILE"
      fi
    else
      log_warn "No pyproject.toml or requirements.txt found; skipping Python deps"
    fi
  else
    log_info "Installing Python deps with pip/venv (alternative)"
    if [[ -f "$REQUIREMENTS_FILE" || -f "$PYPROJECT_FILE" ]]; then
      # Create venv if it doesn't exist
      if [[ ! -d "$ROOT_DIR/.venv" ]]; then
        log_info "Creating virtual environment at $ROOT_DIR/.venv (with system site packages)"
        python3 -m venv --system-site-packages "$ROOT_DIR/.venv" || {
          log_error "Failed to create virtual environment"
          return 1
        }
      fi
      
      # Verify venv was created successfully
      if [[ ! -f "$ROOT_DIR/.venv/bin/activate" ]]; then
        log_error "Virtual environment creation failed - activate script not found"
        return 1
      fi
      
      # Activate venv and install dependencies
      # shellcheck disable=SC1091
      source "$ROOT_DIR/.venv/bin/activate"
      python3 -m pip install --upgrade pip
      if [[ -f "$REQUIREMENTS_FILE" ]]; then
        if [[ $can_compile_netfilterqueue -eq 0 ]]; then
          # Install packages one by one, skipping netfilterqueue if it fails
          install_requirements_separately_pip
        else
          python3 -m pip install -r "$REQUIREMENTS_FILE"
        fi
      elif [[ -f "$PYPROJECT_FILE" ]]; then
        log_warn "pyproject.toml found, but this is not a buildable Python project. Skipping pip install .; using requirements.txt only."
      fi
    else
      log_warn "No dependency manifest found; skipping Python deps"
    fi
  fi
}

install_requirements_separately_pip() {
  # Install each package individually, continuing on failures
  local failed_packages=()
  
  while IFS= read -r line; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    
    local package_spec="$line"
    local package_name="${line%%[><=!]*}"  # Extract package name before version specifiers
    
    log_info "Installing: $package_spec"
    if python3 -m pip install "$package_spec"; then
      log_info "✓ Successfully installed: $package_name"
    else
      log_warn "✗ Failed to install: $package_name"
      failed_packages+=("$package_name")
      
      # Special handling for netfilterqueue
      if [[ "$package_name" =~ netfilterqueue ]]; then
        log_warn "netfilterqueue failed to install - IP spoofing features will not be available"
        log_warn "This is expected if system dependencies are missing"
      fi
    fi
  done < "$REQUIREMENTS_FILE"
  
  if [[ ${#failed_packages[@]} -gt 0 ]]; then
    log_warn "The following packages failed to install:"
    printf '  - %s\n' "${failed_packages[@]}"
    log_warn "Some features may not work. Consider installing missing system dependencies."
  fi
}

install_requirements_separately_uv() {
  # Install each package individually with uv, continuing on failures
  local failed_packages=()
  
  while IFS= read -r line; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    
    local package_spec="$line"
    local package_name="${line%%[><=!]*}"  # Extract package name before version specifiers
    
    log_info "Installing with uv: $package_spec"
    if uv pip install "$package_spec"; then
      log_info "✓ Successfully installed: $package_name"
    else
      log_warn "✗ Failed to install: $package_name"
      failed_packages+=("$package_name")
      
      # Special handling for netfilterqueue
      if [[ "$package_name" =~ netfilterqueue ]]; then
        log_warn "netfilterqueue failed to install - IP spoofing features will not be available"
        log_warn "This is expected if system dependencies are missing"
      fi
    fi
  done < "$REQUIREMENTS_FILE"
  
  if [[ ${#failed_packages[@]} -gt 0 ]]; then
    log_warn "The following packages failed to install:"
    printf '  - %s\n' "${failed_packages[@]}"
    log_warn "Some features may not work. Consider installing missing system dependencies."
  fi
}

attempt_pkg_install_inviteflood() {
  # Best-effort: try common package managers. Package name may vary by distro.
  # We try 'inviteflood' as-is; if it fails, we just return non-zero.
  if have_cmd apt-get; then
    log_info "Trying apt-get to install inviteflood"
    if sudo -n true 2>/dev/null; then SUDO="sudo -n"; else SUDO="sudo"; fi
    $SUDO apt-get update -y || true
    $SUDO apt-get install -y inviteflood && return 0 || return 1
  elif have_cmd dnf; then
    log_info "Trying dnf to install inviteflood"
    if sudo -n true 2>/dev/null; then SUDO="sudo -n"; else SUDO="sudo"; fi
    $SUDO dnf install -y inviteflood && return 0 || return 1
  elif have_cmd pacman; then
    log_info "Trying pacman to install inviteflood"
    if sudo -n true 2>/dev/null; then SUDO="sudo -n"; else SUDO="sudo"; fi
    $SUDO pacman -Sy --noconfirm inviteflood && return 0 || return 1
  elif have_cmd zypper; then
    log_info "Trying zypper to install inviteflood"
    if sudo -n true 2>/dev/null; then SUDO="sudo -n"; else SUDO="sudo"; fi
    $SUDO zypper --non-interactive install inviteflood && return 0 || return 1
  else
    log_warn "No supported package manager detected for inviteflood"
    return 1
  fi
}

build_from_source_inviteflood() {
  local src_dir="$TOOLS_DIR/inviteflood"
  if [[ ! -d "$src_dir" ]]; then
    log_warn "No source dir at $src_dir to build inviteflood from"
    return 1
  fi

  log_info "Attempting to build inviteflood from $src_dir"
  # Try common build flows in order
  if [[ -f "$src_dir/Makefile" ]]; then
    make -C "$src_dir"
  elif [[ -f "$src_dir/CMakeLists.txt" ]]; then
    cmake -S "$src_dir" -B "$src_dir/build"
    cmake --build "$src_dir/build" --config Release
  elif [[ -x "$src_dir/configure" ]]; then
    (cd "$src_dir" && ./configure && make)
  else
    log_warn "No Makefile/CMakeLists.txt/configure found for inviteflood; cannot build"
    return 1
  fi

  # Find a built binary named exactly 'inviteflood'
  local built
  built="$(find "$src_dir" -maxdepth 3 -type f -name inviteflood -perm -111 2>/dev/null | head -n 1 || true)"
  if [[ -n "$built" ]]; then
    install -m 0755 "$built" "$BIN_DIR/inviteflood"
    log_info "Installed inviteflood to $BIN_DIR/inviteflood"
    return 0
  fi

  log_warn "Build completed but could not locate inviteflood binary"
  return 1
}

ensure_inviteflood() {
  ensure_dirs

  # 1) Already available in PATH
  if have_cmd inviteflood; then
    log_info "inviteflood found in PATH: $(command -v inviteflood)"
    # Symlink into local bin for consistency
    ln -sf "$(command -v inviteflood)" "$BIN_DIR/inviteflood"
    return 0
  fi

  # 2) Local binary at external-tools/inviteflood (file)
  if [[ -f "$TOOLS_DIR/inviteflood" && -x "$TOOLS_DIR/inviteflood" ]]; then
    log_info "Found local inviteflood binary at $TOOLS_DIR/inviteflood"
    install -m 0755 "$TOOLS_DIR/inviteflood" "$BIN_DIR/inviteflood"
    return 0
  fi

  # 3) Optionally attempt package manager install (aggressive mode only)
  if [[ "${WITH_TOOLS_INSTALL:-0}" == "1" ]]; then
    if attempt_pkg_install_inviteflood; then
      if have_cmd inviteflood; then
        ln -sf "$(command -v inviteflood)" "$BIN_DIR/inviteflood"
        return 0
      fi
    fi
  fi

  # 4) Optionally build from source if source dir exists (aggressive mode only)
  if [[ "${WITH_TOOLS_INSTALL:-0}" == "1" ]]; then
    if [[ -d "$TOOLS_DIR/inviteflood" ]]; then
      if build_from_source_inviteflood; then
        return 0
      fi
    fi
  fi

  log_warn "inviteflood could not be set up automatically."
  log_warn "Options:"
  log_warn "  - Place the compiled binary at $TOOLS_DIR/inviteflood and re-run"
  log_warn "  - Put source in $TOOLS_DIR/inviteflood and re-run to build"
  log_warn "  - Install it system-wide so it's in PATH and re-run"
  return 1
}

link_inviteflood_into_venv() {
  local venv_bin="$ROOT_DIR/.venv/bin"
  if [[ -d "$venv_bin" && -x "$BIN_DIR/inviteflood" ]]; then
    ln -sf "$BIN_DIR/inviteflood" "$venv_bin/inviteflood"
    log_info "Linked inviteflood into virtualenv: $venv_bin/inviteflood"
  fi
}

main() {
  local python_only=0
  local tools_only=0
  FORCE_NO_UV=0
  FORCE_USE_UV=0
  WITH_TOOLS_INSTALL=0
  for arg in "$@"; do
    case "$arg" in
      --python-only) python_only=1 ;;
      --tools-only) tools_only=1 ;;
      --no-uv) FORCE_NO_UV=1 ;;
      --use-uv) FORCE_USE_UV=1 ;;
      --with-tools-install) WITH_TOOLS_INSTALL=1 ;;
      -h|--help)
        sed -n '1,60p' "$0"
        exit 0
        ;;
      *)
        log_warn "Unknown arg: $arg"
        ;;
    esac
  done

  # Show safety/usage warning banner
  print_usage_warning

  if [[ $tools_only -eq 0 ]]; then
    install_python_deps
  fi

  if [[ $python_only -eq 0 ]]; then
    ensure_inviteflood || true
  fi

  # Ensure the tool is accessible inside the venv as well
  link_inviteflood_into_venv || true

  log_info "Setup complete."
  if [[ -x "$BIN_DIR/inviteflood" ]]; then
    log_info "inviteflood available at $BIN_DIR/inviteflood"
  else
    log_warn "inviteflood not installed; some attacks may not run until installed."
  fi
}

main "$@"
