"""
GUI-specific lab operations that handle sudo requirements gracefully.

This module provides a wrapper around the lab manager that can handle
sudo requirements in a user-friendly way for GUI operations.
"""

import subprocess
import tkinter as tk
from tkinter import messagebox
import threading
import time
from typing import Optional, Callable

from utils.lab_manager import LabManager
from utils.config.config import Config
from utils.core.logs import print_info, print_error, print_warning, print_success


class GUILabManager:
    """
    GUI-friendly wrapper for lab manager operations.

    This class handles sudo requirements and provides user feedback
    for lab operations in the GUI context.
    """

    def __init__(self, config: Config):
        """
        Initialize GUI lab manager.

        Args:
            config: Lab configuration
        """
        self.config = config
        self.lab_manager: Optional[LabManager] = None
        self.status_callback: Optional[Callable[[str], None]] = None
        self._is_starting = False
        self._is_stopping = False

    def set_status_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """Set callback function for status updates."""
        self.status_callback = callback

    def _update_status(self, message: str):
        """Update status via callback if available."""
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                print_error(f"Error in status callback: {e}")

    def _show_sudo_error_dialog(self, operation: str, error_message: str) -> bool:
        """
        Show dialog for sudo-related errors with helpful suggestions.

        Args:
            operation: Name of the operation that failed
            error_message: The error message

        Returns:
            bool: True if user wants to try alternative approach
        """
        try:
            root = tk.Tk()
            root.withdraw()

            message = (
                f"Lab operation '{operation}' requires administrator privileges.\n\n"
                f"Error: {error_message}\n\n"
                "Suggestions:\n"
                "1. Open a terminal and run: sudo docker --version\n"
                "   (This will cache your sudo credentials)\n"
                "2. Then try the lab operation again\n\n"
                "Alternative:\n"
                "• Close this GUI\n"
                "• Run: sudo python main.py --gui\n"
                "• This will start the GUI with admin privileges\n\n"
                "Would you like to open a terminal for manual Docker commands?"
            )

            result = messagebox.askyesnocancel(
                "Administrator Privileges Required",
                message,
                icon='warning'
            )

            root.destroy()

            if result is True:  # Yes - open terminal
                self._open_docker_terminal()
                return True
            elif result is False:  # No - continue without action
                return False
            else:  # Cancel - user cancelled
                return False

        except Exception as e:
            print_error(f"Failed to show sudo error dialog: {e}")
            return False

    def _open_docker_terminal(self):
        """Open a terminal with helpful Docker commands."""
        try:
            terminal_commands = [
                'echo "StormShadow Lab - Manual Docker Commands"',
                'echo "========================================"',
                'echo',
                'echo "First, verify Docker is working:"',
                'echo "  sudo docker --version"',
                'echo',
                'echo "List existing containers:"',
                'echo "  sudo docker ps -a"',
                'echo',
                'echo "Remove existing SIP container if needed:"',
                'echo "  sudo docker rm -f sip-victim"',
                'echo',
                'echo "Build the SIP server image:"',
                'echo "  cd sip-lab/sip_server"',
                'echo "  sudo docker build -t asterisk-sip-server ."',
                'echo',
                'echo "Run the SIP lab container:"',
                ('echo "  sudo docker run --rm -it --network host '
                 '--cap-add=NET_ADMIN --cap-add=NET_RAW '
                 '-e SPOOFED_SUBNET=10.10.123.0/25 -e RETURN_ADDR=10.135.97.2 '
                 '--name sip-victim asterisk-sip-server"'),
                'echo',
                'echo "Press Enter to continue..."',
                'read']

            # Create a script to run in terminal
            script_content = '#!/bin/bash\n' + '\n'.join(terminal_commands)

            import tempfile
            import os

            script_fd, script_path = tempfile.mkstemp(suffix='.sh', prefix='stormshadow_lab_')

            try:
                with os.fdopen(script_fd, 'w') as f:
                    f.write(script_content)

                os.chmod(script_path, 0o755)

                # Open in terminal
                subprocess.Popen([
                    'gnome-terminal',
                    '--title', 'StormShadow Lab - Manual Commands',
                    '--', 'bash', script_path
                ], start_new_session=True)

                print_info("Opened terminal with manual Docker commands")

            except Exception as e:
                print_error(f"Failed to create terminal script: {e}")
                os.close(script_fd)

        except Exception as e:
            print_error(f"Failed to open Docker terminal: {e}")

    def start_lab(self) -> bool:
        """
        Start the lab environment with GUI-friendly error handling.

        Returns:
            bool: True if started successfully
        """
        if self._is_starting:
            print_warning("Lab is already starting")
            return False

        if self.is_running():
            print_info("Lab is already running")
            return True

        self._is_starting = True
        self._update_status("Starting lab...")

        try:
            # Create lab manager with GUI mode enabled
            self.lab_manager = LabManager(self.config, gui_mode=True, dry_run=False)

            # Start in a separate thread to avoid blocking the GUI
            def start_thread():
                try:
                    print_info("Starting lab manager from GUI...")
                    if self.lab_manager:
                        self.lab_manager.start()
                        # Verify it actually started
                        time.sleep(1)  # Give it a moment to start
                        if self.is_running():
                            self._update_status("Lab started successfully")
                            print_success("Lab started successfully")
                        else:
                            error_msg = "Lab container failed to start properly"
                            print_error(error_msg)
                            self._update_status(error_msg)
                            self.lab_manager = None
                    else:
                        raise Exception("Lab manager not initialized")
                except subprocess.CalledProcessError as e:
                    error_msg = f"Command failed: {e}"
                    if "sudo" in str(e) and ("password" in str(e) or "authentication" in str(e)):
                        print_error(f"Sudo error starting lab: {error_msg}")
                        self._show_sudo_error_dialog("Lab Start", error_msg)
                        self._update_status("Lab start failed - sudo required")
                    else:
                        print_error(f"Failed to start lab: {error_msg}")
                        self._update_status(f"Lab start failed: {error_msg}")
                    self.lab_manager = None
                except Exception as e:
                    error_msg = str(e)
                    print_error(f"Failed to start lab: {error_msg}")

                    # More specific error handling
                    if "sudo" in error_msg.lower() or "permission" in error_msg.lower():
                        self._show_sudo_error_dialog("Lab Start", error_msg)
                        self._update_status("Lab start failed - permissions required")
                    elif "container did not start" in error_msg.lower():
                        self._update_status("Lab start failed - container startup timeout")
                        print_error("Container startup failed. Check Docker daemon and image.")
                    elif "connection is closed" in error_msg.lower():
                        self._update_status("Lab start failed - terminal connection error")
                        print_error(
                            "Terminal connection failed. Container may be starting in background.")
                    else:
                        self._update_status(f"Lab start failed: {error_msg}")
                    self.lab_manager = None
                finally:
                    self._is_starting = False

            thread = threading.Thread(target=start_thread, daemon=True)
            thread.start()
            return True

        except Exception as e:
            self._is_starting = False
            error_msg = str(e)
            print_error(f"Failed to initialize lab: {error_msg}")
            self._update_status(f"Lab initialization failed: {error_msg}")
            return False

    def stop_lab(self) -> bool:
        """
        Stop the lab environment.

        Returns:
            bool: True if stopped successfully
        """
        if self._is_stopping:
            print_warning("Lab is already stopping")
            return False

        if not self.lab_manager:
            print_info("Lab is not running")
            return True

        self._is_stopping = True
        self._update_status("Stopping lab...")

        try:
            def stop_thread():
                try:
                    if self.lab_manager:
                        print_info("Stopping lab manager...")
                        self.lab_manager.stop()
                        # Verify it actually stopped
                        time.sleep(1)  # Give it a moment to stop
                        if not self.is_running():
                            self.lab_manager = None
                            self._update_status("Lab stopped")
                            print_success("Lab stopped successfully")
                        else:
                            print_warning("Lab may still be running after stop command")
                            self._update_status("Lab stop may have failed")
                    else:
                        self._update_status("Lab was not running")
                        print_info("Lab manager was not initialized")
                except Exception as e:
                    print_error(f"Failed to stop lab: {e}")
                    self._update_status(f"Lab stop failed: {e}")
                finally:
                    self._is_stopping = False

            thread = threading.Thread(target=stop_thread, daemon=True)
            thread.start()
            return True

        except Exception as e:
            self._is_stopping = False
            print_error(f"Failed to stop lab: {e}")
            self._update_status(f"Lab stop failed: {e}")
            return False

    def restart_lab(self) -> bool:
        """
        Restart the lab environment.

        Returns:
            bool: True if restarted successfully
        """
        self._update_status("Restarting lab...")

        # Stop first
        if not self.stop_lab():
            return False

        # Wait a moment
        time.sleep(2)

        # Start again
        return self.start_lab()

    def get_status(self) -> str:
        """
        Get current lab status.

        Returns:
            str: Current status
        """
        if self._is_starting:
            return "Starting..."
        elif self._is_stopping:
            return "Stopping..."
        elif not self.lab_manager:
            return "Stopped"
        else:
            try:
                status = self.lab_manager.status()
                if status and status.startswith("Up"):
                    return "Running"
                elif status == "Unknown" or not status:
                    return "Error"
                else:
                    return "Stopped"
            except Exception as e:
                return f"Error: {e}"

    def is_running(self) -> bool:
        """
        Check if lab is currently running.

        Returns:
            bool: True if running
        """
        if not self.lab_manager:
            return False

        try:
            status = self.lab_manager.status()
            return status.startswith("Up") and status != "Unknown"
        except BaseException:
            return False
