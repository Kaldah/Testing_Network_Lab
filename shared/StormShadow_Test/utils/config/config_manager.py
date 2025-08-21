"""
Configuration loader for StormShadow.

This module handles loading configurations from various sources with proper precedence:
1. Default configuration
2. Local configuration (lab/attack folder)
3. Command line parameters
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from utils.network.iptables import get_current_iptables_queue_num

from ..core.logs import print_debug, print_success, print_warning

from ..core.system_utils import get_interface, get_interface_ip

from .config import Config, ConfigType, Parameters, UpdateDefaultConfigFromCLIArgs

def get_available_queue_num() -> int:
    """
    Placeholder function to check the current queue number.
    This should be implemented to return the actual queue number of the machine.
    """
    return get_current_iptables_queue_num() + 1

class ConfigManager:
    """
    Configuration manager for StormShadow.
    If no config path is provided, it defaults to the standard configuration file.
    If a config path is provided, it uses that path to load the configuration.
    """
    def __init__(self, CLI_Args: Optional[Parameters] = None, default_config_path: Optional[Path]=None) -> None:
        if default_config_path is None:
            self.config_file_path = Path(__file__).resolve().parents[2]/ "configs" / "sip-stormshadow-config.yaml"
        else:
            self.config_file_path = default_config_path

        if not self.config_file_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file_path}")
        print_debug(f"Default Config file path: {self.config_file_path}")

        # Contain the shared configuration for every parts of the application
        self.app_config: Config
        # Contain the configuration for the attack module
        self.attack_config: Config
        # Contain the configuration for the lab module
        self.lab_config: Config
        # Contain the configuration for the metrics module
        self.metrics_config: Config
        # Contain the configuration for the defense module
        self.defense_config: Config
        # Contain the configuration for the GUI
        self.gui_config: Config
        # Allow to load custom configurations for personalized modules
        self.custom_configs: Config
        # Load the default configuration file
        default_config = self._load_default_config_file()
        # If CLI arguments are provided, update the default configuration
        print_debug(f"Show default configuration file : {default_config}")
        if CLI_Args:
            print_debug(f"Updating default configuration with CLI arguments: {CLI_Args}")
            UpdateDefaultConfigFromCLIArgs(default_config, CLI_Args)
            print_success("Default configuration updated with CLI arguments.")
        else:
            print_debug("No CLI arguments provided, using default configuration.")
            print_warning("No CLI arguments provided, using default configuration.")
        # Load all configurations
        self._load_all_configs(default_config)
        print_success("Configuration manager initialized successfully.")

    def _load_all_configs(self, default_config: Config) -> None:
        # Use the default configuration file
        # and resolve any auto configurations
        # to ensure all parameters are set correctly
        default_config = self._resolve_auto_configs(default_config)

        # Load all configurations based on the default config
        self._load_app_config(default_config)
        self._load_attack_config(default_config)
        self._load_lab_config(default_config)
        self._load_metrics_config(default_config)
        self._load_defense_config(default_config)
        self._load_gui_config(default_config)
        self._load_custom_configs(default_config)

    def _load_default_config_file(self) -> Config:
        default_config_path = self.config_file_path
        if not default_config_path.exists():
            raise FileNotFoundError(f"Default config path not found: {default_config_path}")

        with open(default_config_path, "r") as f:
            yaml_content: Dict[str, Any] = yaml.safe_load(f)
        
        print_debug(f"Default configuration loaded from {default_config_path}")
        parameters=Parameters(yaml_content)
        print_debug(f"Default configuration parameters: {parameters}")
        
        default_config = Config(
            config_type=ConfigType.DEFAULT,
            parameters=parameters
        )

        return default_config

    def _resolve_auto_configs(self, default_config: Config) -> Config:
        
        parameters = default_config.parameters
        auto_to_resolve = [
            ["attack", "target_ip"],
            ["attack", "target_port"],
            ["attack", "source_port"],
            ["attack", "attack_queue_num"],
            ["attack", "interface"],
            ["network", "interface"],
            ["network", "own_ip"],
            ["metrics", "ack_port"],
            ["metrics", "ack_return_queue_num"],
            ["lab", "interface"],
            ["lab", "server_ip"],
            ["lab", "return_path", "dnat_target_ip"],
            ["lab", "return_path", "dnat_port"],
            ["lab", "return_path", "spoofed_subnet"],
            ["metrics", "open_window"],
            ["lab", "open_window"],
            ["attack", "open_window"]
        ]

        # Get default values for auto configurations
        default_sip_port = parameters.get("sip_port", 5060, ["network"])
        default_ack_port = parameters.get("ack_port", 4000, ["metrics"])
        default_interface = parameters.get("interface", "auto", ["network"])
        default_ip = parameters.get("own_ip", "auto", ["network"])
        first_queue_num = parameters.get("first_queue_num", "auto", ["network"])

        # Check if the interface is set, if not, use the default one
        if default_interface == "auto":
            default_interface = get_interface()
            print_debug(f"Using default interface: {default_interface}")
        # Check if the IP is set, if not, use the default one
        if default_ip == "auto":
            default_ip = get_interface_ip(default_interface)
        
        # Resolve auto configurations
        for path in auto_to_resolve:
            k = path[-1]
            # v = find_value_by_path(parameters, path)
            v = parameters.get(k, "auto", path[:-1])
            if v == "auto":
                value = None
                # Resolve the auto value based on the context
                match k:
                    case "target_ip":
                        # Use the local IP for testing purposes
                        value = default_ip
                    case "target_port":
                        # Use the sip port from network config
                        value = default_sip_port
                    case "source_port":
                        # Use the ack port from metrics config
                        value = default_ack_port
                    case "attack_queue_num":
                        # Use the first available queue number for the attack
                        value = first_queue_num if first_queue_num != "auto" else get_available_queue_num() 
                    case "ack_return_queue_num":
                        # Increment the first queue number for ACK return
                        value = first_queue_num if first_queue_num != "auto" else get_available_queue_num()
                    case "interface":
                        # Use the interface from network config
                        print_debug(f"Using interface: {default_interface}")
                        value = default_interface
                    case "server_ip":
                        # Use the interface from network config (simulate IP from interface)
                        value = default_ip
                    case "dnat_target_ip":
                        # Use the attack target_ip
                        value = default_ip
                    case "dnat_port":
                        # Use the attack target_port (already resolved above)
                        value = default_sip_port
                    case "spoofed_subnet":
                        # Use the attack spoofing subnet
                        value = parameters.get("spoofing_subnet", "10.10.123.0/25", ["attack"])
                    case "open_window":
                        # Use the app open_window parameter
                        value = parameters.get("open_window", True, ["app", "enabled"])
                    case _ : pass  # No specific action for other keys
                # If a value is resolved, set it in the parameters
                if value is not None:
                    # Set the resolved value in the parameters
                    parameters.set(k, value, path[:-1])
        print_debug(f"Resolved parameters: {parameters}")
        return Config(
            config_type=ConfigType.DEFAULT,
            parameters=parameters
        )

    def _load_app_config(self, default_config: Config) -> None:
        parameters : Dict[str, Any] = default_config.parameters["app"] if "app" in default_config.parameters else {}
        if parameters == {}:
            raise ValueError("App configuration is missing in the default config.")
        
        self.app_config = Config(
            config_type=ConfigType.APP,
            parameters=Parameters(parameters)
        )

    def _load_attack_config(self, default_config: Config) -> None:
        attack_parameters : Dict[str, Any]= default_config.parameters["attack"] if "attack" in default_config.parameters else {}

        if not attack_parameters:
            raise ValueError("Attack configuration is missing in the default config.")

        self.attack_config = Config(
            config_type=ConfigType.ATTACK,
            parameters=Parameters(attack_parameters)
        )

    def _load_lab_config(self, default_config: Config) -> None:
        lab_parameters : Dict[str, Any] = default_config.parameters["lab"] if "lab" in default_config.parameters else {}

        if not lab_parameters:
            raise ValueError("Lab configuration is missing in the default config.")

        self.lab_config = Config(
            config_type=ConfigType.LAB,
            parameters=Parameters(lab_parameters)
        )

    def _load_metrics_config(self, default_config: Config) -> None:
        metrics_parameters : Dict[str, Any] = default_config.parameters["metrics"] if "metrics" in default_config.parameters else {}
        if not metrics_parameters:
            raise ValueError("Metrics configuration is missing in the default config.")

        self.metrics_config = Config(
            config_type=ConfigType.METRICS,
            parameters=Parameters(metrics_parameters)
        )

    def _load_defense_config(self, default_config: Config) -> None:

        try:
            defense_parameters : Dict[str, Any] = default_config.parameters["defense"] if "defense" in default_config.parameters else {}
            if not defense_parameters:
                raise ValueError("Defense configuration is missing in the default config.")

        except Exception as e:
            print_warning(f"No defense implementation for now: {e}")
            defense_parameters = {}

        self.defense_config = Config(
            config_type=ConfigType.DEFENSE,
            parameters=Parameters(defense_parameters)
        )

    def _load_gui_config(self, default_config: Config) -> None:
        gui_parameters : Dict[str, Any] = default_config.parameters["gui"] if "gui" in default_config.parameters else {}
        if not gui_parameters:
            raise ValueError("GUI configuration is missing in the default config.")

        self.gui_config = Config(
            config_type=ConfigType.GUI,
            parameters=Parameters(gui_parameters)
        )

    def _load_custom_configs(self, default_config: Config) -> None:
        custom_parameters : Dict[str, Any] = default_config.parameters["custom"] if "custom" in default_config.parameters else {}
        if not custom_parameters:
            print_debug("No custom configurations found, using empty config.")
            custom_parameters = {}

        self.custom_configs = Config(
            config_type=ConfigType.CUSTOM,
            parameters=Parameters(custom_parameters)
        )

    def reload_configs(self) -> None:
        """
        Reload all configurations from the default config file.
        This is useful if the configuration file has been modified.
        """
        print_debug("Reloading configurations...")
        default_config = self._load_default_config_file()
        self._load_all_configs(default_config)
        print_success("Configurations reloaded successfully.")

    def reload_configs_from_file(self, config_path: Path) -> None:
        """
        Load a configuration from a specific file path.
        The configuration must implement the DEFAULT type.
        
        Args:
            config_path (Path): Path to the configuration file
        
        Returns:
            Config: Loaded configuration
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            yaml_content: Dict[str, Any] = yaml.safe_load(f)

        if not yaml_content or "app" not in yaml_content:
            raise ValueError("Invalid configuration file.")

        new_default_config = Config(
            config_type=ConfigType.DEFAULT,
            parameters=Parameters(yaml_content)
        )

        # Reload all configurations based on the new default config
        self._load_all_configs(new_default_config)

        return None

    def get_all_configs(self) -> Dict[ConfigType, Config]:
        """
        Get all loaded configurations.

        Returns:
            Dict[ConfigType, Config]: Dictionary of all configurations
        """
        return {
            ConfigType.APP: self.app_config,
            ConfigType.ATTACK: self.attack_config,
            ConfigType.LAB: self.lab_config,
            ConfigType.METRICS: self.metrics_config,
            ConfigType.DEFENSE: self.defense_config,
            ConfigType.GUI: self.gui_config,
            ConfigType.CUSTOM: self.custom_configs
        }


    def get_config(self, config_type: ConfigType) -> Config:
        """
        Get a specific configuration by type.

        Args:
            config_type (ConfigType): The type of configuration to retrieve

        Returns:
            Config: The requested configuration
        """

        match config_type:
            case ConfigType.APP:
                return self.app_config
            case ConfigType.ATTACK:
                return self.attack_config
            case ConfigType.LAB:
                return self.lab_config
            case ConfigType.METRICS:
                return self.metrics_config
            case ConfigType.DEFENSE:
                return self.defense_config
            case ConfigType.GUI:
                return self.gui_config
            case ConfigType.CUSTOM:
                return self.custom_configs
            case ConfigType.DEFAULT:
                return Config(
                    config_type=ConfigType.DEFAULT,
                    parameters=self._load_default_config_file().parameters
                )
            case _:
                raise ValueError(f"Unknown configuration type: {config_type}")
