from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType
from typing import Optional, Type

from utils.config.config import Parameters
from utils.core.logs import print_debug, print_error, print_in_dev, print_info, print_success, print_warning
from utils.interfaces.attack_interface import AttackInterface, create_attack_instance
from utils.attack.attack_enums import AttackProtocol, AttackStatus, AttackType
from utils.attack.attack_modules_finder import find_attack_main_class, check_attack_module_structure
from utils.network.iptables import generate_suid, remove_rules_for_suid


class AttackSession:
    """
    Base class for all attack modules.
    """

    def __init__(self, name: str, main_attack: AttackInterface, enable_spoofing: bool, session_uid: Optional[str] = None, dry_run: bool = False) -> None:
        self.name = name
        self.protocol = AttackProtocol.SIP

        self.main_attack : AttackInterface = main_attack  # Instance of the attack interface
        self.dry_run = dry_run  # Whether dry run is enabled or not
        self.status = AttackStatus.INITIALIZED  # Status of the attack module
        self.enable_spoofing = enable_spoofing  # Whether spoofing is enabled or not

        # Use provided session UID or generate our own
        self.suid: str = session_uid or generate_suid()
        self.main_attack.set_session_uid(self.suid)
        self.is_resumable = self.main_attack.resume_implemented  # Whether the attack module can be resumed or not
        self.use_default_spoofing = not self.main_attack.spoofing_implemented  # Whether to use default spoofing or module spoofing

    def start(self) -> None:
        """
        Start the attack.
        """
        
        print_info(f"Starting attack: {self.name}")
        self.status = AttackStatus.RUNNING
        # Implement logic to start the attack

        if self.dry_run:
            if self.enable_spoofing:
                print_info("Spoofing is enabled, spoofing would be started.")
            print_info("Running in dry-run mode, no actual attack will be performed.")
            if not self.main_attack.dry_run_implemented:
                print_warning("Dry-run mode is not implemented for this attack module\nModule content not available in dry-run.")
                return
            else:
                print_info(f"Dry-run mode is implemented, proceeding with dry-run for {self.name}.")
                self.main_attack.dry_run = True
        if self.enable_spoofing:
            print_info("Spoofing is enabled, starting spoofing...")
            if self.use_default_spoofing:
                print_info("Using default spoofing...")
                print_in_dev("Default spoofing not implemented yet, using module spoofing instead.")
                self.main_attack.start_spoofing()
            else:
                print_info("Using attack module own spoofing...")
                self.main_attack.start_spoofing()
        self.main_attack.run()
        print_success(f"Attack {self.name} started successfully.")

    def stop(self) -> None:
        """
        Stop the attack.
        """
        print_info(f"Stopping attack: {self.name}")
        # Implement logic to stop the attack
        try:
            if self.dry_run:
                if not self.main_attack.dry_run_implemented:
                    if self.enable_spoofing:
                        print_info("Spoofing is enabled, spoofing would be stopped.")
                    print_info("Dry-run mode is enabled, no actual attack will be stopped.")
                    return
                else:
                    print_info("Dry-run mode is implemented, proceeding with stopping the (fake) attack.")
            
            # Stop spoofing FIRST before stopping the main attack
            # This ensures spoofer processes are properly terminated
            if self.enable_spoofing:
                print_info("Stopping spoofing...")
                try:
                    if self.use_default_spoofing:
                        print_in_dev("Default spoofing not implemented yet, stopping module spoofing.")
                        self.main_attack.stop_spoofing()
                    else:
                        self.main_attack.stop_spoofing()
                    print_success("Spoofing stopped successfully.")
                except Exception as e:
                    print_error(f"Error stopping spoofing: {e}")
            
            # Now stop the main attack
            self.main_attack.stop()
            self.status = AttackStatus.STOPPED
            print_info(f"Attack {self.name} stopped successfully.")
            
            # Best-effort cleanup of any rules with this session SUID
            try:
                remove_rules_for_suid(self.suid, dry_run=self.dry_run)
                remove_rules_for_suid(self.suid, table="nat", dry_run=self.dry_run)
            except Exception:
                pass
        except Exception as e:
            print_error(f"Error stopping attack {self.name}: {e}")

    def resume(self) -> None:
        """
        Resume the attack if it was stopped.
        """
        print_info(f"Resuming attack: {self.name}")

        if self.main_attack.dry_run:
            if not self.main_attack.dry_run_implemented:
                print_warning("Dry-run mode is enabled, no actual attack will be resumed.")
                return
            else:
                print_info("Dry-run mode is implemented, proceeding with resuming the (fake) attack.")

        try :
            if self.main_attack.resume_implemented:
                self.status = AttackStatus.RUNNING
                print_info(f"Resuming attack {self.name}...")
                self.main_attack.resume()
                print_info(f"Attack {self.name} resumed successfully.")
            else:
                print_warning(f"Attack {self.name} cannot be resumed, it was not implemented in the attack module.")
        except Exception as e:
            print_error(f"Error resuming attack {self.name}: {e}")
            self.status = AttackStatus.FAILED
            print_error(f"Trying to clean up after failed resume of attack {self.name}.")
            self.main_attack.cleanup()
    
    def cleanup(self) -> None:
        """
        Cleanup resources used by the attack.
        """
        print_info(f"Cleaning up attack: {self.name}")
        # Implement logic to clean up resources
        pass
    def get_status(self) -> AttackStatus:
        """
        Get the status of the attack module.
        """
        return self.status

    def get_name(self) -> str:
        """
        Get the name of the attack module.
        """
        return self.name

    def get_type(self) -> AttackType:
        """
        Get the type of the attack module.
        """
        return self.main_attack.get_attack_type()

