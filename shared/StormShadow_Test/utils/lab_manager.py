"""
Lab Manager for StormShadow.

This module provides centralized lab environment management by managing
Docker containers and lab infrastructure.
"""

import os
import time

from .core.logs import print_info, print_error, print_debug
from .config.config import Config
from utils.core.command_runner import run_command_str, run_process

class LabManager:
    """
    Manages lab module lifecycle and coordination.

    This manager provides:
    - Lab module discovery and loading
    - Lab lifecycle management (start/stop/status)
    - Coordination with other system components
    """

    def __init__(self, config: Config, keep_lab_open: bool = False, gui_mode: bool = False, dry_run: bool = False) -> None:
        """
        Initialize lab manager.
        
        Args:
            config: Lab configuration
            keep_lab_open: Whether to keep lab open after stopping
            gui_mode: Whether running in GUI mode
            dry_run: Whether to run in dry-run mode
            open_window: Whether to open lab container in a new terminal window
        """
        self.parameters = config.parameters
        self.container_process = None
        self.container_name = "sip-victim"
        self.docker_image = "asterisk-sip-server"
        self.dry_run = dry_run
        
        # Get the project root directory (assuming lab manager is in utils/)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.keep_lab_open = keep_lab_open
        self.gui_mode = gui_mode
        self.open_window = self.parameters.get("open_window", False)  # Use config setting for window opening
        print_debug(f"Lab manager initialized with parameters: {self.parameters}")
        self.is_running = False  # Track if the lab is currently running
        print_info("Lab manager initialized")

    def _cleanup_container(self) -> None:
        """
        Clean up any existing Docker container.
        """
        if self.dry_run:
            print_info("Dry run mode: would clean up existing containers")
            return
            
        try:
            print_info("Cleaning up existing containers...")
            
            # Check if container exists by listing all containers and checking names
            result = run_command_str(
                f"docker ps -a --format '{{{{.Names}}}}'",
                check=False,
                capture_output=True,
                want_sudo=True
            )
            
            # Check if our container name is in the output
            container_names = result.stdout.strip().split('\n') if result.stdout.strip() else []
            container_exists = self.container_name in container_names
            
            if container_exists:
                print_info(f"Removing existing container '{self.container_name}'...")
                run_command_str(f"docker rm -f {self.container_name}", want_sudo=True)
                print_info("Container cleanup complete")
            else:
                print_debug(f"Container '{self.container_name}' does not exist or was already removed")
                
        except Exception as e:
            print_error(f"Error during container cleanup: {e}")

    def _build_docker_image(self) -> bool:
        """
        Build the Docker image if it doesn't exist.
        
        Returns:
            bool: True if image exists or was built successfully, False otherwise
        """
        if self.dry_run:
            print_info("Dry run mode: would check/build Docker image")
            return True
            
        try:
            # Check if image exists
            result = run_command_str(
                f"sudo docker images -q {self.docker_image}",
                capture_output=True,
                check=False
            )
            
            if result.stdout.strip():
                print_debug(f"Docker image '{self.docker_image}' already exists")
                return True
            
            print_info(f"Building Docker image '{self.docker_image}'...")
            dockerfile_path = os.path.join(self.project_root, "sip-lab", "sip_server")

            build_result = run_command_str(
                f"sudo docker build -t {self.docker_image} .",
                cwd=dockerfile_path,
                capture_output=False
            )
            
            if build_result.returncode == 0:
                print_info("Docker image built successfully")
                return True
            else:
                print_error("Failed to build Docker image")
                return False
                
        except Exception as e:
            print_error(f"Error building Docker image: {e}")
            return False

    def start(self) -> None:
        """
        Start the lab manager.
        
        This method initializes and starts the SIP lab Docker container.
        """
        print_info("Starting lab manager...")
        
        if self.dry_run:
            print_info("Dry run mode: would start lab Docker container")
            return
        
        try:
            # Clean up any existing containers
            self._cleanup_container()
            
            # Build Docker image if needed
            if not self._build_docker_image():
                print_error("Failed to build Docker image, cannot start lab")
                return
            
            # Start the Docker container
            print_info("Starting Docker container...")
            
            # Choose Docker flags based on whether we want a terminal window
            if self.open_window:
                # Interactive mode with terminal
                docker_flags = "--rm -it"
                print_debug("Starting container in interactive terminal mode")
            else:
                # Detached mode for background execution
                docker_flags = "--rm -d"
                print_debug("Starting container in detached background mode")
            
            docker_command = (
                f"docker run {docker_flags} "
                f"--network host "
                f"--cap-add=NET_ADMIN "
                f"--cap-add=NET_RAW "
                f"-e SPOOFED_SUBNET=10.10.123.0/25 "
                f"-e RETURN_ADDR=10.135.97.2 "
                f"--name {self.container_name} "
                f"{self.docker_image}"
            )
            
            # Start the container - use open_window setting instead of hardcoded new_terminal
            self.container_process = run_process(
                docker_command.split(),
                new_terminal=self.open_window,
                want_sudo=True,
                sudo_preserve_env=True,
                sudo_non_interactive=True
            )
            
            print_info(f"Lab container '{self.container_name}' started successfully")
            
            # When running in detached mode, give it a bit more time to start
            initial_wait = 1.0 if not self.open_window else 0.2
            time.sleep(initial_wait)
            
            waiting_time = 0  # seconds to wait for the container to be ready
            timeout = 10  # increased timeout for more reliable startup
            status = self.status()
            print_debug(f"Initial container status check: '{status}', is_running: {self.is_running}")
            
            while (self.is_running is False and waiting_time < timeout):
                time.sleep(0.5)  # Wait a bit longer between checks
                waiting_time += 0.5
                status = self.status()
                print_debug(f"Container status after {waiting_time}s: '{status}', is_running: {self.is_running}")
                
            if waiting_time >= timeout:
                print_error("Lab container did not start within the expected time")
                print_error(f"Final status: '{status}', is_running: {self.is_running}")
                raise Exception("Lab container did not start in time")
            
            if self.open_window:
                print_info(f"Container is running in a new terminal window: {status}")
            else:
                print_info(f"Container is running in background: {status}")

        except Exception as e:
            print_error(f"Error starting lab: {e}")
            self.stop()

    def stop(self) -> None:
        """
        Stop the lab manager.
        
        This method stops the running Docker container and cleans up resources.
        """
        print_info("Stopping lab manager...")
        
        if self.dry_run:
            print_info("Dry run mode: would stop lab Docker container")
            return
        
        try:
            # Terminate the container process if it exists
            if self.container_process and not self.keep_lab_open:
                try:
                    print_info(f"Terminating container process '{self.container_name}'...")
                    self.container_process.terminate()
                    time.sleep(0.2)  # Give it time to terminate gracefully

                    if self.container_process.poll() is None:
                        self.container_process.kill()
                    # Clean dnat rules if any
                    # run_command(f"sudo iptables -t nat -D OUTPUT -d {self.spoofed_subnet} -p udp -m udp --sport 5060 -m comment --comment asterisk-dnat -j DNAT --to-destination {self.return_addr}")
                except Exception as e:
                    print_debug(f"Error terminating container process: {e}")
                finally:
                    self.container_process = None                
                # Clean up the container
                self._cleanup_container()
                
                print_info("Lab manager stopped successfully")
            
        except Exception as e:
            print_error(f"Error stopping lab: {e}")

    def status(self) -> str:
        """
        Check if the lab is running.
        
        Returns:
            str: Status string of the container
        """
        if self.dry_run:
            print_info("Dry run mode: would check lab status")
            return "Dry run mode"
            
        try:
            result = run_command_str(
                f"docker ps --filter \"name={self.container_name}\" --format '{{{{.Status}}}}'",
                check=False,
                capture_output=True,
                want_sudo=True
            )
            status_output = result.stdout.strip()
            self.is_running = status_output.startswith("Up")
            return status_output
        except Exception as e:
            print_error(f"Error checking lab status: {e}")
            return "Unknown"

    def restart(self) -> None:
        """
        Restart the lab manager.
        """
        print_info("Restarting lab manager...")
        self.stop()
        time.sleep(1)  # Brief pause between stop and start
        self.start()