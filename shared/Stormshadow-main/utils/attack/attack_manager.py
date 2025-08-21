"""
Attack Manager for StormShadow.

This module provides centralized attack lifecycle management by directly
working with attack modules and a simple discovery mechanism.
"""

from pathlib import Path
from typing import Dict, Optional
from utils.core.logs import print_debug, print_error, print_in_dev, print_info, print_success, print_warning
from utils.config.config import Config
from utils.attack.attack_modules_finder import find_attack_modules
from utils.attack.AttackSession import AttackSession, build_attack_from_module
from utils.attack.attack_enums import AttackStatus

class AttackManager:
    """
    Manages attack module lifecycle and coordination.
    
    This manager provides:
    - Attack module discovery and loading
    - Attack lifecycle management (start/stop/status)
    - Coordination with other system components
    """

    def __init__(self, config: Config, attack_modules_path: Path, spoofing_enabled: bool, return_path_enabled: bool, session_uid: Optional[str] = None, dry_run: bool = False) -> None:
        """
        Initialize attack manager.
        
        Args:
            config: Optional attack configuration
            session_uid: Session unique ID to pass to attacks
        """
        self.config = config
        self.session_uid = session_uid
        # Try to find attack modules directory
        self.attack_modules_folder = attack_modules_path
        self.available_modules: Dict[str,Path] = find_attack_modules(self.attack_modules_folder)
        self.spoofing_enabled = spoofing_enabled
        self.return_path_enabled = return_path_enabled
        self.dry_run = dry_run
        print_debug(f"Initializing attack manager with configuration: {config}")

        print_success("Attack manager initialized")

        self.current_attack: Optional[AttackSession] = None  # Currently running attack module

    def actualize_available_modules(self) -> None:
        """
        Refresh the list of available attack modules.
        
        This method rescans the attack modules directory to update the list of available modules.
        """
        print_debug("Actualizing available attack modules...")
        self.available_modules = find_attack_modules(self.attack_modules_folder)
        print_info(f"Available attack modules updated: {self.available_modules.keys()}")
    
    def load_attack_module(self, module_name: str) -> bool:
        """
        Load an attack module by name.
        
        Args:
            module_name: Name of the attack module to load
        
        Returns:
            An instance of the loaded attack module
        """
        print_debug(f"Loading attack module: {module_name}")
        # Here you would implement logic to dynamically load the attack module
        # For example, using importlib or similar mechanisms
        # This is a placeholder for the actual loading logic
        
        try :
            try :
                module_path = self.available_modules[module_name]
                print_info(f"Found attack module: {module_name} at {module_path}")
            # If the module is not found in the available modules, try to find it again
            # After actualizing the available modules
            except KeyError:
                self.available_modules = find_attack_modules(self.attack_modules_folder)
                if module_name not in self.available_modules:
                    print_error(f"Attack module {module_name} not found in available modules.")
                    return False
                module_path = self.available_modules[module_name]
                print_info(f"Found attack module: {module_name} at {module_path}")
        except KeyError:
            print_error(f"Attack module {module_name} not found in available modules.")
            raise KeyError(f"Attack module {module_name} not found in available modules.")
        
        # Build the attack from the module path
        self.current_attack : Optional[AttackSession] = build_attack_from_module(module_path, self.config.parameters, enable_spoofing=self.spoofing_enabled, session_uid=self.session_uid, dry_run=self.dry_run)

        return True  # Return True if the module was loaded successfully

    def start(self) -> None:
        """
        Start the attack manager.
        
        This method initializes and starts all attack modules based on the configuration.
        """
        print_info("Starting attack manager...")
        print_info("Loading attack...")
        if not self.load_attack_module(self.config.parameters.get("attack_name")):
            print_error("Failed to load attack module.")
            raise RuntimeError("Failed to load attack module. Please check the module name and available modules.")

        if self.current_attack:
            if self.current_attack.get_status() == AttackStatus.RUNNING:
                print_warning("Attack is already running, stopping it before starting a new one.")
                self.current_attack.stop()
            if self.current_attack.get_status() == AttackStatus.STOPPED and self.current_attack.is_resumable:
                print_info("Resuming attack...")
                self.current_attack.resume()
            else:
                self.current_attack.start()
        else:
            print_error("No attack module loaded. Attack module must be loaded before starting the manager.")
            raise RuntimeError("No attack module loaded. Please load an attack module before starting the manager.")

    def stop(self) -> None:
        """
        Stop the attack manager.
        
        This method stops all running attack modules and cleans up resources.
        """
        print_in_dev("Stopping attack manager...")
        # Implement logic to stop all attack modules
        if self.current_attack:
            self.current_attack.stop()
        if self.return_path_enabled:
            print_in_dev("Stopping return path...")