# utils/core/stormshadow.py

"""StormShadow core orchestrator module.
This module serves as the main entry point for the StormShadow application,
handling the initialization and orchestration of various components.
It manages configuration, attack modules, and lab modules, providing a unified interface for the application.
Author: Corentin COUSTY
"""

from pathlib import Path
from typing import Optional

from utils.config.config import Config, ConfigType, Parameters
from utils.attack.attack_manager import AttackManager
from utils.config.config_manager import ConfigManager
from utils.core.logs import print_info, print_warning, print_error, print_success, print_debug, set_verbosity, use_log_file
from utils.network.iptables import cleanup_stale_rules, generate_suid, heartbeat_touch, heartbeat_remove, remove_all_rules_for_suid
import threading
from utils.lab_manager import LabManager

class StormShadow:
    """
    Main class for the StormShadow application.
    """

    def __init__(self, CLI_Args: Parameters, default_config_path: Optional[Path] = None, session_uid: Optional[str] = None, preserve_existing_rules: bool = False) -> None:
        # Setup logging first, before any other operations
        verbosity = CLI_Args.get("verbosity", "info") if CLI_Args else "info"
        set_verbosity(verbosity)
        
        print_info("Initializing StormShadow...")
        
        # Generate or use provided session UID for this StormShadow instance
        self.session_uid: str = session_uid or generate_suid()
        print_debug(f"StormShadow session UID: {self.session_uid}")
        
        # Store preservation setting for existing rules
        self.preserve_existing_rules = preserve_existing_rules
        
        # Start heartbeat for this session
        self._hb_thread: Optional[threading.Thread] = None
        self._hb_stop = threading.Event()
        self._start_heartbeat()
        
        # Initialize the configuration manager with CLI arguments and default config path
        print_debug("Initializing ConfigManager with CLI arguments and default config path.")        
        self.configManager = ConfigManager(CLI_Args=CLI_Args, default_config_path=default_config_path)
        print_debug("ConfigManager initialized with CLI arguments and default config path.")
        # Load configurations
        print_debug("Loading app configurations...")
        self.parameters : Parameters = self.configManager.get_config(ConfigType.APP).parameters
        print_debug("App configurations loaded successfully.")
        # If active, a simulation will be run instead of a real attack / lab
        self.dry_run = self.parameters.get("dry_run", False, path=["enabled"])

        if self.dry_run:
            print_warning("Dry run mode is enabled. No real attacks and no features will be executed.")
            print_warning("This is useful for testing configurations without affecting real systems.")

        # Configure log file if enabled
        self.log_file_on = self.parameters.get("log_file", path=["enabled"])  # Enable logging to a file
        if self.log_file_on:
            log_file_path = self.parameters.get("log_file", "stormshadow.log", path=["path"])
            print_debug(f"Enabling log file: {log_file_path}")
            use_log_file(str(log_file_path))

        self.attack_on = self.parameters.get("attack", path=["enabled"]) # Enable attack mode by default
        self.custom_payload_on = self.parameters.get("custom_payload", path=["enabled"])  # Allow the use of a custom payload for some attacks
        self.spoofing_on = self.parameters.get("spoofing", path=["enabled"])  # Enable spoofing by default
        # Activate lab features
        self.lab_on = self.parameters.get("lab", path=["enabled"])  # Enable lab mode by default
        self.defense_on = self.parameters.get("defense", path=["enabled"])  # Enable defense mode by default
        self.return_path_on = self.parameters.get("return_path", path=["enabled"])  # Enable return path

        # Other features
        self.metrics_on = self.parameters.get("metrics", path=["enabled"])  # Enable metrics collection by default
        self.metrics_config : Config = self.configManager.get_config(ConfigType.METRICS)
        self.defense_config : Config = self.configManager.get_config(ConfigType.DEFENSE)
        self.gui_config : Config = self.configManager.get_config(ConfigType.GUI)
        self.custom_configs : Config = self.configManager.get_config(ConfigType.CUSTOM)

    def setup(self) -> None:
        """
        Run the StormShadow application.
        """
        print_info("Starting StormShadow...")

        # Proactive cleanup of stale StormShadow iptables rules on startup
        try:
            removed = cleanup_stale_rules()
            if removed:
                print_warning(f"Removed {removed} stale StormShadow iptables rules on startup")
            else:
                print_debug("No stale StormShadow iptables rules found on startup")
        except Exception as e:
            print_warning(f"Unable to perform startup iptables cleanup: {e}")

        # Initialize managers based on configuration
        if self.lab_on:
            try :
                print_debug("Lab mode is enabled, initializing lab manager...")
                self.lab_manager = LabManager(self.configManager.get_config(ConfigType.LAB), dry_run=self.dry_run)
                print_success("Lab mode is enabled.")
            except Exception as e:
                print_error(f"Failed to initialize lab manager: {e}")
                self.lab_manager = None
        else:
            print_debug("Lab mode is disabled.")
            self.lab_manager = None
    
        if self.attack_on:
            try:
                print_debug("Attack mode is enabled, initializing attack manager...")
                # Use absolute path relative to the current file location
                from utils.core.system_utils import get_project_root
                project_root = get_project_root()
                attack_modules_path = project_root / "sip_attacks"
                self.attack_manager = AttackManager(self.configManager.get_config(ConfigType.ATTACK), attack_modules_path, spoofing_enabled=self.spoofing_on, return_path_enabled=self.return_path_on, session_uid=self.session_uid, dry_run=self.dry_run)
                print_success("Attack mode is enabled.")
            except Exception as e:
                print_error(f"Failed to initialize attack manager: {e}")
                self.attack_manager = None
        else:
            print_debug("Attack mode is disabled.")
            self.attack_manager = None

    def run(self) -> None:
        """
        Start the features of the StormShadow application.
        For CLI mode, this will start the main application loop.
        """
        print_info("Starting features...")

        if self.lab_on :
            if self.lab_manager:
               try :
                    print_info("Starting lab manager...")
                    self.lab_manager.start()
               except Exception as e:
                    print_error(f"Failed to start lab manager: {e}")
                    self.lab_manager = None
            else:
                print_error("Lab manager is not initialized but should be. Skipping lab features.")
        if self.attack_on :
            if self.attack_manager:
                try:
                    print_info("Starting attack manager...")
                    self.attack_manager.start()
                except Exception as e:
                    print_error(f"Failed to start attack manager: {e}")
                    self.attack_manager = None
            else:
                print_error("Attack manager is not initialized but should be. Skipping attack features.")
    
    def stop(self) -> None:
        """
        Stop the features of the StormShadow application.
        For CLI mode, this will stop the main application loop.
        """
        
        print_info(f"Stopping StormShadow features for session {self.session_uid}...")

        if self.attack_on and hasattr(self, 'attack_manager') and self.attack_manager:
            try:
                print_info("Stopping attack manager...")
                self.attack_manager.stop()
            except Exception as e:
                print_error(f"Failed to stop attack manager: {e}")

        if self.lab_on and hasattr(self, 'lab_manager') and self.lab_manager:
            try:
                self.lab_manager.stop()
            except Exception as e:
                print_error(f"Failed to stop lab manager: {e}")
                
        # Stop heartbeat and cleanup session rules
        self._stop_heartbeat()
        try:
            # Remove heartbeat file first to prevent the cleanup logic from thinking this session is active
            print_info(f"Removing heartbeat file for session {self.session_uid}")
            heartbeat_remove(self.session_uid)
            # Remove ALL iptables rules for this session (including anchor jumps)
            print_info(f"Cleaning up iptables rules for session {self.session_uid}")
            removed_count = remove_all_rules_for_suid(self.session_uid)
            if removed_count > 0:
                print_success(f"Cleaned up {removed_count} iptables rules for session {self.session_uid}")
            else:
                print_info(f"No rules found to clean up for session {self.session_uid}")
        except Exception as e:
            print_error(f"Error during rule cleanup for session {self.session_uid}: {e}")

    def _start_heartbeat(self) -> None:
        """Start heartbeat thread to keep session alive for iptables rule protection."""
        def _hb_loop():
            # Touch immediately then every ~50 minutes
            heartbeat_touch(self.session_uid)
            interval = 50 * 60  # 50 minutes
            while not self._hb_stop.wait(timeout=interval):
                heartbeat_touch(self.session_uid)
        
        self._hb_stop.clear()
        self._hb_thread = threading.Thread(target=_hb_loop, name=f"stormshadow-main-hb-{self.session_uid}", daemon=True)
        self._hb_thread.start()
        
    def _stop_heartbeat(self) -> None:
        """Stop heartbeat thread."""
        self._hb_stop.set()
        if self._hb_thread and self._hb_thread.is_alive():
            self._hb_thread.join(timeout=2)