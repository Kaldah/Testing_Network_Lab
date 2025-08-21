from dataclasses import dataclass


@dataclass
class ModuleInfo:
    """
    Module information for the attack module registry.
    This dictionary should be defined in each attack module.
    """
    description: str
    version: str
    author: str
    requirements: list[str]
    license: str