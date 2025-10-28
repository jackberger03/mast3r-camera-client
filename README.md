# MASt3R Camera Client

Camera client for Raspberry Pi Camera Module 3 that captures images and streams them to a [MASt3R-SLAM server](https://github.com/jackberger03/MASt3R-SLAM-API) for real-time 3D reconstruction.

## Features

- 📷 **Raspberry Pi Camera Module 3 support**
- 🔄 **Automatic PNG conversion**
- 📡 **HTTP upload to MASt3R-SLAM server**
- ⚙️ **Configurable capture rate** (default: 1 FPS)
- 🚀 **Systemd service** for automatic startup
- 🌐 **Tailscale support** for easy remote access
- 🔁 **Auto-reconnect** on network issues

## Hardware Requirements

- Raspberry Pi 4 or 5 (recommended)
- Raspberry Pi Camera Module 3
- Raspberry Pi OS (Bookworm or later)
- Network connection (WiFi or Ethernet)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/jackberger03/mast3r-camera-client.git
cd mast3r-camera-client
```

### 2. Run Setup Script

```bash
sudo bash setup.sh
```

This will:
- Install required system packages
- Install Python dependencies
- Configure systemd service
- Enable auto-start on boot

### 3. Start the Service

```bash
sudo systemctl start mast3r-camera
```

That's it! Your Raspberry Pi will now capture images and send them to your MASt3R-SLAM server.

## Configuration

### Change Server Host/Port

Edit the service file:

```bash
sudo nano /etc/systemd/system/mast3r-camera.service
```

Modify the `ExecStart` line:

```ini
ExecStart=/usr/bin/python3 /home/pi/mast3r-camera-client/camera_client.py --host YOUR_HOST --port YOUR_PORT --fps 1
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mast3r-camera
```

### Command Line Options

```bash
python3 camera_client.py --help
```

Options:
- `--host` - Server hostname (default: linux-2)
- `--port` - Server port (default: 5050)
- `--fps` - Frames per second (default: 1.0)
- `--save-local` - Save images locally as well
- `--verbose` - Enable verbose logging

### Example Configurations

**Faster capture (2 FPS):**
```bash
python3 camera_client.py --fps 2
```

**Custom server:**
```bash
python3 camera_client.py --host 192.168.1.100 --port 5050
```

**Save local copies:**
```bash
python3 camera_client.py --save-local
```

## Systemd Service Commands

```bash
# Start service
sudo systemctl start mast3r-camera

# Stop service
sudo systemctl stop mast3r-camera

# Restart service
sudo systemctl restart mast3r-camera

# Check status
sudo systemctl status mast3r-camera

# View live logs
sudo journalctl -u mast3r-camera -f

# Disable auto-start
sudo systemctl disable mast3r-camera

# Enable auto-start
sudo systemctl enable mast3r-camera
```

## Using with Tailscale

If your MASt3R-SLAM server is on Tailscale:

1. **Install Tailscale on Raspberry Pi:**
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. **Use Tailscale hostname:**
   ```bash
   python3 camera_client.py --host linux-2
   ```

   Where `linux-2` is your server's Tailscale hostname.

3. **Check Tailscale status:**
   ```bash
   tailscale status
   ```

## Troubleshooting

### Camera Not Detected

```bash
# Check camera connection
libcamera-hello

# If that doesn't work, enable camera:
sudo raspi-config
# Navigate to Interface Options → Camera → Enable
```

### Cannot Connect to Server

```bash
# Test server connectivity
curl http://linux-2:5050/status

# If using Tailscale, check status
tailscale status

# Ping server
ping linux-2
```

### Service Not Starting

```bash
# Check service logs
sudo journalctl -u mast3r-camera -n 50

# Check service status
sudo systemctl status mast3r-camera

# Test manually
cd ~/mast3r-camera-client
python3 camera_client.py --verbose
```

### Python Dependency Issues

```bash
# Reinstall dependencies
pip3 install --break-system-packages --force-reinstall requests Pillow

# For picamera2
sudo apt install -y python3-picamera2
```

## Manual Installation (Without setup.sh)

If you prefer manual installation:

```bash
# 1. Install system packages
sudo apt update
sudo apt install -y python3 python3-pip python3-picamera2 python3-pil libcamera-apps

# 2. Install Python packages
pip3 install --break-system-packages requests Pillow

# 3. Make script executable
chmod +x camera_client.py

# 4. Test manually
python3 camera_client.py --host linux-2 --port 5050

# 5. (Optional) Install as service
sudo cp mast3r-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mast3r-camera
sudo systemctl start mast3r-camera
```

## Development

### Test Capture Without Upload

```python
from picamera2 import Picamera2
from PIL import Image
import io

# Initialize camera
camera = Picamera2()
config = camera.create_still_configuration()
camera.configure(config)
camera.start()

# Capture
image_array = camera.capture_array()
img = Image.fromarray(image_array)
img.save("test.png")

camera.stop()
```

### Monitor Performance

```bash
# Watch logs in real-time
sudo journalctl -u mast3r-camera -f

# Check CPU/memory usage
htop

# Test FPS performance
python3 camera_client.py --verbose --fps 2
```

## Architecture

```
┌─────────────────────┐
│  Raspberry Pi       │
│  + Camera Module 3  │
│                     │
│  camera_client.py   │
│  (captures @ 1 FPS) │
└──────────┬──────────┘
           │ HTTP POST
           │ (PNG images)
           ▼
    ┌──────────────┐
    │  Tailscale   │  (optional)
    └──────┬───────┘
           │
           ▼
┌─────────────────────────┐
│  MASt3R-SLAM Server     │
│  (linux-2:5050)         │
│                         │
│  image_receiver_api.py  │
│  └─ Receives images     │
│  └─ Converts to PNG     │
│  └─ Queues for SLAM     │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  MASt3R-SLAM            │
│  └─ 3D reconstruction   │
│  └─ Visualization       │
└─────────────────────────┘
```

## Performance Notes

- **1 FPS** is recommended for stable real-time reconstruction
- **Camera Module 3** captures at 4608x2592 resolution
- PNG conversion takes ~100-200ms
- Upload time depends on network speed
- Total loop time: ~300-500ms per frame at 1 FPS

## Server Setup

This client requires a MASt3R-SLAM server with the HTTP API:

1. Clone the server repo:
   ```bash
   git clone https://github.com/jackberger03/MASt3R-SLAM-API.git
   ```

2. Start the API server:
   ```bash
   conda activate mast3r-slam
   python image_receiver_api.py --continuous
   ```

See the [MASt3R-SLAM-API README](https://github.com/jackberger03/MASt3R-SLAM-API) for details.

## License

This project builds on [MASt3R-SLAM](https://github.com/rmurai0610/MASt3R-SLAM) by Riku Murai and Eric Dexheimer.

## Contributing

Issues and pull requests welcome!

## Related Projects

- [MASt3R-SLAM-API](https://github.com/jackberger03/MASt3R-SLAM-API) - Server with HTTP API
- [MASt3R-SLAM](https://github.com/rmurai0610/MASt3R-SLAM) - Original MASt3R-SLAM
- [MASt3R](https://github.com/naver/mast3r) - MASt3R reconstruction model
