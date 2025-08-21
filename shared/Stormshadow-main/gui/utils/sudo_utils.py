"""
Sudo utilities for GUI operations that require elevated privileges.

This module provides utilities to detect when operations need sudo privileges
and automatically restart the application with proper permissions.
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Optional, List
from utils.core.logs import print_info, print_error, print_warning


def check_sudo_available() -> bool:
    """Check if sudo is available and configured."""
    try:
        result = subprocess.run(['sudo', '-n', 'true'],
                                capture_output=True,
                                timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_graphical_sudo_available() -> Optional[str]:
    """
    Check which graphical sudo helper is available on the system.

    Returns:
        str: Name of available graphical sudo helper, or None if none found
    """
    graphical_sudo_helpers = [
        'pkexec',      # PolicyKit (most common on modern Linux)
        'gksudo',      # GNOME sudo (older)
        'kdesudo',     # KDE sudo
        'gksu',        # GTK sudo (older)
    ]

    for helper in graphical_sudo_helpers:
        if subprocess.run(['which', helper], capture_output=True).returncode == 0:
            return helper

    return None


def is_running_as_root() -> bool:
    """Check if the current process is running with root privileges."""
    return os.geteuid() == 0


def check_command_needs_sudo(command: List[str]) -> bool:
    """
    Check if a command typically requires sudo privileges.

    Args:
        command: List of command arguments

    Returns:
        bool: True if command likely needs sudo
    """
    sudo_commands = {
        'iptables', 'ip6tables', 'docker', 'inviteflood',
        'netfilterqueue', 'tcpdump', 'nmap'
    }

    if not command:
        return False

    cmd_name = Path(command[0]).name
    return cmd_name in sudo_commands


def request_sudo_restart() -> bool:
    """
    Ask user if they want to restart the application with sudo privileges.

    Returns:
        bool: True if user agreed to restart with sudo
    """
    try:
        # Create a simple dialog
        root = tk.Tk()
        root.withdraw()  # Hide the main window

        message = (
            "StormShadow GUI requires administrator privileges for network operations.\n\n"
            "This includes:\n"
            "• iptables configuration for packet spoofing\n"
            "• Docker container management for lab mode\n"
            "• Network interface operations\n\n"
            "Would you like to restart with administrator privileges?"
        )

        result = messagebox.askyesno(
            "Administrator Privileges Required",
            message,
            icon='warning'
        )

        root.destroy()
        return result

    except Exception as e:
        print_error(f"Failed to show sudo dialog: {e}")
        return False


def restart_with_sudo(open_new_terminal: bool = False) -> None:
    """Restart the current application with sudo privileges using custom command runner."""
    try:
        from utils.core.command_runner import run_python

        # Get the current script path
        script_path = os.path.abspath(sys.argv[0])

        print_info("Restarting with sudo using custom command runner...")
        print_info(f"Script path: {script_path}")
        print_info(f"Arguments: {sys.argv[1:]}")

        if open_new_terminal:
            print_info("Opening new terminal for sudo restart...")
            # Use our custom command runner which properly preserves environment
            # This will handle sudo with environment preservation automatically
            run_python(
                script=script_path,
                args=sys.argv[1:],  # Pass all original arguments
                want_sudo=True,
                sudo_preserve_env=True,  # This preserves PYTHONPATH and other env vars
                sudo_non_interactive=False,  # Allow interactive password prompt
                new_terminal=True  # Launch in new terminal to avoid blocking current GUI
            )

            print_info(
                "Started new instance with sudo in new terminal, "
                "exiting current instance..."
            )
            # Exit the current process since we started a new one with sudo
            sys.exit(0)
        else:
            print_info("Restarting with sudo in same terminal...")
            # Get the current Python executable path
            python_executable = sys.executable

            # Use standard sudo with environment preservation in same terminal
            sudo_command = [
                'sudo', '-E',  # Preserve environment
                python_executable,
                script_path
            ] + sys.argv[1:]

            print_info(f"Executing: {' '.join(sudo_command)}")
            # Replace current process with sudo version
            os.execvp('sudo', sudo_command)

    except Exception as e:
        print_error(f"Failed to restart with sudo using command runner: {e}")

        # Fallback to original method if command runner fails
        try:
            print_info("Falling back to standard sudo method...")

            # Get the current Python executable path
            python_executable = sys.executable
            script_path = os.path.abspath(sys.argv[0])

            # Use standard sudo with environment preservation
            sudo_command = [
                'sudo', '-E',  # Preserve environment
                python_executable,
                script_path
            ] + sys.argv[1:]

            print_info(f"Fallback command: {' '.join(sudo_command)}")
            os.execvp('sudo', sudo_command)

        except Exception as fallback_e:
            print_error(f"Fallback method also failed: {fallback_e}")
            sys.exit(1)


def handle_permission_error(
        operation_name: str,
        auto_restart: bool = True,
        open_new_terminal: bool = False) -> bool:
    """
    Handle permission errors by optionally restarting with sudo.

    Args:
        operation_name: Name of the operation that failed
        auto_restart: If True, automatically restart with sudo after user confirmation
        open_new_terminal: If True, open new terminal for sudo; if False, use same terminal

    Returns:
        bool: True if restarting with sudo, False otherwise
    """
    print_warning(f"Permission denied for operation: {operation_name}")

    if is_running_as_root():
        print_error("Already running as root, but still getting permission errors")
        return False

    if not auto_restart:
        print_info("Auto-restart disabled, user must manually restart with sudo")
        return False

    # Check if we can use sudo
    if not check_sudo_available():
        print_error("Sudo not available or not configured properly")
        messagebox.showerror(
            "Permission Error",
            f"Operation '{operation_name}' requires administrator privileges, "
            "but sudo is not available.\n\n"
            "Please run the application manually with: sudo python main.py --gui"
        )
        return False

    # Ask user for permission to restart
    if request_sudo_restart():
        print_info("User agreed to restart with sudo privileges")
        restart_with_sudo(open_new_terminal)
        return True  # This won't actually return as process is replaced
    else:
        print_info("User declined to restart with sudo privileges")
        messagebox.showwarning(
            "Limited Functionality",
            f"Operation '{operation_name}' was cancelled.\n\n"
            "Some features may not work without administrator privileges.\n"
            "To enable full functionality, restart with: sudo python main.py --gui"
        )
        return False


def run_command_with_graphical_sudo(
        command: List[str],
        operation_name: str = "network operation") -> subprocess.CompletedProcess[str]:
    """
    Run a single command with sudo using the custom command runner.

    Args:
        command: Command to execute
        operation_name: Human-readable name of the operation

    Returns:
        subprocess.CompletedProcess[str]: Result of the command
    """
    try:
        from utils.core.command_runner import run_command

        # First try without sudo if command doesn't typically need it
        if not check_command_needs_sudo(command):
            print_info(f"Running command without sudo: {' '.join(command)}")
            return run_command(command, capture_output=True, check=True, text=True)

        # Use our custom command runner with sudo
        print_info(f"Running command with sudo (preserving environment): {' '.join(command)}")

        # First try non-interactive sudo
        try:
            result = run_command(
                command,
                want_sudo=True,
                sudo_non_interactive=True,  # Try non-interactive first
                sudo_preserve_env=True,     # Preserve environment
                capture_output=True,
                check=True,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            # If non-interactive failed, try interactive sudo
            if "password is required" in str(e) or "authentication is required" in str(
                    e).lower() or e.returncode == 1:
                print_info("Non-interactive sudo failed, trying interactive...")
                result = run_command(
                    command,
                    want_sudo=True,
                    sudo_non_interactive=False,  # Allow password prompt
                    sudo_preserve_env=True,      # Preserve environment
                    capture_output=True,
                    check=True,
                    text=True
                )
                return result
            else:
                raise

    except ImportError as e:
        print_error(f"Could not import custom command runner: {e}")
        # Fallback to standard subprocess with sudo
        if check_command_needs_sudo(command):
            sudo_command = ['sudo', '-E'] + command  # -E preserves environment
            return subprocess.run(sudo_command, capture_output=True, check=True, text=True)
        else:
            return subprocess.run(command, capture_output=True, check=True, text=True)
    except Exception as e:
        print_error(f"Unexpected error running command: {e}")
        raise


def run_with_sudo_check(
        command: List[str],
        operation_name: str = "network operation") -> subprocess.CompletedProcess[str]:
    """
    Run a command with automatic sudo privilege checking using custom command runner.

    Args:
        command: Command to execute
        operation_name: Human-readable name of the operation

    Returns:
        subprocess.CompletedProcess[str]: Result of the command

    Raises:
        PermissionError: If command requires sudo but user declined restart
    """
    try:
        # Use the custom command runner approach
        return run_command_with_graphical_sudo(command, operation_name)

    except subprocess.CalledProcessError as e:
        # If command failed due to permissions, try the restart approach
        if "permission denied" in str(e).lower() or "not authorized" in str(e).lower():
            if not is_running_as_root():
                if handle_permission_error(operation_name):
                    # This will restart the process, so we shouldn't reach here
                    pass
                else:
                    # User declined, raise permission error
                    raise PermissionError(f"Sudo required for {operation_name}, but user declined")
        # Re-raise the original error if it's not permission-related
        raise


def create_sudo_launcher_script() -> Optional[Path]:
    """
    Create a launcher script that automatically runs the GUI with sudo.

    Returns:
        Path: Path to the created launcher script, or None if failed
    """
    try:
        launcher_content = f"""#!/bin/bash
# StormShadow GUI Launcher with Sudo
# Auto-generated launcher script

cd "{os.getcwd()}"
sudo {sys.executable} {os.path.abspath(sys.argv[0])} --gui "$@"
"""

        launcher_path = Path.cwd() / "launch_gui_sudo.sh"

        with open(launcher_path, 'w') as f:
            f.write(launcher_content)

        # Make executable
        os.chmod(launcher_path, 0o755)

        print_info(f"Created sudo launcher script: {launcher_path}")
        return launcher_path

    except Exception as e:
        print_error(f"Failed to create launcher script: {e}")
        return None
