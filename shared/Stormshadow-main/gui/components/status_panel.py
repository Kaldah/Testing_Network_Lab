"""
Status Panel Component

This module provides the status monitoring and logging interface.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict

from gui.utils.themes import get_theme_colors


class StatusPanel:
    """Status panel class for monitoring system status and logs."""

    def __init__(self, parent: tk.Widget, gui_manager: Any):
        """
        Initialize the status panel.

        Args:
            parent: Parent widget
            gui_manager: GUI storm manager instance
        """
        self.parent = parent
        self.gui_manager = gui_manager
        
        # Cache for system info to avoid repeated checks
        self._docker_version_cached = None
        self._docker_checked = False

        # Create the main frame
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create components
        self._create_instance_status()
        self._create_system_info()
        self._create_log_viewer()

        # Update status periodically
        self._update_status()

        # Register for status updates
        self.gui_manager.register_status_callback("status_panel", self._on_status_update)

    def _create_instance_status(self):
        """Create the instance status section."""
        # Instance status frame
        status_frame = ttk.LabelFrame(self.main_frame, text="📊 Running Instances",
                                      style="Card.TFrame")
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # Create treeview for instances
        columns = ('Name', 'Type', 'Status', 'Uptime')
        self.instance_tree = ttk.Treeview(status_frame, columns=columns, show='headings', height=6)

        # Define headings
        self.instance_tree.heading('Name', text='Instance Name')
        self.instance_tree.heading('Type', text='Type')
        self.instance_tree.heading('Status', text='Status')
        self.instance_tree.heading('Uptime', text='Uptime')

        # Define column widths
        self.instance_tree.column('Name', width=200)
        self.instance_tree.column('Type', width=100)
        self.instance_tree.column('Status', width=100)
        self.instance_tree.column('Uptime', width=150)

        self.instance_tree.pack(fill=tk.X, padx=10, pady=10)

        # Control buttons for instances
        control_frame = ttk.Frame(status_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(control_frame, text="🔄 Refresh",
                   command=self._refresh_instances).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="⏹️ Stop Selected",
                   command=self._stop_selected_instance).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="🗑️ Remove Selected",
                   command=self._remove_selected_instance).pack(side=tk.LEFT, padx=(0, 10))

    def _create_system_info(self):
        """Create the system information section."""
        # System info frame
        info_frame = ttk.LabelFrame(self.main_frame, text="🖥️ System Information",
                                    style="Card.TFrame")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        # Create info grid
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X, padx=10, pady=10)

        # Store references to update them later
        # Map label text -> ttk.Label so Pylance knows the widget type
        self.info_labels: Dict[str, ttk.Label] = {}

        # System information labels
        self._create_info_row(info_grid, 0, "Platform:", "Linux (detected automatically)")
        self._create_info_row(info_grid, 1, "Python Version:", "3.x")
        self._create_info_row(info_grid, 2, "Root Access:", "Checking...")
        self._create_info_row(info_grid, 3, "Docker Status:", "Checking...")
        self._create_info_row(info_grid, 4, "Network Interface:", "Auto-detected")
        self._create_info_row(info_grid, 5, "Available Attacks:", "Loading...")

    def _create_info_row(self, parent: tk.Widget, row: int, label_text: str, value_text: str) -> None:
        """Create a row of system information.

        Args:
            parent: Parent widget where the row will be placed (typically a Frame).
            row: Grid row index for placement.
            label_text: Text for the left-hand label (used as a key in self.info_labels).
            value_text: Initial text for the value label on the right.
        """
        ttk.Label(parent, text=label_text, style="Heading.TLabel").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=2)
        label = ttk.Label(parent, text=value_text)
        label.grid(row=row, column=1, sticky=tk.W, padx=20, pady=2)
        self.info_labels[label_text] = label

    def _create_log_viewer(self):
        """Create the log viewer section."""
        # Log viewer frame
        log_frame = ttk.LabelFrame(self.main_frame, text="📋 System Logs",
                                   style="Card.TFrame")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Log controls
        control_frame = ttk.Frame(log_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(control_frame, text="Log Level:", style="Heading.TLabel").pack(side=tk.LEFT)

        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(control_frame, textvariable=self.log_level_var,
                                       values=["DEBUG", "INFO", "WARNING", "ERROR"],
                                       state="readonly", width=10)
        log_level_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="🗑️ Clear Logs",
                   command=self.clear_logs).pack(side=tk.RIGHT)
        ttk.Button(control_frame, text="💾 Export Logs",
                   command=self._export_logs).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(control_frame, text="🔄 Refresh",
                   command=self._refresh_logs).pack(side=tk.RIGHT, padx=(0, 5))

        # Log text area with scrollbar
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = tk.Text(log_text_frame, height=15,
                                bg=get_theme_colors()['entry_bg'],
                                fg=get_theme_colors()['fg'],
                                insertbackground=get_theme_colors()['fg'],
                                font=('Consolas', 10))

        # Create scrollbars and manually connect them
        scrollbar_v = ttk.Scrollbar(log_text_frame, orient=tk.VERTICAL)
        scrollbar_h = ttk.Scrollbar(log_text_frame, orient=tk.HORIZONTAL)
        
        # Set up the text widget's scroll commands
        self.log_text.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        # Use getattr to get the methods directly by name to bypass type checking issues
        yview_method = getattr(self.log_text, 'yview')
        xview_method = getattr(self.log_text, 'xview')
        
        scrollbar_v['command'] = yview_method
        scrollbar_h['command'] = xview_method

        # Pack scrollbars and text
        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Initial log message
        self._add_log_message("System started. Monitoring for events...")

    def _update_status(self):
        """Update the status display."""
        # Update instance list
        self._refresh_instances()

        # Update system info
        self._update_system_info()

        # Schedule next update
        self.parent.after(5000, self._update_status)  # Update every 5 seconds

    def _refresh_instances(self):
        """Refresh the instances display."""
        # Clear existing items
        for item in self.instance_tree.get_children():
            self.instance_tree.delete(item)

        # Get current instances
        instances = self.gui_manager.get_all_instances()

        for instance_name, status in instances.items():
            # Determine instance type from name
            if instance_name.startswith("attack_"):
                instance_type = "Attack"
                display_name = instance_name.replace("attack_", "")
            elif instance_name == "lab":
                instance_type = "Lab"
                display_name = "SIP Lab"
            else:
                instance_type = "Unknown"
                display_name = instance_name

            # Format status with color-coded icons
            if status == "running":
                status_text = "🟢 Running"
                uptime = "Active"  # In a real implementation, calculate actual uptime
            elif status == "stopped":
                status_text = "🔴 Stopped"
                uptime = "N/A"
            elif status == "error":
                status_text = "🔺 Error"
                uptime = "N/A"
            else:
                status_text = f"⚪ {status.capitalize()}"
                uptime = "N/A"

            # Insert into tree
            self.instance_tree.insert(
                '',
                'end',
                values=(
                    display_name,
                    instance_type,
                    status_text,
                    uptime))

    def _update_system_info(self):
        """Update the system information display."""
        import sys
        import os

        # Update Python version
        python_version = f"{
            sys.version_info.major}.{
            sys.version_info.minor}.{
            sys.version_info.micro}"
        self.info_labels["Python Version:"].config(text=python_version)

        # Update root access status
        if os.geteuid() == 0:
            self.info_labels["Root Access:"].config(
                text="✓ Running as root", style="Success.TLabel")
        else:
            self.info_labels["Root Access:"].config(
                text="⚠ Not running as root", style="Warning.TLabel")

        # Update Docker status (cached to avoid repeated checks)
        if not self._docker_checked:
            try:
                from gui.utils.command_utils import get_command_version
                self._docker_version_cached = get_command_version('docker')
                self._docker_checked = True
            except Exception:
                self._docker_version_cached = None
                self._docker_checked = True
        
        # Use cached result
        if self._docker_version_cached:
            self.info_labels["Docker Status:"].config(
                text="✓ Available", style="Success.TLabel")
        else:
            self.info_labels["Docker Status:"].config(
                text="✗ Not available", style="Error.TLabel")

        # Update available attacks count
        attacks = self.gui_manager.get_available_attacks()
        self.info_labels["Available Attacks:"].config(text=f"{len(attacks)} modules found")

    def _stop_selected_instance(self):
        """Stop the selected instance."""
        selected_item = self.instance_tree.selection()
        if not selected_item:
            return

        item = self.instance_tree.item(selected_item[0])
        display_name = item['values'][0]
        instance_type = item['values'][1]

        # Convert display name back to instance name
        if instance_type == "Attack":
            instance_name = f"attack_{display_name}"
        elif instance_type == "Lab":
            instance_name = "lab"
        else:
            return

        success = self.gui_manager.stop_instance(instance_name)
        if success:
            self._add_log_message(f"Stopped instance: {display_name}")
        else:
            self._add_log_message(f"Failed to stop instance: {display_name}")

    def _remove_selected_instance(self):
        """Remove the selected instance."""
        selected_item = self.instance_tree.selection()
        if not selected_item:
            return

        item = self.instance_tree.item(selected_item[0])
        display_name = item['values'][0]
        instance_type = item['values'][1]

        # Convert display name back to instance name
        if instance_type == "Attack":
            instance_name = f"attack_{display_name}"
        elif instance_type == "Lab":
            instance_name = "lab"
        else:
            return

        success = self.gui_manager.remove_instance(instance_name)
        if success:
            self._add_log_message(f"Removed instance: {display_name}")
        else:
            self._add_log_message(f"Failed to remove instance: {display_name}")

    def _refresh_logs(self):
        """Refresh the log display."""
        # In a real implementation, you might reload logs from files
        self._add_log_message("Log display refreshed.")

    def _export_logs(self):
        """Export logs to a file."""
        from tkinter import filedialog

        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
            )

            if filename:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self._add_log_message(f"Logs exported to: {filename}")
        except Exception as e:
            self._add_log_message(f"Failed to export logs: {e}")

    def clear_logs(self):
        """Clear the log display."""
        self.log_text.delete(1.0, tk.END)
        self._add_log_message("Logs cleared.")

    def _add_log_message(self, message: str, level: str = "INFO"):
        """Add a log message to the display."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}\n"

        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)

    def _on_status_update(self, instance_name: str, status: str):
        """Handle status updates from the GUI manager."""
        self._add_log_message(f"Instance '{instance_name}' status changed to: {status}")
        # Refresh instances display to show updated status
        self._refresh_instances()

    def update_status(self, instance_name: str, status: str):
        """Public method to update status (called from main window)."""
        self._on_status_update(instance_name, status)

    def refresh_docker_status(self):
        """Force refresh of Docker status check."""
        self._docker_checked = False
        self._docker_version_cached = None
        self._update_system_info()

    def cleanup(self):
        """Clean up the status panel resources."""
        # Unregister status callback
        self.gui_manager.unregister_status_callback("status_panel")
