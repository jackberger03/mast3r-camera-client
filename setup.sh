#!/bin/bash
#
# Setup script for MASt3R Camera Client on Raspberry Pi
#
# This script will:
# 1. Install required system packages
# 2. Install Python dependencies
# 3. Configure the systemd service
# 4. Enable the service to run at startup
#
# Usage: sudo bash setup.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Usage: sudo bash setup.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(eval echo ~$ACTUAL_USER)

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}MASt3R Camera Client Setup${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Installing for user: $ACTUAL_USER"
echo "Home directory: $USER_HOME"
echo ""

# Update package list
echo -e "${YELLOW}[1/5] Updating package list...${NC}"
apt update

# Install system dependencies
echo -e "${YELLOW}[2/5] Installing system dependencies...${NC}"
apt install -y \
    python3 \
    python3-pip \
    python3-picamera2 \
    python3-pil \
    libcamera-apps

# Install Python dependencies
echo -e "${YELLOW}[3/5] Installing Python dependencies...${NC}"
pip3 install --break-system-packages requests Pillow

# Copy project files to user's home directory if not already there
PROJECT_DIR="$USER_HOME/mast3r-camera-client"
if [ "$PWD" != "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}[4/5] Copying project files to $PROJECT_DIR...${NC}"
    mkdir -p "$PROJECT_DIR"
    cp camera_client.py "$PROJECT_DIR/"
    cp mast3r-camera.service "$PROJECT_DIR/"
    chown -R "$ACTUAL_USER:$ACTUAL_USER" "$PROJECT_DIR"
else
    echo -e "${YELLOW}[4/5] Project files already in place${NC}"
fi

# Make script executable
chmod +x "$PROJECT_DIR/camera_client.py"

# Configure systemd service
echo -e "${YELLOW}[5/5] Configuring systemd service...${NC}"

# Update service file with correct paths
SERVICE_FILE="/etc/systemd/system/mast3r-camera.service"
cp "$PROJECT_DIR/mast3r-camera.service" "$SERVICE_FILE"

# Replace pi user with actual user
sed -i "s|User=pi|User=$ACTUAL_USER|g" "$SERVICE_FILE"
sed -i "s|/home/pi|$USER_HOME|g" "$SERVICE_FILE"

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable mast3r-camera.service

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "The camera client has been installed and configured to run at startup."
echo ""
echo "Commands:"
echo "  ${GREEN}sudo systemctl start mast3r-camera${NC}    - Start the service now"
echo "  ${GREEN}sudo systemctl stop mast3r-camera${NC}     - Stop the service"
echo "  ${GREEN}sudo systemctl status mast3r-camera${NC}   - Check service status"
echo "  ${GREEN}sudo systemctl restart mast3r-camera${NC}  - Restart the service"
echo "  ${GREEN}sudo journalctl -u mast3r-camera -f${NC}   - View live logs"
echo ""
echo "To test manually:"
echo "  ${GREEN}cd $PROJECT_DIR${NC}"
echo "  ${GREEN}python3 camera_client.py${NC}"
echo ""
echo "Configuration:"
echo "  Edit $SERVICE_FILE to change:"
echo "    - Server hostname (default: linux-2)"
echo "    - Server port (default: 5050)"
echo "    - FPS (default: 1)"
echo ""
echo -e "${YELLOW}Note: After editing the service file, run:${NC}"
echo "  ${GREEN}sudo systemctl daemon-reload${NC}"
echo "  ${GREEN}sudo systemctl restart mast3r-camera${NC}"
echo ""
