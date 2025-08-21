"""
Attack-related enumerations for the SIP attack framework.
"""

from enum import Enum

class AttackProtocol(Enum):
    SIP = "SIP"
    ICMP = "ICMP"
    HTTP = "HTTP"
    TEMPLATE = "TEMPLATE"  # For template attacks that can be customized

class AttackStatus(Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    COMPLETED = "completed"

class AttackType(Enum):
    DOS = "DOS"
    DDOS = "DDOS"
    EXPLOIT = "EXPLOIT"
    SCAN = "SCAN"  # To know the vulnerabilities of the target
    BRUTE_FORCE = "BRUTE_FORCE"
    TEMPLATE = "TEMPLATE"  # For template attacks that can be customized
