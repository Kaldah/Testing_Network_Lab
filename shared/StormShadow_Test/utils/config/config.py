"""
This module defines the configuration management system for the StormShadow application.
It includes configuration types and data structures.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, cast, Optional, override
from enum import Enum
from ..core.logs import print_debug, print_info, print_warning

class ConfigType(Enum):
    DEFAULT = "default"
    APP = "app"
    LOG = "log"
    GUI = "gui"
    SIP_ATTACK = "sip_attack"
    ATTACK = "sip_attack"
    LAB = "lab"
    METRICS = "metrics"
    DEFENSE = "defense"
    CUSTOM = "custom"

@dataclass
class Parameters(Dict[str, Any]):
    def __init__(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize Parameters with an optional dictionary.
        
        Args:
            parameters: Optional dictionary of parameters
        """
        if parameters is None:
            print_debug("Initializing Parameters with an empty dictionary.")
            parameters = {}
        self.authorized_values = (str, int, float, bool, list, dict, Path)
        super().__init__(parameters)
    
    def __repr__(self) -> str:
        """Return a string representation of the Parameters object."""
        return f"Parameters({dict(self)})"
    
    def __str__(self) -> str:
        """Return a string representation of the Parameters object."""
        return f"Parameters({dict(self)})"
    
    @override
    def get(self, name: str, default: Any = None, path: list[str] = []) -> Any:
        """
        Get the value of a parameter by its name with a default value.
        
        Args:
            name: The name of the parameter to retrieve.
            default: The default value to return if the parameter is not found.
            path: The path to the parameter in the nested dictionary.

        Returns:
            The value of the parameter or the default value if not found.
        """

        print_debug(f"Getting parameter '{name}' with default '{default}'")

        def _get_recursive(d: Dict[str, Any], path: list[str]) -> Any:
            if not path:
                print_debug(f"Returning parameter '{name}' with the value from {d}'")
                try :
                    return d[name]
                except KeyError:
                    print_warning(f"Parameter '{name}' not found in {d}, returning default value '{default}'")
                    return default 
            key = path[0]
            print_debug(f"Checking path '{key}' in parameters")

            if key not in d:
                print_info(f"Path '{key}' not found in parameters, returning default value.")
                return default
           
            else:
                return _get_recursive(d[key], path[1:])

        return _get_recursive(self, path)

    def set(self, name: str, value: Any, path: list[str] = []) -> None:
        """
        Set the value of a parameter by its name.
        
        Args:
            name: The name of the parameter to set.
            value: The value to assign to the parameter.
        """
        if not isinstance(value, self.authorized_values):
            raise ValueError(f"Unsupported type for parameter '{name}': {type(value)}")
        print_debug(f"Setting parameter '{name}' to '{value}' with path '{path}'")
        
        def _set_recursive(d: Dict[str, Any], path: list[str]) -> None:
            if not path:
                d[name] = value
                return
            
            key = path[0]
            
            if key not in d:
                if len(path) > 0:
                    print_warning(f"Creating new path '{key}' in parameters because it does not exist.")
                    d[key] = {}
                else:
                    print_warning(f"Creating new key '{key}' in parameters because it does not exist.")
                    d[key] = value
                    return
            if len(path) == 1:
                print_debug(f"Adding {name} with value {value}")
                d[key][name] = value
            else:
                _set_recursive(d[key], path[1:])
        _set_recursive(self, path)
    
    def flatten(self) -> Dict[str, Any]:
        """
        Flatten the parameters dictionary to a single level.
        
        Returns:
            A flattened dictionary with all parameters.
        """
        print_debug("Flattening parameters dictionary")
        flat_params: Parameters = Parameters({})

        def _flatten(d: Dict[str, Any], parent_key: str = '') -> None:
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict):
                    v_str_dict = cast(Dict[str, Any], v)
                    _flatten(v_str_dict, new_key)
                else:
                    flat_params[new_key] = v

        _flatten(self)
        return flat_params

@dataclass
class Config:
    # Contain the configuration type
    config_type: ConfigType
    # Contain the configuration data with Parameters-Value pairs
    parameters: Parameters


