"""
Lab Panel Component

This module provides the lab environment management interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from gui.utils.themes import get_theme_colors, create_tooltip
from gui.managers.gui_storm_manager import GUIStormManager
from gui.utils.gui_lab_manager import GUILabManager


class LabPanel:
    """Lab panel class for managing the SIP lab environment."""

    def __init__(self, parent: tk.Widget, gui_manager: GUIStormManager):
        """
        Initialize the lab panel.

        Args:
            parent: Parent widget
            gui_manager: GUI storm manager instance
        """
        self.parent = parent
        self.gui_manager = gui_manager
        self.lab_instance = None
        
        # Create a dedicated GUI lab manager for direct lab operations
        from utils.config.config import Config, Parameters, ConfigType
        lab_params = Parameters({})  # Empty params, will be filled by GUI controls
        lab_config = Config(ConfigType.LAB, lab_params)
        self.gui_lab_manager = GUILabManager(lab_config)
        self.gui_lab_manager.set_status_callback(self._on_lab_status_update)

        # Create the main frame
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create components
        self._create_lab_info()
        self._create_lab_configuration()
        self._create_control_buttons()
        self._create_status_display()

        # Register for status updates from storm manager
        self.gui_manager.register_status_callback("lab_panel", self._on_status_update)
        
        # Start status update timer
        self._update_status_timer()

    def _create_lab_info(self):
        """Create the lab information section."""
        # Info frame
        info_frame = ttk.LabelFrame(self.main_frame, text="🧪 Lab Environment Info",
                                    style="Card.TFrame")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # Information text
        info_text = """
        The SIP Lab Environment provides a containerized Asterisk PBX server for testing SIP attacks safely.

        Features:
        • Asterisk PBX with SIP support
        • Containerized for isolation and security
        • Pre-configured with test extensions
        • Network isolation with custom routing
        • Real-time monitoring and logging
        """

        info_label = ttk.Label(info_frame, text=info_text.strip(),
                               wraplength=600, justify=tk.LEFT)
        info_label.pack(padx=15, pady=10)

    def _create_lab_configuration(self):
        """Create the lab configuration section."""
        # Configuration frame
        config_frame = ttk.LabelFrame(self.main_frame, text="⚙️ Lab Configuration",
                                      style="Card.TFrame")
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # Left column - Network settings
        left_frame = ttk.Frame(config_frame)
        left_frame.grid(row=0, column=0, sticky=tk.NW, padx=10, pady=5)

        ttk.Label(left_frame, text="Network Settings:", style="Heading.TLabel").pack(anchor=tk.W)

        # Spoofed subnet
        subnet_frame = ttk.Frame(left_frame)
        subnet_frame.pack(fill=tk.X, pady=2)
        ttk.Label(subnet_frame, text="Spoofed Subnet:").pack(side=tk.LEFT)
        self.spoofed_subnet_var = tk.StringVar(value="10.10.123.0/25")
        subnet_entry = ttk.Entry(subnet_frame, textvariable=self.spoofed_subnet_var, width=15)
        subnet_entry.pack(side=tk.LEFT, padx=(5, 0))
        create_tooltip(subnet_entry, "Subnet used for IP spoofing in attacks")

        # Return address
        return_frame = ttk.Frame(left_frame)
        return_frame.pack(fill=tk.X, pady=2)
        ttk.Label(return_frame, text="Return Address:").pack(side=tk.LEFT)
        self.return_addr_var = tk.StringVar(value="10.135.97.2")
        return_entry = ttk.Entry(return_frame, textvariable=self.return_addr_var, width=15)
        return_entry.pack(side=tk.LEFT, padx=(5, 0))
        create_tooltip(return_entry, "IP address for return traffic routing")

        # Right column - Lab options
        right_frame = ttk.Frame(config_frame)
        right_frame.grid(row=0, column=1, sticky=tk.NW, padx=20, pady=5)

        ttk.Label(right_frame, text="Lab Options:", style="Heading.TLabel").pack(anchor=tk.W)

        # Checkboxes
        self.keep_open_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Keep Lab Open on Exit",
                        variable=self.keep_open_var).pack(anchor=tk.W, pady=2)
        create_tooltip(right_frame, "Keep the lab container running when the GUI exits")

        self.enable_logging_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Enable Container Logging",
                        variable=self.enable_logging_var).pack(anchor=tk.W, pady=2)

        self.auto_cleanup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Auto Cleanup on Stop",
                        variable=self.auto_cleanup_var).pack(anchor=tk.W, pady=2)

        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(right_frame, text="Dry Run Mode",
                        variable=self.dry_run_var).pack(anchor=tk.W, pady=2)

        self.open_window_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(right_frame, text="Open Terminal Window",
                        variable=self.open_window_var).pack(anchor=tk.W, pady=2)
        create_tooltip(right_frame, "Open the lab container in a new terminal window (not recommended for GUI use)")

        # Container info section
        container_frame = ttk.Frame(config_frame)
        container_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        ttk.Label(
            container_frame,
            text="Container Details:",
            style="Heading.TLabel").pack(
            anchor=tk.W)

        details_text = "Image: asterisk-sip-server | Container: sip-victim | Network: host mode"
        ttk.Label(container_frame, text=details_text,
                  style="TLabel").pack(anchor=tk.W, pady=2)

    def _create_control_buttons(self):
        """Create the control buttons section."""
        # Control buttons frame
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Buttons
        self.start_button = ttk.Button(control_frame, text="🚀 Start Lab",
                                       style="Success.TButton",
                                       command=self._start_lab)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = ttk.Button(control_frame, text="⏹️ Stop Lab",
                                      style="Danger.TButton",
                                      command=self._stop_lab, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))

        self.restart_button = ttk.Button(control_frame, text="🔄 Restart Lab",
                                         style="Warning.TButton",
                                         command=self._restart_lab, state=tk.DISABLED)
        self.restart_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(control_frame, text="📋 Show Logs",
                   command=self._show_logs).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(control_frame, text="🔧 Container Shell",
                   command=self._open_shell).pack(side=tk.LEFT, padx=(0, 10))

    def _create_status_display(self):
        """Create the status display section."""
        # Status frame
        status_frame = ttk.LabelFrame(self.main_frame, text="📊 Lab Status",
                                      style="Card.TFrame")
        status_frame.pack(fill=tk.BOTH, expand=True)

        # Status information frame
        status_info_frame = ttk.Frame(status_frame)
        status_info_frame.pack(fill=tk.X, padx=10, pady=5)

        # Status indicators
        ttk.Label(status_info_frame, text="Status:", style="Heading.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=5)
        self.status_label = ttk.Label(status_info_frame, text="Stopped", style="Error.TLabel")
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(status_info_frame, text="Container IP:", style="Heading.TLabel").grid(
            row=0, column=2, sticky=tk.W, padx=20)
        self.container_ip_label = ttk.Label(status_info_frame, text="N/A")
        self.container_ip_label.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(status_info_frame, text="SIP Port:", style="Heading.TLabel").grid(
            row=1, column=0, sticky=tk.W, padx=5)
        self.sip_port_label = ttk.Label(status_info_frame, text="5060")
        self.sip_port_label.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(status_info_frame, text="Uptime:", style="Heading.TLabel").grid(
            row=1, column=2, sticky=tk.W, padx=20)
        self.uptime_label = ttk.Label(status_info_frame, text="N/A")
        self.uptime_label.grid(row=1, column=3, sticky=tk.W, padx=5)

        # Status log
        ttk.Label(status_frame, text="Lab Logs:", style="Heading.TLabel").pack(
            anchor=tk.W, padx=10, pady=(10, 0))

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
            "Lab environment ready to start. Configure settings and click 'Start Lab'.")

    def _start_lab(self):
        """Start the lab environment."""
        self._add_status_message("Starting lab environment...")

        # Update the GUI lab manager's config with current settings
        from utils.config.config import Config, Parameters, ConfigType
        lab_params = Parameters({
            "spoofed_subnet": self.spoofed_subnet_var.get(),
            "return_addr": self.return_addr_var.get(),
            "keep_lab_open": self.keep_open_var.get(),
            "enable_logging": self.enable_logging_var.get(),
            "auto_cleanup": self.auto_cleanup_var.get(),
            "dry_run": self.dry_run_var.get(),
            "open_window": self.open_window_var.get(),
        })
        
        lab_config = Config(ConfigType.LAB, lab_params)
        self.gui_lab_manager.config = lab_config

        self._add_status_message(f"Configuration: {dict(lab_params)}")

        # Start lab using GUI lab manager
        def start_thread():
            success = self.gui_lab_manager.start_lab()
            if success:
                self._update_button_states(lab_running=True)
                self._add_status_message("Lab start initiated...")
            else:
                self._add_status_message("Failed to start lab!")
                messagebox.showerror(
                    "Error", "Failed to start the lab. Check Docker installation and permissions.")

        # Run in separate thread to avoid blocking GUI
        thread = threading.Thread(target=start_thread, daemon=True)
        thread.start()

    def _stop_lab(self):
        """Stop the lab environment."""
        self._add_status_message("Stopping lab environment...")

        def stop_thread():
            success = self.gui_lab_manager.stop_lab()
            if success:
                self._update_button_states(lab_running=False)
                self._update_status_display("Stopped")
                self._add_status_message("Lab stopped successfully!")
            else:
                self._add_status_message("Failed to stop lab!")
                messagebox.showerror("Error", "Failed to stop the lab.")

        # Run in separate thread to avoid blocking GUI
        thread = threading.Thread(target=stop_thread, daemon=True)
        thread.start()

    def _restart_lab(self):
        """Restart the lab environment."""
        self._add_status_message("Restarting lab environment...")
        
        def restart_thread():
            # Stop first
            success = self.gui_lab_manager.stop_lab()
            if success:
                time.sleep(2)  # Wait a moment
                # Start again
                success = self.gui_lab_manager.start_lab()
                if success:
                    self._add_status_message("Lab restart initiated...")
                else:
                    self._add_status_message("Failed to restart lab!")
                    messagebox.showerror("Error", "Failed to restart the lab.")
            else:
                self._add_status_message("Failed to stop lab for restart!")

        # Run in separate thread to avoid blocking GUI
        thread = threading.Thread(target=restart_thread, daemon=True)
        thread.start()

    def _show_logs(self):
        """Show detailed container logs."""
        # This is a placeholder - in a real implementation, you'd fetch actual container logs
        messagebox.showinfo("Container Logs",
                            "Container log viewing will be implemented in a future version.\n"
                            "For now, check the Status tab for basic log information.")

    def _open_shell(self):
        """Open a shell to the container."""
        # This is a placeholder - in a real implementation, you'd open a terminal to the container
        messagebox.showinfo("Container Shell",
                            "Container shell access will be implemented in a future version.\n"
                            "For now, use: docker exec -it sip-victim /bin/bash")

    def _update_button_states(self, lab_running: bool):
        """Update button states based on lab status."""
        if lab_running:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.restart_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.restart_button.config(state=tk.DISABLED)

    def _update_status_display(self, status: str):
        """Update the status display."""
        self.status_label.config(text=status)

        if status == "Running":
            self.status_label.config(style="Success.TLabel")
            # In a real implementation, you'd get the actual container IP
            self.container_ip_label.config(text="127.0.0.1")
            self.uptime_label.config(text="Just started")
        else:
            self.status_label.config(style="Error.TLabel")
            self.container_ip_label.config(text="N/A")
            self.uptime_label.config(text="N/A")

    def _add_status_message(self, message: str):
        """Add a status message to the display."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        self.status_text.insert(tk.END, formatted_message)
        self.status_text.see(tk.END)

    def _on_lab_status_update(self, message: str):
        """Handle status updates from the GUI lab manager."""
        self._add_status_message(f"Lab: {message}")
        
        # Update display based on status
        status = self.gui_lab_manager.get_status()
        if status == "Running":
            self._update_status_display("Running")
            self._update_button_states(lab_running=True)
        elif status == "Stopped":
            self._update_status_display("Stopped") 
            self._update_button_states(lab_running=False)
        elif status.startswith("Starting"):
            self._update_status_display("Starting")
        elif status.startswith("Stopping"):
            self._update_status_display("Stopping")
        else:
            self._update_status_display(status)

    def _update_status_timer(self):
        """Periodically update the lab status."""
        try:
            # Check actual lab status
            status = self.gui_lab_manager.get_status()
            current_display = self.status_label.cget("text")
            
            # Update if status changed
            if current_display != status:
                self._update_status_display(status)
                
                # Update button states based on status
                if status == "Running":
                    self._update_button_states(lab_running=True)
                elif status == "Stopped":
                    self._update_button_states(lab_running=False)
                    
        except Exception as e:
            self._add_status_message(f"Status check error: {e}")
            
        # Schedule next update
        self.parent.after(3000, self._update_status_timer)  # Update every 3 seconds

    def _on_status_update(self, instance_name: str, status: str):
        """Handle status updates from the GUI manager."""
        # This is for storm manager updates, we now primarily use gui_lab_manager
        if "lab" in instance_name.lower():
            self._add_status_message(f"Storm Manager - {instance_name}: {status}")

            if status in ["stopped", "error"]:
                self._update_button_states(lab_running=False)
                if status == "error":
                    self._add_status_message("Lab encountered an error!")

    def cleanup(self):
        """Clean up the lab panel resources."""
        # Unregister status callback from storm manager
        self.gui_manager.unregister_status_callback("lab_panel")

        # Stop lab if running via GUI lab manager
        if hasattr(self, 'gui_lab_manager') and self.gui_lab_manager.is_running():
            self.gui_lab_manager.stop_lab()
