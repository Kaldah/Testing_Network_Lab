"""
Attack Panel Component

This module provides the attack configuration and execution interface.
"""

import tkinter as tk
from typing import Dict, List, Any, Optional
from tkinter import ttk, messagebox

from utils.config.config import Parameters
from gui.utils.themes import get_theme_colors, create_tooltip
from gui.managers.gui_storm_manager import GUIStormManager


class AttackPanel:
    """Attack panel class for configuring and running SIP attacks."""

    def __init__(self, parent: tk.Widget, gui_manager: GUIStormManager):
        """
        Initialize the attack panel.

        Args:
            parent: Parent widget
            gui_manager: GUI storm manager instance
        """
        self.parent = parent
        self.gui_manager = gui_manager
        self.current_attack_instance: Optional[str] = None

        # Create the main frame
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create components
        self._create_attack_selection()
        self._create_target_configuration()
        self._create_attack_options()
        self._create_control_buttons()
        self._create_status_display()

        # Load available attacks
        self.refresh_attacks()

        # Register for status updates
        self.gui_manager.register_status_callback("attack_panel", self._on_status_update)

    def _create_attack_selection(self):
        """Create the attack selection section."""
        # Attack selection frame
        selection_frame = ttk.LabelFrame(self.main_frame, text="🎯 Attack Selection",
                                         style="Card.TFrame")
        selection_frame.pack(fill=tk.X, pady=(0, 10))

        # Attack dropdown
        ttk.Label(selection_frame, text="Attack Module:", style="Heading.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=5)

        self.attack_var = tk.StringVar()
        self.attack_combo = ttk.Combobox(selection_frame, textvariable=self.attack_var,
                                         state="readonly", width=30)
        self.attack_combo.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        self.attack_combo.bind('<<ComboboxSelected>>', self._on_attack_selected)

        # Attack description
        self.description_label = ttk.Label(
            selection_frame,
            text="Select an attack module to see details.",
            wraplength=400)
        self.description_label.grid(row=1, column=0, columnspan=2, sticky=tk.W,
                                    padx=10, pady=5)

    def _create_target_configuration(self):
        """Create the target configuration section."""
        # Target configuration frame
        target_frame = ttk.LabelFrame(self.main_frame, text="🎯 Target Configuration",
                                      style="Card.TFrame")
        target_frame.pack(fill=tk.X, pady=(0, 10))

        # Get default IP from system utils
        try:
            from utils.core.system_utils import get_default_ip
            default_ip = get_default_ip()
        except Exception:
            default_ip = "127.0.0.1"

        # Target IP
        ttk.Label(target_frame, text="Target IP:", style="Heading.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=5)

        self.target_ip_var = tk.StringVar(value=default_ip)
        self.target_ip_entry = ttk.Entry(target_frame, textvariable=self.target_ip_var, width=20)
        self.target_ip_entry.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        create_tooltip(self.target_ip_entry, "IP address of the target SIP server")

        # Target Port
        ttk.Label(target_frame, text="Target Port:", style="Heading.TLabel").grid(
            row=0, column=2, sticky=tk.W, padx=10, pady=5)

        self.target_port_var = tk.StringVar(value="5060")
        self.target_port_entry = ttk.Entry(
            target_frame, textvariable=self.target_port_var, width=10)
        self.target_port_entry.grid(row=0, column=3, sticky=tk.W, padx=10, pady=5)
        create_tooltip(self.target_port_entry, "Port number of the target SIP server")

        # Quick target buttons
        quick_frame = ttk.Frame(target_frame)
        quick_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, padx=10, pady=5)

        ttk.Button(
            quick_frame,
            text="Local Lab",
            command=lambda: self._set_quick_target(
                "127.0.0.1",
                "5060")).pack(
            side=tk.LEFT,
            padx=(
                0,
                5))
        ttk.Button(
            quick_frame,
            text="Docker Lab",
            command=lambda: self._set_quick_target(
                "172.17.0.2",
                "5060")).pack(
            side=tk.LEFT,
            padx=(
                0,
                5))
        ttk.Button(quick_frame, text="Auto-detect",
                   command=self._auto_detect_ip).pack(side=tk.LEFT, padx=(0, 5))

    def _create_attack_options(self):
        """Create the attack options section."""
        # Options frame
        options_frame = ttk.LabelFrame(self.main_frame, text="⚙️ Attack Options",
                                       style="Card.TFrame")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        # Left column
        left_frame = ttk.Frame(options_frame)
        left_frame.grid(row=0, column=0, sticky=tk.NW, padx=10, pady=5)

        # Packet count
        ttk.Label(left_frame, text="Max Packets:", style="Heading.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=2)
        self.max_count_var = tk.StringVar(value="100")
        ttk.Entry(left_frame, textvariable=self.max_count_var, width=10).grid(
            row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)

        # Delay between packets
        ttk.Label(left_frame, text="Delay (ms):", style="Heading.TLabel").grid(
            row=1, column=0, sticky=tk.W, pady=2)
        self.delay_var = tk.StringVar(value="100")
        ttk.Entry(left_frame, textvariable=self.delay_var, width=10).grid(
            row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)

        # Right column
        right_frame = ttk.Frame(options_frame)
        right_frame.grid(row=0, column=1, sticky=tk.NW, padx=20, pady=5)

        # Checkboxes
        self.spoofing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Enable IP Spoofing",
                        variable=self.spoofing_var).pack(anchor=tk.W, pady=2)

        self.return_path_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Enable Return Path",
                        variable=self.return_path_var).pack(anchor=tk.W, pady=2)

        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(right_frame, text="Dry Run Mode",
                        variable=self.dry_run_var).pack(anchor=tk.W, pady=2)

        self.open_window_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Open Output Window",
                        variable=self.open_window_var).pack(anchor=tk.W, pady=2)

    def _create_control_buttons(self):
        """Create the control buttons section."""
        # Control buttons frame
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Buttons
        self.start_button = ttk.Button(control_frame, text="🚀 Start Attack",
                                       style="Success.TButton",
                                       command=self._start_attack)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = ttk.Button(control_frame, text="⏹️ Stop Attack",
                                      style="Danger.TButton",
                                      command=self._stop_attack, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(control_frame, text="🔄 Reset",
                   command=self._reset_form).pack(side=tk.LEFT, padx=(0, 10))

    def _create_status_display(self):
        """Create the status display section."""
        # Status frame
        status_frame = ttk.LabelFrame(self.main_frame, text="📊 Attack Status",
                                      style="Card.TFrame")
        status_frame.pack(fill=tk.BOTH, expand=True)

        # Status text
        self.status_text = tk.Text(status_frame, height=8, width=70,
                                   bg=get_theme_colors()['entry_bg'],
                                   fg=get_theme_colors()['fg'],
                                   insertbackground=get_theme_colors()['fg'])
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar for status text
        scrollbar = ttk.Scrollbar(self.status_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # Use getattr to get the method directly by name to bypass type checking issues
        yview_method = getattr(self.status_text, 'yview')
        scrollbar.config(command=yview_method)

        # Initial status message
        self._add_status_message(
            "Ready to launch attacks. Select an attack module and configure targets.")

    def _on_attack_selected(self, event: Optional[tk.Event] = None):
        """Handle attack selection change."""
        selected_attack = self.attack_var.get()
        if not selected_attack:
            return

        # Update description (placeholder for now)
        descriptions = {
            "invite-flood": "Floods the target with SIP INVITE requests to overwhelm the server.",
            "custom-version": "Custom version of the invite flood attack with additional features.",
            "eBPF": "eBPF-based attack for enhanced performance and stealth.",
            "template": "Template attack module for development and testing.",
        }

        description = descriptions.get(selected_attack,
                                       "No description available for this attack module.")
        self.description_label.config(text=description)

        self._add_status_message(f"Selected attack: {selected_attack}")

    def _set_quick_target(self, ip: str, port: str):
        """Set target IP and port quickly."""
        self.target_ip_var.set(ip)
        self.target_port_var.set(port)
        self._add_status_message(f"Target set to {ip}:{port}")

    def _auto_detect_ip(self):
        """Auto-detect and set the default IP address."""
        try:
            from utils.core.system_utils import get_default_ip
            default_ip = get_default_ip()
            self.target_ip_var.set(default_ip)
            self._add_status_message(f"Auto-detected IP: {default_ip}")
        except Exception as e:
            self._add_status_message(f"Failed to auto-detect IP: {e}")
            messagebox.showwarning("Auto-detect Failed",
                                   "Could not auto-detect IP address. Using default.")
            self.target_ip_var.set("127.0.0.1")

    def _start_attack(self):
        """Start the selected attack."""
        # Validate inputs
        if not self.attack_var.get():
            messagebox.showerror("Error", "Please select an attack module.")
            return

        if not self.target_ip_var.get():
            messagebox.showerror("Error", "Please enter a target IP address.")
            return

        try:
            target_port = int(self.target_port_var.get())
            if not (1 <= target_port <= 65535):
                raise ValueError("Port must be between 1 and 65535")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number (1-65535).")
            return

        try:
            max_count = int(self.max_count_var.get())
            if max_count < 1:
                raise ValueError("Max count must be at least 1")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid packet count.")
            return

        # Create configuration parameters
        config_params = Parameters({
            "target_ip": self.target_ip_var.get(),
            "target_port": target_port,
            "max_count": max_count,
            "spoofing_enabled": self.spoofing_var.get(),
            "return_path_enabled": self.return_path_var.get(),
            "dry_run": self.dry_run_var.get(),
            "open_window": self.open_window_var.get(),
        })

        # Add delay if specified
        try:
            delay = int(self.delay_var.get())
            if delay > 0:
                config_params["delay_ms"] = delay
        except ValueError:
            pass  # Ignore invalid delay values

        # Create and start attack instance
        attack_name = self.attack_var.get()

        self._add_status_message(f"Starting attack: {attack_name}")
        self._add_status_message(f"Target: {self.target_ip_var.get()}:{target_port}")
        self._add_status_message(f"Configuration: {dict(config_params)}")

        success = self.gui_manager.create_attack_instance(attack_name, config_params)
        if success:
            instance_name = f"attack_{attack_name}"
            self.current_attack_instance = instance_name

            success = self.gui_manager.start_instance(instance_name)
            if success:
                self._update_button_states(attack_running=True)
                self._add_status_message("Attack started successfully!")
            else:
                # Check if it was a permission error
                self._add_status_message("Failed to start attack - checking permissions...")

                # Show permission error dialog
                from gui.utils.sudo_utils import request_sudo_restart, restart_with_sudo

                self._add_status_message("Attack failed due to permission error!")

                if request_sudo_restart():
                    self._add_status_message("Restarting with administrator privileges...")
                    try:
                        restart_with_sudo()
                    except Exception as e:
                        self._add_status_message(f"Failed to restart with sudo: {e}")
                        messagebox.showerror("Restart Failed",
                                             f"Could not restart with admin privileges: {e}")
                else:
                    messagebox.showwarning(
                        "Limited Functionality",
                        "Attack cancelled. Some features require administrator privileges.\n"
                        "To enable full functionality, restart with: sudo python main.py --gui")
        else:
            self._add_status_message("Failed to create attack instance!")
            messagebox.showerror("Error", "Failed to create the attack instance.")

    def _stop_attack(self):
        """Stop the current attack."""
        if self.current_attack_instance:
            self._add_status_message(f"Stopping attack: {self.current_attack_instance}")
            self._add_status_message("Cleaning up spoofer processes and iptables rules...")

            success = self.gui_manager.stop_instance(self.current_attack_instance)
            if success:
                self.gui_manager.remove_instance(self.current_attack_instance)
                self.current_attack_instance = None
                self._update_button_states(attack_running=False)
                self._add_status_message("Attack stopped successfully!")
                self._add_status_message("All spoofer processes and iptables rules have been cleaned up.")
            else:
                self._add_status_message("Failed to stop attack!")
                self._add_status_message("Some spoofer processes or iptables rules may still be active.")
                messagebox.showerror("Error", "Failed to stop the attack. Check logs for details.")
        else:
            self._add_status_message("No attack is currently running.")
            messagebox.showwarning("Warning", "No attack is currently running.")

    def _reset_form(self):
        """Reset all form fields to default values."""
        # First, stop any running instances
        if hasattr(self, 'current_attack_instance') and self.current_attack_instance:
            self.gui_manager.stop_instance(self.current_attack_instance)
            self.gui_manager.remove_instance(self.current_attack_instance)
            self.current_attack_instance = None

        # Get default IP from system utils
        try:
            from utils.core.system_utils import get_default_ip
            default_ip = get_default_ip()
        except Exception:
            default_ip = "127.0.0.1"

        # Reset all variables to defaults
        self.attack_var.set("")
        self.target_ip_var.set(default_ip)
        self.target_port_var.set("5060")
        self.max_count_var.set("100")
        self.delay_var.set("0")
        self.spoofing_var.set(True)
        self.return_path_var.set(True)
        self.dry_run_var.set(False)
        self.open_window_var.set(True)

        # Clear status messages
        self.status_text.delete(1.0, tk.END)

        # Update button states
        self._update_button_states(attack_running=False)

        # Add confirmation message
        self._add_status_message("Form reset successfully. All fields restored to defaults.")

    def _update_button_states(self, attack_running: bool):
        """Update button states based on attack status."""
        if attack_running:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def _add_status_message(self, message: str):
        """Add a status message to the display."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        self.status_text.insert(tk.END, formatted_message)
        self.status_text.see(tk.END)

    def _on_status_update(self, instance_name: str, status: str):
        """Handle status updates from the GUI manager."""
        if instance_name == self.current_attack_instance:
            self._add_status_message(f"Attack status: {status}")

            if status in ["stopped", "error", "completed"]:
                self._update_button_states(attack_running=False)
                
                if status == "error":
                    self._add_status_message("Attack encountered an error!")
                elif status == "completed":
                    self._add_status_message("Attack completed successfully!")
                    self._add_status_message("Spoofer processes and iptables rules have been cleaned up automatically.")
                    # Clear the current attack instance since it completed
                    self.current_attack_instance = None
                elif status == "stopped":
                    self._add_status_message("Attack was stopped manually.")
                    # Clear the current attack instance since it was stopped
                    self.current_attack_instance = None

    def refresh_attacks(self):
        """Refresh the list of available attack modules."""
        # get_available_attacks returns Dict[str, Path]
        attacks: Dict[str, Any] = self.gui_manager.get_available_attacks() 
        attack_names: List[str] = list(attacks.keys())

        self.attack_combo['values'] = attack_names
        if attack_names and not self.attack_var.get():
            self.attack_var.set(attack_names[0])
            self._on_attack_selected(None)

        self._add_status_message(f"Refreshed attack modules: {len(attack_names)} available")

    def cleanup(self):
        """Clean up the attack panel resources."""
        # Unregister status callback
        self.gui_manager.unregister_status_callback("attack_panel")

        # Stop current attack if running
        if self.current_attack_instance:
            self.gui_manager.stop_instance(self.current_attack_instance)
            self.gui_manager.remove_instance(self.current_attack_instance)
