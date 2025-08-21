# Compiled Binaries Directory

This directory contains system-specific compiled binaries for different platforms used in the testing lab.

## Directory Structure

```
compiled-binaries/
├── host/                 # Binaries compiled on the host system (your computer)
├── linux-x86_64/        # Binaries compiled for standard Linux x86_64
├── openwrt-x86_64/       # Binaries compiled for OpenWRT x86_64
└── <platform>/           # Additional platforms as needed
```

## Platform-Specific Binaries

### host/
- Binaries compiled on your local development machine
- Used for development and testing outside containers
- Architecture: $(uname -m)

### linux-x86_64/
- Standard Linux binaries for the Linux container
- Compatible with most Linux distributions
- Used by the Linux Docker container

### openwrt-x86_64/
- OpenWRT-specific binaries compiled with OpenWRT toolchain
- Compatible with OpenWRT's musl libc and specific kernel
- Used by the OpenWRT Docker container

## Usage

Each Docker container will mount the appropriate subdirectory:
- Linux container: `/shared/compiled-binaries/linux-x86_64` → `/usr/local/bin/`
- OpenWRT container: `/shared/compiled-binaries/openwrt-x86_64` → `/usr/local/bin/`

## Building Binaries

### Universal Build Script
The `build-tools.sh` script automatically detects where it's running and compiles accordingly:

#### From Host System
```bash
cd shared/compiled-binaries
./build-tools.sh inviteflood       # Builds for host
./build-tools.sh all               # Builds all tools for host
```

#### From Containers
```bash
# In Linux container
docker exec -it sip-attacker bash
cd /shared/compiled-binaries
./build-tools.sh inviteflood       # Builds for Linux container

# In OpenWRT container  
docker exec -it openwrt-router sh
cd /shared/compiled-binaries
./build-tools.sh inviteflood       # Builds for OpenWRT container
```

The script automatically:
- Detects the current platform (host, Linux container, or OpenWRT container)
- Uses the correct paths and compilation settings
- Places binaries in the appropriate platform directory

## Benefits

1. **System Compatibility**: Each system gets binaries compiled specifically for it
2. **Development Workflow**: Compile once, use everywhere
3. **Version Control**: Track different versions for different platforms
4. **Debugging**: Easy to test host vs container versions
5. **Flexibility**: Add new platforms as needed

## Tools to Compile

- inviteflood
- StormShadow dependencies
- Custom SIP tools
- Any other network testing utilities

## Notes

- Binaries are excluded from git (add to .gitignore)
- This directory is synchronized across all containers via Docker volumes
- Each platform may have different compilation requirements
