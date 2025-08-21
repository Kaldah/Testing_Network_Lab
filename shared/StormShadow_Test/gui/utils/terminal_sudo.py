"""
Terminal-based sudo utilities for GUI operations.

This module provides utilities to run sudo commands in a terminal window
when the GUI needs to execute privileged operations.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List
from utils.core.logs import print_info, print_error


def create_sudo_script(commands: List[str], description: str = "StormShadow Operation") -> Path:
    """
    Create a temporary script that runs multiple sudo commands.

    Args:
        commands: List of shell commands that need sudo
        description: Description of what the script does

    Returns:
        Path: Path to the created script
    """
    script_content = f"""#!/bin/bash
# {description}
# Auto-generated sudo script for StormShadow GUI

echo "==================================================="
echo "StormShadow: {description}"
echo "==================================================="
echo "The following commands will be executed with sudo:"
echo

"""

    # Add each command with echo for visibility
    for i, cmd in enumerate(commands, 1):
        script_content += f'echo "  {i}. {cmd}"\n'

    script_content += """
echo
echo "Press Enter to continue, or Ctrl+C to cancel..."
read -r

echo "Executing commands..."
echo

"""

    # Add the actual commands
    for i, cmd in enumerate(commands, 1):
        script_content += f"""echo ">>> Executing: {cmd}"
if sudo {cmd}; then
    echo "✓ Command {i} completed successfully"
else
    echo "✗ Command {i} failed with exit code $?"
    echo "Do you want to continue? (y/N)"
    read -r continue_choice
    if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
        echo "Aborting remaining commands."
        exit 1
    fi
fi
echo

"""

    script_content += """echo "All commands completed!"
echo "Press Enter to close this window..."
read -r
"""

    # Create temporary script file
    script_fd, script_path = tempfile.mkstemp(suffix='.sh', prefix='stormshadow_sudo_')
    script_path_obj = Path(script_path)

    try:
        with os.fdopen(script_fd, 'w') as f:
            f.write(script_content)

        # Make executable
        os.chmod(script_path, 0o755)
        return script_path_obj

    except Exception as e:
        os.close(script_fd)
        script_path_obj.unlink(missing_ok=True)
        raise e


def run_sudo_commands_in_terminal(commands: List[str],
                                  description: str = "StormShadow Operation",
                                  wait: bool = False) -> subprocess.Popen[bytes]:
    """
    Run sudo commands in a new terminal window.

    Args:
        commands: List of shell commands that need sudo
        description: Description of what the operation does
        wait: If True, wait for the terminal to close

    Returns:
        subprocess.Popen: The terminal process
    """
    try:
        # Create the sudo script
        script_path = create_sudo_script(commands, description)

        print_info(f"Created sudo script: {script_path}")
        print_info(f"Opening terminal for: {description}")

        # Run the script in a new terminal
        terminal_cmd = [
            'gnome-terminal',
            '--title', f'StormShadow: {description}',
            '--',
            'bash', str(script_path)
        ]

        process = subprocess.Popen(terminal_cmd,
                                   start_new_session=True,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)

        if wait:
            process.wait()
            # Clean up the script after completion
            script_path.unlink(missing_ok=True)
        else:
            # Schedule cleanup (best effort)
            def cleanup_later():
                try:
                    process.wait()
                    script_path.unlink(missing_ok=True)
                except BaseException:
                    pass

            import threading
            cleanup_thread = threading.Thread(target=cleanup_later, daemon=True)
            cleanup_thread.start()

        return process

    except Exception as e:
        print_error(f"Failed to run sudo commands in terminal: {e}")
        raise


def run_docker_lab_in_terminal(docker_command: str,
                               container_name: str = "sip-victim") -> subprocess.Popen[bytes]:
    """
    Run Docker lab commands in a dedicated terminal window.

    Args:
        docker_command: The docker command to run
        container_name: Name of the container for the terminal title

    Returns:
        subprocess.Popen: The terminal process
    """
    commands = [
        f'echo "Starting Docker container: {container_name}"',
        f'echo "Command: {docker_command}"',
        'echo "Press Ctrl+C to stop the container"',
        'echo',
        docker_command
    ]

    return run_sudo_commands_in_terminal(
        commands,
        f"Docker Lab - {container_name}",
        wait=False
    )


def check_terminal_available() -> bool:
    """Check if gnome-terminal is available."""
    try:
        result = subprocess.run(['which', 'gnome-terminal'],
                                capture_output=True,
                                timeout=5)
        return result.returncode == 0
    except BaseException:
        return False
