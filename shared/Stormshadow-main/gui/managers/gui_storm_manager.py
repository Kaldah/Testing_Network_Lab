"""
GUI Storm Manager

This module manages StormShadow instances for the GUI application,
providing a clean interface between the GUI and the core StormShadow functionality.
"""

import threading
from pathlib import Path
from typing import Dict, Optional, Callable
from dataclasses import dataclass
import subprocess

from utils.config.config import Parameters
from utils.core.stormshadow import StormShadow
from utils.core.logs import print_info, print_error, print_debug, print_success, print_warning
from utils.attack.attack_modules_finder import find_attack_modules
from utils.network.iptables import generate_suid


@dataclass
class StormShadowInstance:
    """Represents a managed StormShadow instance."""
    name: str
    instance: StormShadow
    thread: Optional[threading.Thread] = None
    is_running: bool = False
    instance_type: str = "unknown"  # "lab", "attack", "both"


class GUIStormManager:
    """
    Manages StormShadow instances for the GUI application.

    This manager provides:
    - Creation and management of StormShadow instances
    - Thread management for non-blocking operations
    - Status tracking and monitoring
    - Configuration management for GUI operations
    - Shared SUID across all instances for proper cleanup
    """

    def __init__(self, preserve_existing_rules: bool = False):
        """Initialize the GUI storm manager."""
        print_debug("Initializing GUI Storm Manager...")

        self.instances: Dict[str, StormShadowInstance] = {}
        self.available_attacks: Dict[str, Path] = {}
        self.status_callbacks: Dict[str, Callable[[str, str], None]] = {}

        # Generate a single shared SUID for all instances in this GUI session
        self.shared_suid = generate_suid()
        print_debug(f"GUI session SUID: {self.shared_suid}")

        # Store preservation setting for existing rules
        self.preserve_existing_rules = preserve_existing_rules

        # Discover available attack modules
        self._discover_attacks()

    def discover_attacks(self) -> Dict[str, Path]:
        """Public wrapper to (re)discover and return available attack modules.

        This avoids exposing protected members to external callers.
        """
        # Re-run discovery to refresh the cached list and return a copy
        self._discover_attacks()
        return self.get_available_attacks()

        print_success("GUI Storm Manager initialized")

    def _discover_attacks(self):
        """Discover available attack modules."""
        print_debug("Discovering available attack modules...")
        try:
            # Use absolute path relative to the project root
            from utils.core.system_utils import get_project_root
            project_root = get_project_root()
            attack_modules_path = project_root / "sip_attacks"
            self.available_attacks = find_attack_modules(attack_modules_path)
            print_info(
                f"Found {len(self.available_attacks)} attack modules: "
                f"{list(self.available_attacks.keys())}")
        except Exception as e:
            print_error(f"Failed to discover attack modules: {e}")
            self.available_attacks = {}

    def get_shared_suid(self) -> str:
        """Get the shared SUID for this GUI session."""
        return self.shared_suid

    def get_available_attacks(self) -> Dict[str, Path]:
        """Get the list of available attack modules."""
        return self.available_attacks.copy()

    def create_attack_instance(self, attack_name: str, config_params: Parameters) -> bool:
        """
        Create a new StormShadow instance configured for attack mode.

        Args:
            attack_name: Name of the attack to configure
            config_params: Additional configuration parameters

        Returns:
            bool: True if instance was created successfully
        """
        instance_name = f"attack_{attack_name}"

        # If instance already exists, remove it first
        if instance_name in self.instances:
            print_debug(f"Instance {instance_name} already exists, removing it first")
            self.stop_instance(instance_name)
            self.remove_instance(instance_name)

        try:
            # Get default IP address
            from utils.core.system_utils import get_default_ip
            default_ip = get_default_ip()

            # Create parameters for attack mode
            attack_params = Parameters({
                "mode": "attack",
                "attack_name": attack_name,
                "attack": True,
                "lab": False,
                "gui": True,
                "open_window": config_params.get("open_window", False),  # Don't force open_window for GUI
                "spoofing_enabled": config_params.get("spoofing_enabled", True),
                "return_path_enabled": config_params.get("return_path_enabled", True),
                "target_ip": config_params.get("target_ip", default_ip),
                "target_port": config_params.get("target_port", 5060),
                "max_count": config_params.get("max_count", 100),
                "dry_run": config_params.get("dry_run", False)
            })

            # Merge with additional parameters
            for key, value in config_params.items():
                if key not in attack_params:
                    attack_params[key] = value
            
            # Convert delay_ms (milliseconds) to delay (seconds) for attack modules
            if "delay_ms" in attack_params:
                delay_ms = attack_params.get("delay_ms", 0)
                if isinstance(delay_ms, (int, float)) and delay_ms > 0:
                    attack_params["delay"] = delay_ms / 1000.0  # Convert ms to seconds
                    print_debug(f"Converted delay_ms {delay_ms}ms to delay {attack_params['delay']}s")
                # Remove delay_ms since attack modules don't use it
                del attack_params["delay_ms"]

            # Create StormShadow instance with shared SUID
            storm_instance = StormShadow(
                CLI_Args=attack_params,
                session_uid=self.shared_suid,
                preserve_existing_rules=self.preserve_existing_rules
            )
            storm_instance.setup()

            # Create managed instance
            managed_instance = StormShadowInstance(
                name=instance_name,
                instance=storm_instance,
                instance_type="attack"
            )

            self.instances[instance_name] = managed_instance
            print_success(f"Created attack instance: {instance_name}")
            return True

        except Exception as e:
            print_error(f"Failed to create attack instance {instance_name}: {e}")
            return False

    def create_lab_instance(self, config_params: Optional[Parameters] = None) -> bool:
        """
        Create a new StormShadow instance configured for lab mode.

        Args:
            config_params: Optional configuration parameters

        Returns:
            bool: True if instance was created successfully
        """
        instance_name = "lab_manager"

        # If instance already exists, remove it first
        if instance_name in self.instances:
            print_debug(f"Instance {instance_name} already exists, removing it first")
            self.stop_instance(instance_name)
            self.remove_instance(instance_name)

        try:
            # Create parameters for lab mode
            lab_params = Parameters({
                "mode": "lab",
                "attack": False,
                "lab": True,
                "gui": True
            })

            # Merge with additional parameters
            if config_params:
                for key, value in config_params.items():
                    lab_params[key] = value

            # Create StormShadow instance with shared SUID
            storm_instance = StormShadow(
                CLI_Args=lab_params,
                session_uid=self.shared_suid,
                preserve_existing_rules=self.preserve_existing_rules
            )
            storm_instance.setup()

            # Create managed instance
            managed_instance = StormShadowInstance(
                name=instance_name,
                instance=storm_instance,
                instance_type="lab"
            )

            self.instances[instance_name] = managed_instance
            print_success(f"Created lab instance: {instance_name}")
            return True

        except Exception as e:
            print_error(f"Failed to create lab instance {instance_name}: {e}")
            return False

    def start_instance(self, instance_name: str) -> bool:
        """
        Start a StormShadow instance in a separate thread.

        Args:
            instance_name: Name of the instance to start

        Returns:
            bool: True if started successfully
        """
        if instance_name not in self.instances:
            print_error(f"Instance {instance_name} not found")
            return False

        instance = self.instances[instance_name]

        if instance.is_running:
            print_error(f"Instance {instance_name} is already running")
            return False

        try:
            def run_instance():
                completed_naturally = False
                try:
                    print_info(f"Starting instance {instance_name}...")
                    instance.is_running = True
                    self._notify_status_change(instance_name, "starting")

                    # Run the StormShadow instance
                    instance.instance.run()

                    # Attack completed - ensure spoofer cleanup
                    print_info(f"Attack {instance_name} completed, cleaning up spoofer...")
                    self._cleanup_spoofer_processes()
                    
                    completed_naturally = True  # Mark as natural completion
                    self._notify_status_change(instance_name, "completed")
                    print_success(f"Instance {instance_name} completed successfully")

                except subprocess.CalledProcessError as e:
                    # Handle sudo permission errors specifically
                    if "password is required" in str(e) or e.returncode == 1:
                        print_error(f"Permission error running instance {instance_name}: {e}")
                        self._notify_status_change(instance_name, "permission_error")

                        # Try to handle permission error
                        try:
                            from gui.utils.sudo_utils import handle_permission_error
                            operation_name = f"running {instance_name}"
                            handle_permission_error(operation_name, auto_restart=True)
                        except ImportError:
                            print_error("Could not import sudo utilities")
                    else:
                        print_error(f"Command error running instance {instance_name}: {e}")
                        self._notify_status_change(instance_name, "error")

                except Exception as e:
                    print_error(f"Error running instance {instance_name}: {e}")
                    self._notify_status_change(instance_name, "error")
                finally:
                    instance.is_running = False
                    # Only send "stopped" if it wasn't a natural completion
                    if not completed_naturally:
                        self._notify_status_change(instance_name, "stopped")

            # Create and start thread
            instance.thread = threading.Thread(target=run_instance, daemon=True)
            instance.thread.start()

            return True

        except Exception as e:
            print_error(f"Failed to start instance {instance_name}: {e}")
            instance.is_running = False
            return False

    def stop_instance(self, instance_name: str) -> bool:
        """
        Stop a running StormShadow instance.

        Args:
            instance_name: Name of the instance to stop

        Returns:
            bool: True if stopped successfully
        """
        if instance_name not in self.instances:
            print_error(f"Instance {instance_name} not found")
            return False

        instance = self.instances[instance_name]

        if not instance.is_running:
            print_error(f"Instance {instance_name} is not running")
            return False

        try:
            print_info(f"Stopping instance {instance_name}...")
            self._notify_status_change(instance_name, "stopping")

            # Stop the StormShadow instance
            instance.instance.stop()

            # Wait for thread to finish (with timeout)
            if instance.thread and instance.thread.is_alive():
                instance.thread.join(timeout=5.0)

            # Additional cleanup: ensure any remaining spoofer processes are terminated
            try:
                self._cleanup_spoofer_processes()
            except Exception as e:
                print_warning(f"Error during spoofer cleanup: {e}")

            instance.is_running = False
            self._notify_status_change(instance_name, "stopped")
            print_success(f"Instance {instance_name} stopped successfully")
            return True

        except Exception as e:
            print_error(f"Failed to stop instance {instance_name}: {e}")
            return False

    def _cleanup_spoofer_processes(self):
        """
        Emergency cleanup of any remaining spoofer processes.
        This is a failsafe to ensure no spoofer processes remain running.
        """
        try:
            import os
            import signal
            import subprocess
            
            print_debug("Performing emergency spoofer process cleanup...")
            
            # Use pkill to find and terminate spoofer processes
            try:
                # First try to find spoofer processes gracefully
                result = subprocess.run(['pgrep', '-f', 'spoofer.py'], capture_output=True, text=True)
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    pids = [pid for pid in pids if pid.strip()]
                    
                    if pids:
                        print_debug(f"Found {len(pids)} spoofer processes to clean up")
                        # Try graceful termination first
                        subprocess.run(['pkill', '-TERM', '-f', 'spoofer.py'], capture_output=True)
                        
                        # Give processes time to terminate gracefully
                        import time
                        time.sleep(1)
                        
                        # Check if any processes remain and force kill them
                        result = subprocess.run(['pgrep', '-f', 'spoofer.py'], capture_output=True, text=True)
                        if result.returncode == 0:
                            print_debug("Some spoofer processes didn't terminate gracefully, force killing")
                            subprocess.run(['pkill', '-KILL', '-f', 'spoofer.py'], capture_output=True)
                        
                        print_info("Spoofer process cleanup completed")
                    else:
                        print_debug("No stray spoofer processes found")
                else:
                    print_debug("No spoofer processes found running")
                    
            except FileNotFoundError:
                print_debug("pgrep/pkill not available, skipping spoofer process cleanup")
            except Exception as e:
                print_debug(f"Error using pgrep/pkill: {e}")
                
        except Exception as e:
            print_warning(f"Error during spoofer process cleanup: {e}")

    def remove_instance(self, instance_name: str) -> bool:
        """
        Remove a StormShadow instance.

        Args:
            instance_name: Name of the instance to remove

        Returns:
            bool: True if removed successfully
        """
        if instance_name not in self.instances:
            print_error(f"Instance {instance_name} not found")
            return False

        instance = self.instances[instance_name]

        # Stop the instance if it's running
        if instance.is_running:
            if not self.stop_instance(instance_name):
                print_error(f"Failed to stop instance {instance_name} before removal")
                return False

        try:
            # Remove the instance
            del self.instances[instance_name]
            print_success(f"Instance {instance_name} removed successfully")
            return True

        except Exception as e:
            print_error(f"Failed to remove instance {instance_name}: {e}")
            return False

    def get_instance_status(self, instance_name: str) -> Optional[str]:
        """
        Get the status of a StormShadow instance.

        Args:
            instance_name: Name of the instance

        Returns:
            Optional[str]: Status string or None if instance not found
        """
        if instance_name not in self.instances:
            return None

        instance = self.instances[instance_name]
        if instance.is_running:
            return "running"
        else:
            return "stopped"

    def get_all_instances(self) -> Dict[str, str]:
        """
        Get all instances and their statuses.

        Returns:
            Dict[str, str]: Instance name to status mapping
        """
        return {
            name: "running" if instance.is_running else "stopped"
            for name, instance in self.instances.items()
        }

    def register_status_callback(self, callback_id: str, callback: Callable[[str, str], None]):
        """
        Register a callback for status changes.

        Args:
            callback_id: Unique identifier for the callback
            callback: Function to call on status changes (instance_name, status)
        """
        self.status_callbacks[callback_id] = callback

    def unregister_status_callback(self, callback_id: str):
        """
        Unregister a status callback.

        Args:
            callback_id: Identifier of the callback to remove
        """
        if callback_id in self.status_callbacks:
            del self.status_callbacks[callback_id]

    def _notify_status_change(self, instance_name: str, status: str):
        """
        Notify all registered callbacks about a status change.

        Args:
            instance_name: Name of the instance that changed status
            status: New status
        """
        for callback in self.status_callbacks.values():
            try:
                callback(instance_name, status)
            except Exception as e:
                print_error(f"Error in status callback: {e}")

    def cleanup(self):
        """Clean up all instances and resources."""
        print_info("Cleaning up GUI Storm Manager...")
        print_info(f"Shared SUID for this session: {self.shared_suid}")

        # Stop all running instances
        stopped_count = 0
        for instance_name in list(self.instances.keys()):
            instance = self.instances[instance_name]
            print_info(f"Processing instance {instance_name}, running: {instance.is_running}")
            if instance.is_running:
                print_info(
                    f"Stopping instance {instance_name} with SUID: {
                        instance.instance.session_uid}")
                if self.stop_instance(instance_name):
                    stopped_count += 1
                else:
                    print_error(f"Failed to stop instance {instance_name}")

        # Manual cleanup for all instances with this shared SUID
        if stopped_count > 0 or self.instances:
            print_info(f"Performing manual cleanup for shared SUID: {self.shared_suid}")
            try:
                from utils.network.iptables import remove_all_rules_for_suid, heartbeat_remove
                # Remove heartbeat file first
                heartbeat_remove(self.shared_suid)
                # Remove all rules for the shared SUID
                removed_count = remove_all_rules_for_suid(self.shared_suid)
                if removed_count > 0:
                    print_success(
                        f"Manually cleaned up {removed_count} iptables rules for shared SUID {
                            self.shared_suid}")
                else:
                    print_info(f"No rules found to clean up for shared SUID {self.shared_suid}")
            except Exception as e:
                print_error(f"Error during manual cleanup: {e}")

        # Clear all instances
        self.instances.clear()

        # Clear callbacks
        self.status_callbacks.clear()

        print_success("GUI Storm Manager cleanup completed")
