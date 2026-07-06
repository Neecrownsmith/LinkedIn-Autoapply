#!/bin/bash
# One-shot installation script for systemd timer setup on Linux

# Ensure the script is run with root privileges
if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run this script with sudo privileges:"
  echo "sudo bash $0"
  exit 1
fi

PROJECT_DIR="/home/botuser/LinkedIn-Autoapply"
SERVICE_NAME="linkedin_bot.service"
TIMER_NAME="linkedin_bot.timer"

echo "=== LinkedIn Auto-Apply Bot Service Installation ==="

# 1. Ensure wrapper script is executable
echo "[1/4] Setting executable permissions on launch script..."
if [ -f "$PROJECT_DIR/deploy/launch_bot.sh" ]; then
    chmod +x "$PROJECT_DIR/deploy/launch_bot.sh"
else
    echo "Error: launch_bot.sh not found in $PROJECT_DIR/deploy/"
    exit 1
fi

# 2. Copy systemd units
echo "[2/4] Copying systemd service and timer files to system directory..."
if [ -f "$PROJECT_DIR/deploy/$SERVICE_NAME" ] && [ -f "$PROJECT_DIR/deploy/$TIMER_NAME" ]; then
    cp "$PROJECT_DIR/deploy/$SERVICE_NAME" /etc/systemd/system/
    cp "$PROJECT_DIR/deploy/$TIMER_NAME" /etc/systemd/system/
else
    echo "Error: Systemd files not found in $PROJECT_DIR/deploy/"
    exit 1
fi

# 3. Reload systemd daemon
echo "[3/4] Reloading systemd daemon..."
systemctl daemon-reload

# 4. Enable and start timer
echo "[4/4] Enabling and starting $TIMER_NAME..."
systemctl enable --now "$TIMER_NAME"

echo "============================================="
echo "Installation Successful!"
echo "---------------------------------------------"
echo "Check timer status:"
echo "  systemctl status $TIMER_NAME"
echo ""
echo "Monitor log outputs:"
echo "  journalctl -u $SERVICE_NAME -f"
echo ""
echo "Trigger a manual execution right now:"
echo "  sudo systemctl start $SERVICE_NAME"
echo "============================================="
