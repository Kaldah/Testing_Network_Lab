#!/usr/bin/env python3
"""
StormShadow SIP-Only GUI Application

A modern Tkinter-based GUI for the StormShadow SIP testing toolkit.
Provides an intuitive interface for running SIP attacks and managing lab environments.

Author: Corentin COUSTY
License: Educational Use Only
"""

from gui.managers.gui_storm_manager import GUIStormManager
from gui.components.main_window import MainWindow
from utils.core.logs import print_info, print_error, print_success
from utils.config.config import Parameters
import sys
import tkinter as tk
from pathlib import Path
from typing import Optional

# Add the parent directory to sys.path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))


class StormShadowGUI:
    """Main GUI application class for StormShadow."""

    def __init__(self, cli_args: Optional[Parameters] = None, config_path: Optional[Path] = None):
        """Initialize the GUI application.

        Args:
            cli_args: Command line arguments as Parameters object
            config_path: Path to configuration file
        """
        print_info("Initializing StormShadow GUI...")

        # Store configuration for later use
        self.cli_args = cli_args or Parameters()
        self.config_path = config_path
        # Note: Don't create a separate StormShadow instance here
        # The GUI manager will handle all StormShadow instances
        self.stormshadow = None

        # Create the main Tkinter root window
        self.root = tk.Tk()
        self.root.title("StormShadow SIP-Only")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        # Set up the application icon if available
        try:
            # You can add an icon file later
            # self.root.iconbitmap("path/to/icon.ico")
            pass
        except Exception:
            pass

        # Initialize the GUI storm manager (this handles all StormShadow instances)
        self.gui_manager = GUIStormManager()
        print_info(f"GUI session will use shared SUID: {self.gui_manager.get_shared_suid()}")

        # Create the main window components
        self.main_window = MainWindow(self.root, self.gui_manager)

        # Configure window closing behavior
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        print_success("StormShadow GUI initialized successfully")

    def run(self):
        """Start the GUI application."""
        try:
            print_info("Starting StormShadow GUI...")
            self.root.mainloop()
        except KeyboardInterrupt:
            print_info("GUI interrupted by user")
        except Exception as e:
            print_error(f"GUI error: {e}")
        finally:
            self._on_closing()

    def _on_closing(self):
        """Handle application closing."""
        if hasattr(self, '_closed'):
            return  # Already closed

        print_info("Closing StormShadow GUI...")
        self._closed = True

        try:
            # Clean up GUI Storm Manager (this handles all StormShadow instances)
            if hasattr(self, 'gui_manager'):
                print_info("Cleaning up GUI Storm Manager...")
                self.gui_manager.cleanup()
                print_success("GUI Storm Manager cleanup completed")
        except Exception as e:
            print_error(f"Error during GUI manager cleanup: {e}")

        try:
            # Destroy the root window if it still exists
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.destroy()
        except Exception as e:
            print_error(f"Error during window destruction: {e}")

        print_success("StormShadow GUI closed")


def main():
    """Main entry point for the GUI application."""
    try:
        # Create and run the GUI application
        app = StormShadowGUI()
        app.run()
        return 0
    except KeyboardInterrupt:
        print_info("GUI application interrupted by user")
        return 0
    except Exception as e:
        print_error(f"Failed to start GUI application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
