"""
SIP Attack Module Interface
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Type

from utils.config.config import Parameters
from utils.attack.attack_enums import AttackProtocol, AttackType
import inspect

from utils.core.logs import print_debug, print_in_dev, print_warning
from utils.registry.metadata import ModuleInfo

class AttackInterface(ABC):
    # Module information for the registry
    infos : ModuleInfo  = ModuleInfo(
        description="StormShadow Template Attack Module",
        version="1.0.0",
        author="StormShadow",
        requirements=[],
        license="Educational Use Only"
    )
    
    def __init__(self, 
                 target_ip: str="127.0.0.1", # Target IP address for the attack
                 rate: int = 0, # Rate of the attack in requests per second (0 = unlimited)
                 delay: float = 0.0, # Delay between requests in seconds
                 target_port: int = 5060, # Target port for the attack
                 interface: str = "eth0", # Network interface to use
                 source_port: int = 0, # Source port for the attack (default 0 means random)
                 attack_queue_num: int = 1, # Queue number for the attack
                 max_count: int = 0, # Number of messages to send (0 = unlimited)
                 max_duration: int = 0, # Maximum duration in seconds (0 = unlimited)
                 user_agent: str = "StormShadow", # User agent string for the attack
                 spoofing_subnet: Optional[str] = None, # Subnet for IP spoofing if needed
                 custom_payload_path: Optional[Path] = None, # Custom payload file path
                 sip_users: List[int]=[],
                 open_window: bool = False): # List of SIP users to target

        self.attack_type : AttackType = AttackType.DDOS  # Default attack type, can be overridden
        self.attack_protocol : AttackProtocol = AttackProtocol.SIP  # Default protocol, can be overridden
        self.attack_name : str = self.__class__.__name__
        self.target_ip : str = target_ip
        self.target_port : int = target_port
        self.rate : int = rate
        self.delay : float = delay # Delay between requests in seconds
        self.sip_users : List[int] = sip_users # List of SIP users to target
        self.dry_run : bool = False  # Whether to run the attack in dry-run mode

        self.dry_run_implemented : bool = False  # Whether dry-run is implemented in the attack module
        self.resume_implemented : bool = False  # Whether resume is implemented in the attack module
        self.spoofing_implemented : bool = False  # Whether spoofing is implemented in the attack module

        self.interface : str = interface  # Network interface to use
        self.source_port : int = source_port  # Source port for the attack
        self.attack_queue_num : int = attack_queue_num  # Queue number for the attack
        self.max_count : int = max_count  # Number of messages to send (0 = unlimited)
        self.max_duration : int = max_duration  # Maximum duration in seconds (0 = unlimited)
        self.spoofing_subnet : Optional[str] = spoofing_subnet  # Subnet for IP spoofing
        self.user_agent : str = user_agent  # User agent string
        self.custom_payload_path : Optional[Path] = custom_payload_path  # Path to custom payload file
        self.open_window : bool = open_window  # Whether to open a new window for the attack

        self.debug_parameters()
    @abstractmethod
    def run(self):
        """Start the attack"""
        pass

    @abstractmethod
    def stop(self):
        """Stop the attack (default behavior: call cleanup)"""
        print(f"[INFO] Stopping attack on {self.target_ip}")
        # Ensure spoofer is stopped when attack is stopped
        if hasattr(self, 'spoofing_implemented') and self.spoofing_implemented:
            try:
                self.stop_spoofing()
            except Exception as e:
                print(f"[ERROR] Error stopping spoofer during stop: {e}")
        self.cleanup()

    def resume(self) -> bool:
        """Resume the attack if it was stopped"""
        print(f"[INFO] Resuming attack on {self.target_ip}")
        # Implement logic to resume the attack
        return False # If the attack cannot be resumed, return False

    def end(self):
        """End the attack (default behavior: call cleanup)"""
        print(f"[INFO] Ending attack on {self.target_ip}")
        # Ensure spoofer is stopped before cleanup
        if hasattr(self, 'spoofing_implemented') and self.spoofing_implemented:
            try:
                self.stop_spoofing()
            except Exception as e:
                print(f"[ERROR] Error stopping spoofer during end: {e}")
        self.cleanup()

    @abstractmethod
    def cleanup(self):
        """Default cleanup (optional override)"""
        print("[INFO] Default cleanup called (no specific cleanup implemented)")

    @abstractmethod
    def get_attack_description(self) -> str:
        """Return a description of the attack"""
        pass

    def load_config(self, params: Parameters):
        """Load parameters for the attack"""
        print("[INFO] Loading parameters for SIP attack")
        self.target_ip = params.get("target_ip", self.target_ip)
        self.target_port = params.get("target_port", self.target_port)
        self.rate = params.get("rate", self.rate)
        self.delay = params.get("delay", self.delay)

        # Handle sip_user (string) or sip_users (list)
        if "sip_user" in params:
            sip_user = params.get("sip_user")
            if isinstance(sip_user, str):
                self.sip_users = [int(sip_user)]
            elif isinstance(sip_user, int):
                self.sip_users = [sip_user]
        else:
            self.sip_users = params.get("sip_users", self.sip_users)

    def get_attack_type(self) -> AttackType:
        """Return the type of attack"""
        return self.attack_type

    def get_attack_name(self) -> str:
        """Return the name of the attack"""
        return self.attack_name

    def debug_parameters(self):
        """Print the current parameters for debugging purposes."""
        print_in_dev(f"Debugging parameters for {self.attack_name}:")
        print_debug(f"Debugging parameters for {self.attack_name}:")
        for key, value in self.__dict__.items():
            print_debug(f"  {key}: {value}")

    def start_spoofing(self) -> bool:
        """
        Implement spoofing logic for the attack if needed.
        
        Returns:
            bool: True if spoofing is successfully set up, False otherwise.
        """
        print_warning("Spoofing not implemented in this attack module.")
        return False
    
    def stop_spoofing(self) -> bool:
        """
        Stop spoofing if it is implemented in the attack module.
        
        Returns:
            bool: True if spoofing was stopped successfully, False otherwise.
        """
        print_warning("Stopping spoofing not implemented in this attack module.")
        return False

    # ---- Session wiring helpers ----
    def set_session_uid(self, suid: str) -> None:
        """Attach a StormShadow Session Unique ID to the attack instance."""
        self.session_uid = suid

def get_init_args(cls : Type[AttackInterface]) -> List[str]:
    signature = inspect.signature(cls.__init__)
    # Exclude 'self' and get argument names
    return [param.name for param in signature.parameters.values() if param.name != "self"]

def create_attack_instance(
    attack_class: Type[AttackInterface],
    params: Optional[Parameters] = None,
) -> AttackInterface:
    """
    Create an instance of the attack class with the given arguments.

    Args:
        attack_class: The attack class to instantiate.
        params: Parameters to pass to the attack class constructor.

    Returns:
        An instance of the attack class.
    """
    # Flatten the parameters if they are provided
    if params:
        given_args = params.flatten()
    else:
        given_args = {}
    params_to_remove = ["attack_name", "attack_type", "attack_protocol", "name"]

    for param in params_to_remove:
        given_args.pop(param, None)

    # Ensure all required arguments are present
    required_args = get_init_args(attack_class)

    missing_args : List[str] = []
    for arg in required_args:
        if arg not in given_args:
            missing_args.append(arg)

    if missing_args:
        print_warning(f"Missing required arguments for {attack_class.__name__}: {missing_args}")
        print_warning("Using default values for missing arguments")

    return attack_class(**given_args)
