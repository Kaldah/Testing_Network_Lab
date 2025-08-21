"""
Printing utilities for StormShadow.

This module provides colored printing functions for different message types.
"""

import sys
from typing import Any


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'  # End color


def _supports_color() -> bool:
    """
    Check if the terminal supports color output.

    Returns:
        bool: True if terminal supports color
    """
    return (
        hasattr(sys.stdout, 'isatty') and
        sys.stdout.isatty() and
        sys.platform != 'win32'
    )


def _colorize(text: str, color: str) -> str:
    """
    Apply color to text if terminal supports it.

    Args:
        text: Text to colorize
        color: ANSI color code

    Returns:
        str: Colorized text or plain text
    """
    if _supports_color():
        return f"{color}{text}{Colors.END}"
    return text


def print_success(message: Any, **kwargs: Any) -> None:
    """
    Print a success message in green.

    Args:
        message: Message to print
        **kwargs: Additional arguments for print()
    """
    colored_message = _colorize(f"✓ {message}", Colors.GREEN)
    print(colored_message, **kwargs)


def print_error(message: Any, **kwargs: Any) -> None:
    """
    Print an error message in red.

    Args:
        message: Message to print
        **kwargs: Additional arguments for print()
    """
    colored_message = _colorize(f"✗ {message}", Colors.RED)
    print(colored_message, file=sys.stderr, **kwargs)


def print_warning(message: Any, **kwargs: Any) -> None:
    """
    Print a warning message in yellow.

    Args:
        message: Message to print
        **kwargs: Additional arguments for print()
    """
    colored_message = _colorize(f"⚠ {message}", Colors.YELLOW)
    print(colored_message, **kwargs)


def print_info(message: Any, **kwargs: Any) -> None:
    """
    Print an info message in blue.

    Args:
        message: Message to print
        **kwargs: Additional arguments for print()
    """
    colored_message = _colorize(f"ℹ {message}", Colors.BLUE)
    print(colored_message, **kwargs)


def print_debug(message: Any, **kwargs: Any) -> None:
    """
    Print a debug message in magenta.

    Args:
        message: Message to print
        **kwargs: Additional arguments for print()
    """
    colored_message = _colorize(f"🐛 {message}", Colors.MAGENTA)
    print(colored_message, **kwargs)

def print_in_dev(message: Any, **kwargs: Any) -> None:
    """
    Print a message indicating that the feature is not available in the current environment.

    Args:
        message: Message to print
        **kwargs: Additional arguments for print()
    """
    colored_message = _colorize(f"== IN DEV ==\n⚠ {message}\n" + "="*30, Colors.YELLOW)
    colored_message = f"{Colors.YELLOW}{Colors.BOLD}{colored_message}{Colors.END}"
    print(colored_message, file=sys.stderr, **kwargs)

def print_header(message: Any, **kwargs: Any) -> None:
    """
    Print a header message in bold cyan.

    Args:
        message: Message to print
        **kwargs: Additional arguments for print()
    """
    colored_message = _colorize(f"{message}", f"{Colors.BOLD}{Colors.CYAN}")
    print(colored_message, **kwargs)


def print_separator(char: str = "=", length: int = 60) -> None:
    """
    Print a separator line.

    Args:
        char: Character to use for separator
        length: Length of separator line
    """
    print(char * length)
