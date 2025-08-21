"""
System utilities for StormShadow.

This module provides system-level utility functions including:
- Root permission checking
- Network interface and IP management
- Service availability checking
- Process management
- Logging setup
"""

import os
from subprocess import CalledProcessError, run
from typing import Optional, Dict
from pathlib import Path
import netifaces

from .logs import print_warning

def get_project_root() -> Path:
    """
    Get the root directory of the StormShadow project.
    
    Returns:
        Path: The absolute path to the project root directory
    """
    # Get the directory containing this file (/utils/core/)
    current_file = Path(__file__).resolve()
    
    # Go up two levels to get to the project root
    # /utils/core/system_utils.py -> /utils/ -> /project_root/
    project_root = current_file.parent.parent.parent
    
    return project_root


def check_root() -> bool:
    """
    Check if the current process is running with root privileges.

    Returns:
        bool: True if running as root, False otherwise
    """
    return os.geteuid() == 0

def get_interface() -> str:
    """Get the default network interface."""
    try:
        gateways = netifaces.gateways()
        
        # Look for the IPv4 gateway interface
        if netifaces.AF_INET in gateways:
            interfaces_with_gateway = gateways[netifaces.AF_INET]
            if interfaces_with_gateway:
                # Return the interface of the first gateway (usually the default route)
                return interfaces_with_gateway[0][1]
        
        # Fallback: find the first non-loopback interface with an IP
        for interface in netifaces.interfaces():
            if interface != 'lo':
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    return interface
                    
    except Exception:
        pass
    
    return "lo"

def get_interface_ip(interface: str) -> Optional[str]:
    """
    Get the IP address of a specific network interface.

    Args:
        interface: Network interface name (e.g., 'eth0', 'wlan0')

    Returns:
        Optional[str]: IP address of the interface or None if not found
    """
    try:
        if interface in netifaces.interfaces():
            addresses = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addresses:
                return addresses[netifaces.AF_INET][0]['addr']  # type: ignore
    except ImportError:
        # Fallback using ip command
        try:
            result = run(
                ['ip', 'addr', 'show', interface],
                capture_output=True,
                text=True,
                check=True
            )

            for line in result.stdout.split('\n'):
                if 'inet ' in line and 'scope global' in line:
                    ip = line.strip().split()[1].split('/')[0]
                    return ip
        except (CalledProcessError, IndexError):
            pass

    except Exception as e:
        print_warning(f"Error getting IP for {interface}. Falling back to localhost IP: {e}")

    return "127.0.0.1"  # Fallback to localhost if interface not found

def get_default_ip() -> str:
    """
    Get the default IP address for the system.
    
    Returns:
        str: The IP address of the default network interface
    """
    try:
        default_interface = get_interface()
        default_ip = get_interface_ip(default_interface)
        return default_ip if default_ip else "127.0.0.1"
    except Exception as e:
        print_warning(f"Error getting default IP: {e}")
        return "127.0.0.1"


def get_system_info() -> Dict[str, str]:
    """
    Get system information.

    Returns:
        Dict[str, str]: System information dictionary
    """
    import platform

    info: Dict[str, str] = {
        'platform': str(platform.platform()),
        'system': str(platform.system()),
        'release': str(platform.release()),
        'version': str(platform.version()),
        'machine': str(platform.machine()),
        'processor': str(platform.processor()),
        'python_version': str(platform.python_version()),
        'is_root': str(check_root()),
        'local_ip': str(get_interface_ip(get_interface()))
    }

    return info