def load_main_attack(py_file: Path) -> Optional[Type[AttackInterface]]:
    """
    Load the main attack class from a specific file, after validating the module structure.
    
    Args:
        module: Path to the attack module.
    
    Returns:
        An instance of the attack module.
    """
    print_debug(f"Trying to load attack module from {py_file}")
    # Ensure the directory structure is valid before importing
    module_dir = py_file.parent
    if not check_attack_module_structure(module_dir):
        print_warning(f"Module directory failed structure validation: {module_dir}")
        return None
    try:
        spec = spec_from_file_location("attack_module", str(py_file))
        if spec is None:
            print_debug(f"Failed to load attack module from {py_file}: Spec is None")
            return None
        # Dynamically load the module
        attack_module : ModuleType = module_from_spec(spec)
        # Verify if the module has the required interface
        if spec.loader is None:
            print_debug(f"Failed to load attack module from {py_file}: Loader is None")
            return None
        # Load all classes, functions and variables from the module
        print_debug(f"Loading attack module from {py_file}")
        spec.loader.exec_module(attack_module)

        # Look for the main attack class implementing the AttackInterface
        print_debug(f"Looking for main attack class in {py_file}")
        main_attack_class: Optional[Type[AttackInterface]] = find_attack_main_class(attack_module)

        if main_attack_class is None:
            print_warning(f"No valid attack class found in {py_file}")
            return None
        print_info(f"Successfully loaded attack module: {py_file}")
        return main_attack_class

    except Exception as e:
        print_debug(f"Failed to import attack module from {py_file} : {e}")
        return None

def build_attack_from_module(module: Path, attack_params: Parameters, enable_spoofing: bool, session_uid: Optional[str] = None, open_window: bool = False, dry_run: bool = False) -> Optional[AttackSession]:
    """
    Build an attack instance from a module path.
    
    Args:
        module: Path to the attack module.
        attack_params: Parameters for the attack instance.
        enable_spoofing: Whether to enable spoofing for this attack
        session_uid: Session unique ID to use for this attack
        open_window: Whether to open a window for this attack
        dry_run: Whether to run in dry-run mode

    Returns:
        An instance of the attack module.
    """

    print_debug(f"Creating attack session from module: {module}")

    if not module.exists():
        print_error(f"Module path does not exist: {module}")
        raise FileNotFoundError(f"Module path does not exist: {module}")
    
    if not module.is_dir():
        print_error(f"Module path is not a directory: {module}")
        raise NotADirectoryError(f"Module path is not a directory: {module}")
    
    # Load the module dynamically
    try:
        main_attack_class: Optional[Type[AttackInterface]] = None
        print_debug(f"Loading attack module from path: {module}")
        print_debug(f"module contents: {list(module.glob('*.py'))}")
        for py_file in module.glob("*.py"):
            found_class = load_main_attack(py_file)
            if found_class is None:
                print_debug(f"No valid attack class found in {py_file}, skipping.")
            else:
                print_debug(f"Found valid attack class in {py_file}: {found_class.__name__}")
                main_attack_class = found_class
                break
                
        if main_attack_class is None:
            print_error(f"No valid attack module found in {module}")
            raise ImportError(f"No valid attack module found in {module}")
        
        # Create an instance of the attack using the class
        main_attack = create_attack_instance(main_attack_class, attack_params)
        
        # Set the session UID on the attack instance
        if session_uid and hasattr(main_attack, 'set_session_uid'):
            main_attack.set_session_uid(session_uid)
        
        # Create an instance of the attack session
        attack_session = AttackSession(name=main_attack.attack_name, main_attack=main_attack, enable_spoofing=enable_spoofing, session_uid=session_uid, dry_run=dry_run)
        print_info(f"Attack session created successfully: {attack_session.get_name()}")
        return attack_session
    except ImportError as e:
        print_error(f"Error importing attack module. No valid attack module found in {module}: {e}")
        return None