def UpdateDefaultConfigFromCLIArgs(config: Config, args: Parameters) -> None:
    """
    Convert command line parameters to a Config object.
    
    Args:
        params: Dictionary of command line parameters
    
    Returns:
        Config: Config object with the provided parameters
    """
    print_info(f"Converting command line parameters to Config: {args}")

    parameters : Parameters = config.parameters

    for key, value in args.items():
        match key:
            case "mode":
                # Set the mode in the parameters
                print_debug(f"Setting mode to '{value}'")

                match value:
                    case "lab":
                        parameters.set("lab", True, ["app", "enabled"])
                        parameters.set("attack", False, ["app", "enabled"])
                    case "attack":
                        parameters.set("attack", True, ["app", "enabled"])
                        parameters.set("lab", False, ["app", "enabled"])
                    case "both":
                        parameters.set("lab", True, ["app", "enabled"])
                        parameters.set("attack", True, ["app", "enabled"])
                    case "gui":
                        parameters.set("gui", True, ["app", "enabled"])
                    case _ :
                        print_warning(f"Unknown mode '{value}', default parameters will be used.")
                        pass
            case "attack":
                # Set the attack mode
                    print_debug(f"Setting attack mode to {value}")
                    parameters.set("attack", value, ["app", "enabled"])
            case "lab":
                # Set the lab mode
                print_debug(f"Setting lab mode to {value}")
                parameters.set("lab", value, ["app", "enabled"])
            case "metrics":
                # Set the metrics mode
                print_debug(f"Setting metrics mode to {value}")
                parameters.set("metrics", value, ["app", "enabled"])
            case "defense":
                # Set the defense mode
                print_debug(f"Setting defense mode to {value}")
                parameters.set("defense", value, ["app", "enabled"])
            case "gui":
                # Set the GUI mode
                print_debug(f"Setting GUI mode to {value}")
                parameters.set("gui", value, ["app", "enabled"])
            case "verbosity":
                # Set the verbosity level
                print_info(f"Setting verbosity level to '{value}'")
                parameters.set("verbosity_level", value, ["log"])
            case "dry_run":
                # Set dry run mode
                print_debug(f"Setting dry run mode to '{value}'")
                parameters.set("dry_run", value, ["app", "enabled"])
            case "target_ip":
                # Set the target IP address
                print_debug(f"Setting target IP to '{value}'")
                parameters.set("target_ip", value, ["attack"])
            case "target_port":
                # Set the target port
                print_debug(f"Setting target port to '{value}'")
                parameters.set("target_port", value, ["attack"])
            case "attack_name":
                # Set the attack name
                print_debug(f"Setting attack name to '{value}' and enabling attack mode")
                parameters.set("attack_name", value, ["attack"])
                parameters.set("attack", True, ["app", "enabled"])

            case "spoofing_enabled":
                # Set spoofing enabled/disabled
                print_debug(f"Setting spoofing enabled to '{value}'")
                parameters.set("spoofing", value, ["app", "enabled"])
            case "return_path_enabled":
                # Set return path enabled/disabled
                print_debug(f"Setting return path enabled to '{value}'")
                parameters.set("return_path", value, ["app", "enabled"])
            case "log_file_on":
                # Set log file enabled/disabled
                print_debug(f"Setting log file enabled to '{value}'")
                parameters.set("log_file", value, ["app", "enabled"])
            case "metrics_on":
                # Set metrics enabled/disabled
                print_debug(f"Setting metrics enabled to '{value}'")
                parameters.set("metrics", value, ["app", "enabled"])
            case "log_file":
                # Set log file path
                if isinstance(value, str):
                    print_debug(f"Setting log file path to '{value}'")
                    parameters.set("file", value, ["log"])
            case "log_format":
                # Set log format
                if isinstance(value, str):
                    print_debug(f"Setting log format to '{value}'")
                    print_warning("Not implemented yet, will be set in the logger setup"
                                  "with simple format settings with simple letters like "
                                  "--log_format anlm for asctime, name, levelname and message")
                pass
            case "max_count":
                # Set maximum count for attacks
                if isinstance(value, int):
                    print_debug(f"Setting maximum count to '{value}'")
                    parameters.set("max_count", value, ["attack"])
                else:
                    print_warning(f"Unsupported type for max_count: {type(value)}. Expected int.")
            case "delay":
                # Set delay between packets for attacks
                if isinstance(value, (int, float)):
                    print_debug(f"Setting delay to '{value}' seconds")
                    parameters.set("delay", value, ["attack"])
                else:
                    print_warning(f"Unsupported type for delay: {type(value)}. Expected int or float.")
            case "open_window":
                # Set whether to open a new terminal window for the attack
                if isinstance(value, bool) :
                    print_debug(f"Setting open_window to '{value}' on attack, lab and metrics")
                    parameters.set("open_window", value, ["app", "enabled"])
                    parameters.set("open_window", value, ["attack"])
                    parameters.set("open_window", value, ["metrics"])
                    parameters.set("open_window", value, ["lab"])
                    
            case _:
                if value is not None:
                    # Set custom parameters
                    if isinstance(value, parameters.authorized_values):
                        print_debug(f"Setting custom parameter '{key}' to '{value}'")
                        parameters.set(key, value, ["custom"])
                    else:
                        print_warning(f"Unsupported type for custom parameter '{key}': {type(value)}")
                else:
                    print_warning(f"Skipping parameter '{key}' because its value is None")

    config.parameters = parameters
    print_debug(f"Updated config parameters: {config.parameters}")

def UpdateFlatConfig(config:Config, new_parameters: Parameters):
    print_debug(f"Old flat config parameters: {config.parameters}")
    for key, value in new_parameters.items():
        if key in config.parameters:
            config.parameters[key] = value
            print_debug(f"Updated flat config parameter '{key}' to '{value}'")
        else:
            print_warning(f"Unknown flat config parameter '{key}'")
    print_debug(f"Final flat config parameters: {config.parameters}")
    