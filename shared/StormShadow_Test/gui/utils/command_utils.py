"""
GUI command utilities that properly handle sudo and environment preservation.

This module provides a simple interface for GUI components to run commands
with proper sudo handling using the custom command runner.
"""

import subprocess
from typing import List, Dict, Optional, Any
from utils.core.logs import print_info, print_error, print_warning


def run_gui_command(
    command: List[str],
    *,
    operation_name: str = "operation",
    need_sudo: bool = False,
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None
) -> subprocess.CompletedProcess[str]:
    """
    Run a command from GUI with proper sudo handling and environment preservation.

    This function uses the custom command runner to ensure that:
    - Environment variables (PYTHONPATH, etc.) are preserved
    - Sudo prompts work correctly in GUI context
    - Commands are executed with proper privileges

    Args:
        command: Command to execute as list of strings
        operation_name: Human-readable name for error messages
        need_sudo: Whether this command typically needs sudo
        capture_output: Whether to capture stdout/stderr
        text: Whether to decode output as text
        check: Whether to raise exception on non-zero exit
        cwd: Working directory for command
        env: Environment variables override

    Returns:
        subprocess.CompletedProcess[str]: Result of the command

    Raises:
        subprocess.CalledProcessError: If check=True and command fails
        PermissionError: If sudo is needed but user declines
    """
    try:
        from utils.core.command_runner import run_command

        print_info(f"GUI running {operation_name}: {' '.join(command)}")

        # Use custom command runner with environment preservation
        result = run_command(
            command,
            cwd=cwd,
            env=env,
            want_sudo=need_sudo,
            sudo_preserve_env=True,  # Always preserve environment for GUI commands
            sudo_non_interactive=False,  # Allow password prompts for GUI
            capture_output=capture_output,
            check=check,
            text=text
        )

        return result

    except ImportError as e:
        print_warning(f"Custom command runner not available, falling back to subprocess: {e}")

        # Fallback to standard subprocess with sudo if needed
        if need_sudo:
            # Add sudo with environment preservation
            final_command = ['sudo', '-E'] + command
        else:
            final_command = command

        return subprocess.run(
            final_command,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            check=check,
            text=text
        )

    except Exception as e:
        print_error(f"Failed to run {operation_name}: {e}")
        raise


def run_docker_command(
    docker_args: List[str],
    *,
    operation_name: str = "docker operation",
    **kwargs: Any
) -> subprocess.CompletedProcess[str]:
    """
    Run a docker command with automatic sudo handling.

    Args:
        docker_args: Docker command arguments (without 'docker')
        operation_name: Human-readable name for error messages
        **kwargs: Additional arguments for run_gui_command

    Returns:
        subprocess.CompletedProcess[str]: Result of the command
    """
    command = ['docker'] + docker_args
    return run_gui_command(
        command,
        operation_name=operation_name,
        need_sudo=True,  # Docker typically needs sudo
        **kwargs
    )


def run_iptables_command(
    iptables_args: List[str],
    *,
    operation_name: str = "iptables operation",
    **kwargs: Any
) -> subprocess.CompletedProcess[str]:
    """
    Run an iptables command with automatic sudo handling.

    Args:
        iptables_args: iptables command arguments (without 'iptables')
        operation_name: Human-readable name for error messages
        **kwargs: Additional arguments for run_gui_command

    Returns:
        subprocess.CompletedProcess[str]: Result of the command
    """
    command = ['iptables'] + iptables_args
    return run_gui_command(
        command,
        operation_name=operation_name,
        need_sudo=True,  # iptables always needs sudo
        **kwargs
    )


def check_command_available(command_name: str) -> bool:
    """
    Check if a command is available on the system.

    Args:
        command_name: Name of the command to check

    Returns:
        bool: True if command is available, False otherwise
    """
    try:
        result = run_gui_command(
            ['which', command_name],
            operation_name=f"check {command_name}",
            need_sudo=False,
            check=False,  # Don't raise exception if not found
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False


def get_command_version(command_name: str, version_arg: str = '--version') -> Optional[str]:
    """
    Get version information for a command.

    Args:
        command_name: Name of the command
        version_arg: Argument to get version (default: --version)

    Returns:
        Optional[str]: Version string if successful, None otherwise
    """
    try:
        # For version checks, use subprocess directly to avoid logging
        import subprocess
        
        result = subprocess.run(
            [command_name, version_arg],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            # Return first line of output, stripped
            return result.stdout.strip().split('\n')[0]
        else:
            return None

    except Exception:
        return None


def test_sudo_access() -> bool:
    """
    Test if sudo access is available without prompting for password.

    Returns:
        bool: True if sudo access is available, False otherwise
    """
    try:
        result = run_gui_command(
            ['sudo', '-n', 'true'],
            operation_name="test sudo access",
            need_sudo=False,  # We're calling sudo explicitly
            check=False,
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False
