# utils/core/logging_utils.py

import logging
import os
import sys
from typing import Any, Optional


# ---------- Colors (reusing your palette) ----------
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def _supports_color(stream: Any) -> bool:
    """
    Check if the given stream supports ANSI color codes.
    On Windows, this requires colorama to be installed.
    """
    # Force color support when environment variable is set
    if os.environ.get("FORCE_COLOR") in ("1", "true", "yes"):
        return True
    
    # Disable colors when NO_COLOR is set
    if os.environ.get("NO_COLOR"):
        return False
    
    # Check if stream supports color
    return (
        hasattr(stream, "isatty")
        and stream.isatty()
        and os.environ.get("TERM") not in ("dumb", None)
    )


# ---------- Custom levels ----------
SUCCESS_LEVEL = 25
DEV_LEVEL = 15
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")
logging.addLevelName(DEV_LEVEL, "DEV")


# ---------- Custom Logger class ----------
class StormLogger(logging.Logger):
    """Custom Logger with additional success() and dev() methods."""
    
    def success(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Log a success message at SUCCESS_LEVEL (25)."""
        if self.isEnabledFor(SUCCESS_LEVEL):
            self._log(SUCCESS_LEVEL, msg, args, **kwargs)
    
    def dev(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """Log a development message at DEV_LEVEL (15)."""
        if self.isEnabledFor(DEV_LEVEL):
            self._log(DEV_LEVEL, msg, args, **kwargs)


# Set our custom logger as the default logger class
logging.setLoggerClass(StormLogger)


# ---------- Formatter with color & emoji ----------
class StormFormatter(logging.Formatter):
    EMOJI = {
        "DEBUG": "🐛",
        "DEV": "🧪",
        "INFO": "ℹ",
        "SUCCESS": "✓",
        "WARNING": "⚠",
        "ERROR": "✗",
        "CRITICAL": "💥",
    }
    COLOR = {
        "DEBUG": Colors.MAGENTA,
        "DEV": Colors.YELLOW,
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "CRITICAL": Colors.RED + Colors.BOLD,
    }

    def __init__(self, use_color: bool, for_file: bool = False):
        super().__init__(fmt="%(message)s")
        # Never use color in file output
        self.use_color = use_color and not for_file

    def format(self, record: logging.LogRecord) -> str:
        # Prefix with emoji + message
        levelname = record.levelname
        emoji = self.EMOJI.get(levelname, "")
        base = f"{emoji} {record.getMessage()}"

        # Optional header style used by print_in_dev
        if levelname == "DEV" and "IN_DEV_BLOCK" in record.__dict__ and record.__dict__["IN_DEV_BLOCK"]:
            base = f"== IN DEV ==\n⚠ {record.getMessage()}\n" + "=" * 30

        # Apply colors if supported and enabled
        if self.use_color:
            color = self.COLOR.get(levelname, "")
            if color:
                # Make sure we're properly embedding the color codes
                return f"{color}{base}{Colors.END}"
        
        # No color formatting
        return base


# ---------- Setup ----------
def setup_logging(
    *,
    name: str = "stormshadow",
    verbosity: str | int = "info",
    logfile: Optional[str] = None,
    use_colors: Optional[bool] = True,  # Default to True to force color output
) -> StormLogger:
    """
    Create/configure a logger once (idempotent).
    - verbosity: "debug"|"dev"|"info"|"success"|"warning"|"error" or numeric level
    - logfile: optional path to write plain-text logs
    
    Default level is INFO (20) which includes: ERROR (40), WARNING (30), SUCCESS (25), INFO (20)
    but excludes: DEBUG (10), DEV (15)
    """
    logger = logging.getLogger(name)
    # Ensure we got our custom logger class
    assert isinstance(logger, StormLogger), f"Expected StormLogger, got {type(logger)}"
    
    if getattr(logger, "_storm_is_configured", False):
        return logger

    # Level mapping with better defaults
    if isinstance(verbosity, str):
        v = verbosity.lower()
        level_map = {
            "debug": logging.DEBUG,        # 10 - shows everything
            "dev": DEV_LEVEL,             # 15 - shows dev + info + warning + error + success
            "info": logging.INFO,         # 20 - shows info + warning + error + success (DEFAULT)
            "success": SUCCESS_LEVEL,     # 25 - shows success + warning + error
            "warning": logging.WARNING,   # 30 - shows warning + error
            "error": logging.ERROR,       # 40 - shows only error
            "critical": logging.CRITICAL, # 50 - shows only critical
        }
        level = level_map.get(v, logging.INFO)
    else:
        level = int(verbosity)

    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler(stream=sys.stdout)
    # Force colors if explicitly requested
    console_colors = _supports_color(sys.stdout) if use_colors is None else use_colors
    ch.setFormatter(StormFormatter(use_color=console_colors))
    ch.setLevel(level)
    logger.addHandler(ch)

    # File handler (no color)
    if logfile:
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(StormFormatter(use_color=False, for_file=True))
        fh.setLevel(level)
        logger.addHandler(fh)

    # Store the configured color setting for later reference
    logger.use_color = console_colors  # type: ignore[attr-defined]
    logger._storm_is_configured = True  # type: ignore[attr-defined]
    return logger


# ---------- Compatibility layer (your existing API) ----------
_logger: StormLogger = setup_logging()

def enable_debug_mode():
    """Enable debug mode with colors."""
    set_verbosity("debug")

def set_verbosity(verbosity: str | int) -> None:
    """Set the verbosity level for logging."""
    global _logger
    # Clear the configuration flag to allow reconfiguration
    if hasattr(_logger, '_storm_is_configured'):
        delattr(_logger, '_storm_is_configured')
    
    # Remove existing handlers to avoid duplicates
    for handler in _logger.handlers.copy():
        _logger.removeHandler(handler)
        handler.close()
    
    _logger = setup_logging(verbosity=verbosity)

def setup_stormshadow_logging(verbosity: str = "info", log_file: Optional[str] = None) -> StormLogger:
    """
    Setup StormShadow logging with the specified verbosity and optional log file.
    
    Args:
        verbosity: Logging level ("debug", "dev", "info", "success", "warning", "error")
        log_file: Optional path to log file
        
    Returns:
        Configured StormLogger instance
    """
    return setup_logging(verbosity=verbosity, logfile=log_file)

def get_logger() -> StormLogger:
    """Get the configured StormLogger instance."""
    return _logger

def use_log_file(path: str) -> None:
    """Enable logging to a file."""
    setup_logging(logfile=path)

# ---------- Replacement functions for printing.py ----------
def print_success(message: Any, **kwargs: Any) -> None:
    """Print a success message (replaces printing.print_success)."""
    _logger.success(str(message))

def print_error(message: Any, **kwargs: Any) -> None:
    """Print an error message (replaces printing.print_error)."""
    _logger.error(str(message))

def print_warning(message: Any, **kwargs: Any) -> None:
    """Print a warning message (replaces printing.print_warning)."""
    _logger.warning(str(message))

def print_info(message: Any, **kwargs: Any) -> None:
    """Print an info message (replaces printing.print_info)."""
    _logger.info(str(message))

def print_debug(message: Any, **kwargs: Any) -> None:
    """Print a debug message (replaces printing.print_debug)."""
    _logger.debug(str(message))

def print_in_dev(message: Any, **kwargs: Any) -> None:
    """Print a development message (replaces printing.print_in_dev)."""
    _logger.dev(str(message), extra={"IN_DEV_BLOCK": True})

def print_header(message: Any, **kwargs: Any) -> None:
    """Print a header message (replaces printing.print_header)."""
    # Treat as info but bold cyan like before
    _logger.info(f"{Colors.BOLD}{Colors.CYAN}{message}{Colors.END}" if _supports_color(sys.stdout) else str(message))

def print_separator(char: str = "=", length: int = 60) -> None:
    """Print a separator line (replaces printing.print_separator)."""
    _logger.info(char * length)
