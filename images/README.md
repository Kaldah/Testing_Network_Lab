# Docker Images Export/Import

This folder contains exported Docker images for the SIP lab.

## Usage

### Exporting Images

Use the build script with the export flag:
```bash
./build.sh --export-images
```

Or manually export images:
```bash
# Create the images directory
mkdir -p images

# Export individual images
docker save -o images/sip-lab-attacker_latest.tar sip-lab-attacker:latest
docker save -o images/sip-lab-sip_server_latest.tar sip-lab-sip_server:latest  
docker save -o images/sip-lab-openwrt_latest.tar sip-lab-openwrt:latest
```

### Loading Images

Use the build and start script:
```bash
./build_and_start.sh
```

This script will:
1. Check for `.tar` files in this directory
2. Load any found images into Docker
3. Build missing services if needed
4. Start the lab

Or manually load images:
```bash
# Load all tar files
for tar_file in images/*.tar; do
  docker load -i "$tar_file"
done
```

## File Format

Exported images are saved as `.tar` files with naming convention:
- `sip-lab-attacker_latest.tar`
- `sip-lab-sip_server_latest.tar`
- `sip-lab-openwrt_latest.tar`

## Benefits

- **Faster deployment**: Skip rebuild time by loading pre-built images
- **Offline usage**: Deploy lab without internet connection for builds
- **Version control**: Save specific image versions for testing
- **CI/CD**: Use in automated deployment pipelines
