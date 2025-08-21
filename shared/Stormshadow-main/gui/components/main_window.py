"""
Main Window Component

This module provides the main window interface for the StormShadow GUI application.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from gui.components.attack_panel import AttackPanel
from gui.components.lab_panel import LabPanel
from gui.components.status_panel import StatusPanel
from gui.components.menu_bar import MenuBar
from gui.utils.themes import apply_modern_theme
from gui.managers.gui_storm_manager import GUIStormManager


class MainWindow:
    """Main window class for the StormShadow GUI."""

    def __init__(self, root: tk.Tk, gui_manager: GUIStormManager):
        """
        Initialize the main window.

        Args:
            root: The root Tkinter window
            gui_manager: The GUI storm manager instance
        """
        self.root = root
        self.gui_manager = gui_manager

        # Apply modern theme
        apply_modern_theme(self.root)

        # Create the menu bar
        self.menu_bar = MenuBar(self.root, self)

        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create panels
        self._create_panels()

        # Register for status updates
        self.gui_manager.register_status_callback("main_window", self._on_status_update)

    def _create_panels(self):
        """Create all the GUI panels."""
        # Attack Panel
        self.attack_frame = ttk.Frame(self.notebook)
        self.attack_panel = AttackPanel(self.attack_frame, self.gui_manager)
        self.notebook.add(self.attack_frame, text="🎯 SIP Attacks", padding=10)

        # Lab Panel
        self.lab_frame = ttk.Frame(self.notebook)
        self.lab_panel = LabPanel(self.lab_frame, self.gui_manager)
        self.notebook.add(self.lab_frame, text="🧪 Lab Environment", padding=10)

        # Status Panel
        self.status_frame = ttk.Frame(self.notebook)
        self.status_panel = StatusPanel(self.status_frame, self.gui_manager)
        self.notebook.add(self.status_frame, text="📊 Status & Logs", padding=10)

    def _on_status_update(self, instance_name: str, status: str):
        """
        Handle status updates from the GUI manager.

        Args:
            instance_name: Name of the instance that changed status
            status: New status
        """
        # Update the status panel
        if hasattr(self, 'status_panel'):
            self.status_panel.update_status(instance_name, status)

    def show_about_dialog(self):
        """Show the about dialog."""
        about_text = """StormShadow SIP-Only GUI

A modern interface for SIP security testing and lab management.

Version: 1.0.0
Author: Corentin COUSTY
License: Educational Use Only

This tool is designed for educational and authorized testing purposes only.
Use responsibly and only on systems you own or have explicit permission to test.
        """
        messagebox.showinfo("About StormShadow", about_text)

    def show_help_dialog(self):
        """Show the help dialog."""
        help_text = """StormShadow SIP-Only GUI - Help

🎯 SIP Attacks Tab:
- Select an attack module from the dropdown
- Configure target IP and port
- Set attack parameters (packet count, spoofing, etc.)
- Start/stop attacks with real-time monitoring

🧪 Lab Environment Tab:
- Start/stop the SIP lab Docker container
- Configure lab parameters
- Monitor lab status

📊 Status & Logs Tab:
- View real-time status of all running instances
- Monitor log output from attacks and lab
- Track system resources and performance

💡 Tips:
- Use the lab environment to test attacks safely
- Always verify target permissions before testing
- Monitor system resources during attacks
- Check logs for troubleshooting information
        """
        messagebox.showinfo("Help", help_text)

    def cleanup(self):
        """Clean up the main window resources."""
        # Unregister status callback
        self.gui_manager.unregister_status_callback("main_window")

        # Clean up panels
        if hasattr(self, 'attack_panel'):
            self.attack_panel.cleanup()
        if hasattr(self, 'lab_panel'):
            self.lab_panel.cleanup()
        if hasattr(self, 'status_panel'):
            self.status_panel.cleanup()
