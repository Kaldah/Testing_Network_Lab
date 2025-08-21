# StormShadow GUI

A modern Tkinter-based graphical user interface for the StormShadow SIP testing toolkit.

## Features

### 🎯 SIP Attacks Tab
- **Attack Module Selection**: Choose from available attack modules (invite-flood, custom-version, eBPF, etc.)
- **Target Configuration**: Set target IP, port, and attack parameters
- **Real-time Monitoring**: View attack progress and status
- **Flexible Options**: Configure packet count, delays, spoofing, and return paths

### 🧪 Lab Environment Tab
- **Docker Integration**: Start/stop containerized Asterisk PBX server
- **Network Configuration**: Configure spoofed subnets and return addresses
- **Container Management**: Monitor lab status and access logs
- **Safety Features**: Isolated testing environment with proper cleanup

### 📊 Status & Logs Tab
- **Instance Monitoring**: Track all running attack and lab instances
- **System Information**: View platform details, permissions, and dependencies  
- **Real-time Logs**: Monitor system events and troubleshooting information
- **Log Management**: Export, clear, and filter log messages

### 🎨 Modern Interface
- **Dark Theme**: Modern dark theme with accent colors
- **Responsive Design**: Adaptive layout that works on different screen sizes
- **Keyboard Shortcuts**: Quick access to common functions
- **Tooltips & Help**: Context-sensitive help and guidance

## Usage

### Starting the GUI

From the main application:
```bash
# Start GUI directly from main.py
python3 main.py --mode gui

# Or start from the GUI module
cd gui/
python3 main_gui.py
```

### Basic Workflow

1. **Start Lab Environment** (optional but recommended):
   - Go to "Lab Environment" tab
   - Configure network settings if needed
   - Click "Start Lab" to launch the containerized target

2. **Configure Attack**:
   - Go to "SIP Attacks" tab  
   - Select an attack module from the dropdown
   - Set target IP (use 127.0.0.1 for local lab)
   - Configure attack parameters (packet count, delays, etc.)

3. **Launch Attack**:
   - Click "Start Attack" to begin
   - Monitor progress in the status area
   - Use "Stop Attack" to terminate if needed

4. **Monitor Results**:
   - Switch to "Status & Logs" tab to view detailed information
   - Check running instances and system status
   - Export logs for analysis

### Safety Features

- **Confirmation Dialogs**: Warns before stopping running instances
- **Automatic Cleanup**: Properly stops instances on application exit
- **Error Handling**: Graceful handling of Docker and system errors
- **Dry Run Mode**: Test configurations without executing real attacks

## Architecture

The GUI is built with a modular architecture:

```
gui/
├── main_gui.py              # Main application entry point
├── components/              # UI components
│   ├── main_window.py      # Main window container  
│   ├── attack_panel.py     # Attack configuration panel
│   ├── lab_panel.py        # Lab management panel
│   ├── status_panel.py     # Status monitoring panel
│   └── menu_bar.py         # Application menu bar
├── managers/               # Business logic managers
│   └── gui_storm_manager.py # StormShadow instance manager
└── utils/                  # Utilities and helpers
    └── themes.py           # UI theming and styling
```

### Key Design Principles

- **Separation of Concerns**: UI components are separate from business logic
- **Thread Safety**: Non-blocking operations using background threads
- **Resource Management**: Proper cleanup of instances and resources
- **Extensibility**: Easy to add new attack modules and features
- **Integration**: Seamless integration with existing StormShadow core

## Integration with StormShadow Core

The GUI integrates with the existing StormShadow architecture by:

1. **Using Existing Components**: Leverages `StormShadow`, `AttackManager`, `LabManager` classes
2. **Configuration Management**: Uses the same `Parameters` and `Config` system
3. **Attack Discovery**: Utilizes existing attack module finder and loader
4. **Command Runner**: Integrates with the existing command execution system

## Requirements

- Python 3.8+
- tkinter (usually included with Python)
- All StormShadow dependencies (Docker, attack modules, etc.)

## Troubleshooting

### Common Issues

1. **GUI won't start**: Check Python tkinter installation
2. **No attack modules found**: Verify `sip_attacks/` directory exists and is populated
3. **Lab won't start**: Ensure Docker is installed and user has appropriate permissions
4. **Permission errors**: Run with appropriate privileges for network operations

### Debug Mode

Enable verbose logging to troubleshoot issues:
```bash
python3 main.py --mode gui --verbosity debug
```

## Future Enhancements

- **Configuration Profiles**: Save and load attack/lab configurations
- **Advanced Monitoring**: Real-time charts and metrics
- **Plugin System**: Easy integration of custom attack modules
- **Network Visualization**: Visual representation of network topology
- **Automated Testing**: Scripted test sequences and reporting
