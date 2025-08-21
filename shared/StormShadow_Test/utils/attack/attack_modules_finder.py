from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType
from typing import Dict, Optional, Type

from utils.core.logs import print_debug, print_in_dev, print_warning
from utils.interfaces.attack_interface import AttackInterface

def find_attack_main_class(module: ModuleType) -> Optional[Type[AttackInterface]]:
    """
    Find the main attack class in the given module.

    Args:
        module: The module to search for the attack class.

    Returns:
        The first class found that implements AttackInterface, or None if not found.
    """
    print_debug("Searching for attack class in module...")
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, AttackInterface) and attr is not AttackInterface:
            print_debug(f"Found attack class: {attr_name}")
            return attr  # This is the class with the AttackInterface implementation
    
    print_debug("No attack class found in module.")
    return None

def check_attack_module_structure(module_path: Path) -> bool:
    """
    Check if the attack module has the required structure.

    Args:
        module_path: Path to the attack module directory.

    Returns:
        True if the module has the required structure, False otherwise.
    """
    # Check if the module path is a directory
    if not module_path.exists():
        print_warning(f"Module path does not exist: {module_path}")
        return False
    if not module_path.is_dir():
        print_debug(f"Module path is not a directory: {module_path}")
        return False
    # Check if there is a file implementing the AttackInterface
    if not any(module_path.glob("*.py")):
        print_warning(f"No Python files found in module path: {module_path}")
        return False
    # Check if the module has at least one valid AttackInterface implementation by
    # attempting a safe dynamic import (same mechanism used at runtime)
    found_valid = False
    for py_file in module_path.glob("*.py"):
        try:
            print_debug(f"Validating attack file: {py_file}")
            spec = spec_from_file_location(f"attack_module_check_{py_file.stem}", str(py_file))
            if spec is None or spec.loader is None:
                print_warning(f"Unable to create import spec for: {py_file}")
                continue
            tmp_module: ModuleType = module_from_spec(spec)
            spec.loader.exec_module(tmp_module)
            if find_attack_main_class(tmp_module):
                found_valid = True
                break
            else:
                print_debug(f"File does not define a valid AttackInterface class: {py_file}")
        except Exception as e:
            # If a specific file fails to import, log and continue checking others
            print_warning(f"Error validating attack file {py_file}: {e}")
            continue
    if not found_valid:
        print_warning(f"No valid attack class found in any file under: {module_path}")
    return found_valid

def find_attack_modules(attack_modules_folder: Path) -> Dict[str,Path]:
    """
    Discover and return a list of available attack modules.

    Returns:
        A list of Path objects representing the paths to available attack modules folders.
    """
    print_debug(f"Searching for attack modules in: {attack_modules_folder}")
    if not attack_modules_folder.exists() or not attack_modules_folder.is_dir():
        print_warning(f"Attack modules folder does not exist or is not a directory: {attack_modules_folder}")
        return {}
    print_debug(f"Found attack modules folder: {attack_modules_folder}")
    # List all directories in the attack modules folder
    print_debug("Listing all directories in the attack modules folder...")

    attack_modules : Dict[str, Path] = {module.name: module for module in attack_modules_folder.iterdir() if check_attack_module_structure(module)}
    print_in_dev(f"Found attack modules: {list(attack_modules.keys())}")
    return attack_modules
