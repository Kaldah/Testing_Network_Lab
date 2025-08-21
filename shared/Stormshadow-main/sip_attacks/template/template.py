

from typing import List, Optional
from pathlib import Path
from utils.attack.attack_enums import AttackProtocol, AttackType
from utils.core.logs import print_info, print_error
from utils.interfaces.attack_interface import AttackInterface

from utils.registry.metadata import ModuleInfo

class TemplateAttack(AttackInterface):
    # Module information for the registry
    infos : ModuleInfo  = ModuleInfo(
        description="StormShadow Template Attack Module",
        version="1.0.0",
        author="StormShadow",
        requirements=[],
        license="Educational Use Only"
    )

    def __init__(self, 
                 target_ip: str = "127.0.0.1",
                 rate: int = 0,
                 delay: float = 0.0,
                 target_port: int = 5060,
                 interface: str = "eth0",
                 source_port: int = 0,
                 attack_queue_num: int = 1,
                 max_count: int = 0,
                 max_duration: int = 0,
                 user_agent: str = "StormShadow",
                 spoofing_subnet: Optional[str] = None,
                 custom_payload_path: Optional[Path] = None,
                 sip_users: List[int] = []) -> None:
        """Initialize the attack with parameters."""
 
        # Call the parent class constructor
        super().__init__(
            target_ip=target_ip,
            rate=rate,
            delay=delay,
            target_port=target_port,
            interface=interface,
            source_port=source_port,
            attack_queue_num=attack_queue_num,
            max_count=max_count,
            max_duration=max_duration,
            user_agent=user_agent,
            spoofing_subnet=spoofing_subnet,
            custom_payload_path=custom_payload_path,
            sip_users=sip_users
        )
        self.attack_type = AttackType.TEMPLATE  # Set a specific attack type for this template
        self.attack_protocol = AttackProtocol.TEMPLATE  # Set a specific protocol for this template
        self.name = "TemplateAttack"
        self.dry_run_implemented = True  # Indicate that dry-run is implemented for this attack
        self.resume_implemented = True  # Indicate that resume is implemented for this
        self.debug_parameters()
        # Print the initialization message
        print_info(f"Template attack initialized with target: {target_ip}:{target_port}")

    def cleanup(self) -> None:
        print_info("Cleaning up template attack resources")
        # Stop spoofing if it was enabled
        if hasattr(self, 'spoofer') and self.spoofer:  # type: ignore
            print_info("Stopping spoofer as part of cleanup...")
            try:
                self.stop_spoofing()
            except Exception as e:
                print_error(f"Error stopping spoofer during cleanup: {e}")
        # Implement any other necessary cleanup logic here
    
    def end(self):
        print_info("Ending the template attack")
        print_info("Cleaning up resources used by the template attack")
        self.cleanup()

    def run(self) -> None:
        print_info("Running template attack")
        # Implement the attack logic here

    def stop(self) -> None:
        print_info("Stopping template attack")
        print_info("Ending the attack and cleanup resources by default")
        self.end()
    
    def get_attack_description(self) -> str:
        return "This is a template attack module for demonstration purposes." \
        "It can be extended to implement specific attack logic." \
        "It inherits from AttackInterface and implements the required methods."
    
    
