"""
Menu Bar Component

This module provides the menu bar for the StormShadow GUI application.
"""

import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.components.main_window import MainWindow


class MenuBar:
    """Menu bar class for the StormShadow GUI."""

    def __init__(self, root: tk.Tk, main_window: 'MainWindow'):
        """
        Initialize the menu bar.

        Args:
            root: The root Tkinter window
            main_window: Reference to the main window
        """
        self.root = root
        self.main_window = main_window

        # Create the menu bar
        self.menubar = tk.Menu(root, bg='#2b2b2b', fg='white',
                               activebackground='#404040', activeforeground='white')
        root.config(menu=self.menubar)

        self._create_file_menu()
        self._create_tools_menu()
        self._create_help_menu()

    def _create_file_menu(self):
        """Create the File menu."""
        file_menu = tk.Menu(self.menubar, tearoff=0, bg='#2b2b2b', fg='white',
                            activebackground='#404040', activeforeground='white')

        file_menu.add_command(label="New Configuration", command=self._new_config)
        file_menu.add_command(label="Load Configuration", command=self._load_config)
        file_menu.add_command(label="Save Configuration", command=self._save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Export Logs", command=self._export_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._exit_application)

        self.menubar.add_cascade(label="File", menu=file_menu)

    def _create_tools_menu(self):
        """Create the Tools menu."""
        tools_menu = tk.Menu(self.menubar, tearoff=0, bg='#2b2b2b', fg='white',
                             activebackground='#404040', activeforeground='white')

        tools_menu.add_command(label="Refresh Attack Modules", command=self._refresh_attacks)
        tools_menu.add_command(label="System Check", command=self._system_check)
        tools_menu.add_separator()
        tools_menu.add_command(label="Clear All Logs", command=self._clear_logs)
        tools_menu.add_command(label="Stop All Instances", command=self._stop_all)

        self.menubar.add_cascade(label="Tools", menu=tools_menu)

    def _create_help_menu(self):
        """Create the Help menu."""
        help_menu = tk.Menu(self.menubar, tearoff=0, bg='#2b2b2b', fg='white',
                            activebackground='#404040', activeforeground='white')

        help_menu.add_command(label="User Guide", command=self._show_user_guide)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.main_window.show_about_dialog)

        self.menubar.add_cascade(label="Help", menu=help_menu)

    def _new_config(self):
        """Create a new configuration."""
        messagebox.showinfo("New Configuration",
                            "This feature will be implemented in a future version.")

    def _load_config(self):
        """Load a configuration file."""
        messagebox.showinfo("Load Configuration",
                            "This feature will be implemented in a future version.")

    def _save_config(self):
        """Save the current configuration."""
        messagebox.showinfo("Save Configuration",
                            "This feature will be implemented in a future version.")

    def _export_logs(self):
        """Export logs to a file."""
        messagebox.showinfo("Export Logs",
                            "This feature will be implemented in a future version.")

    def _refresh_attacks(self):
        """Refresh the available attack modules."""
        try:
            # Refresh attack modules in the GUI manager
            # Use the public API to refresh available attacks
            self.main_window.gui_manager.discover_attacks()

            # Update attack panel if it exists
            if hasattr(self.main_window, 'attack_panel'):
                self.main_window.attack_panel.refresh_attacks()

            messagebox.showinfo("Success", "Attack modules refreshed successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh attack modules: {e}")

    def _system_check(self):
        """Perform a system check."""
        try:
            # Basic system checks
            checks: list[str] = []

            # Check if we can access attack modules
            attacks = self.main_window.gui_manager.get_available_attacks()
            checks.append(f"✓ Found {len(attacks)} attack modules")

            # Check for sudo access
            import os
            if os.geteuid() == 0:
                checks.append("✓ Running with root privileges")
            else:
                checks.append("⚠ Not running with root privileges (some features may be limited)")

            # Check for Docker
            try:
                from gui.utils.command_utils import get_command_version
                docker_version = get_command_version('docker')
                if docker_version:
                    checks.append(f"✓ Docker is available ({docker_version})")
                else:
                    checks.append("✗ Docker is not available")
            except Exception:
                checks.append("✗ Docker is not available")

            report = "System Check Report:\n\n" + "\n".join(checks)
            messagebox.showinfo("System Check", report)

        except Exception as e:
            messagebox.showerror("Error", f"System check failed: {e}")

    def _clear_logs(self):
        """Clear all logs."""
        try:
            if hasattr(self.main_window, 'status_panel'):
                self.main_window.status_panel.clear_logs()
            messagebox.showinfo("Success", "All logs cleared!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear logs: {e}")

    def _stop_all(self):
        """Stop all running instances."""
        try:
            instances = self.main_window.gui_manager.get_all_instances()
            stopped_count = 0

            for instance_name in instances:
                if instances[instance_name] == "running":
                    if self.main_window.gui_manager.stop_instance(instance_name):
                        stopped_count += 1

            if stopped_count > 0:
                messagebox.showinfo("Success", f"Stopped {stopped_count} running instances!")
            else:
                messagebox.showinfo("Info", "No running instances found.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop instances: {e}")

    def _show_user_guide(self):
        """Show the user guide."""
        self.main_window.show_help_dialog()

    def _show_shortcuts(self):
        """Show keyboard shortcuts."""
        shortcuts = """Keyboard Shortcuts:

Ctrl+N     - New Configuration
Ctrl+O     - Load Configuration
Ctrl+S     - Save Configuration
Ctrl+E     - Export Logs

F5         - Refresh Attack Modules
F9         - System Check
Ctrl+L     - Clear Logs
Ctrl+Q     - Stop All Instances

F1         - Help
Ctrl+?     - This shortcuts dialog

Tab        - Navigate between fields
Enter      - Execute focused button
Escape     - Cancel current operation
        """
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)

        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self._new_config())
        self.root.bind('<Control-o>', lambda e: self._load_config())
        self.root.bind('<Control-s>', lambda e: self._save_config())
        self.root.bind('<Control-e>', lambda e: self._export_logs())
        self.root.bind('<F5>', lambda e: self._refresh_attacks())
        self.root.bind('<F9>', lambda e: self._system_check())
        self.root.bind('<Control-l>', lambda e: self._clear_logs())
        self.root.bind('<Control-q>', lambda e: self._stop_all())
        self.root.bind('<F1>', lambda e: self._show_user_guide())
        self.root.bind('<Control-question>', lambda e: self._show_shortcuts())

    def _exit_application(self):
        """Exit the application."""
        # Check if there are running instances
        instances = self.main_window.gui_manager.get_all_instances()
        running_instances = [name for name, status in instances.items() if status == "running"]

        if running_instances:
            response = messagebox.askyesno(
                "Confirm Exit",
                f"There are {len(running_instances)} running instances:\n"
                f"{', '.join(running_instances)}\n\n"
                "Do you want to stop them and exit?",
                icon='warning'
            )

            if response:
                # Stop all running instances
                for instance_name in running_instances:
                    self.main_window.gui_manager.stop_instance(instance_name)
                self.root.quit()
        else:
            self.root.quit()
