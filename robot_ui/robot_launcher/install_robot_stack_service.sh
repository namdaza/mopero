#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="robot-stack.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
PROJECT_DIR="/home/jetson/mopero"
START_SCRIPT="${PROJECT_DIR}/robot_ui/robot_launcher/start_robot_stack.sh"

sudo tee "${SERVICE_PATH}" >/dev/null <<EOF
[Unit]
Description=Mopero robot UI, AI server, and ROS2 navigation stack
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=jetson
WorkingDirectory=${PROJECT_DIR}
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/jetson/.Xauthority
Environment=XDG_RUNTIME_DIR=/run/user/1000
ExecStart=${START_SCRIPT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"

echo "Installed and enabled ${SERVICE_NAME}"
echo "Start now:    sudo systemctl start ${SERVICE_NAME}"
echo "Stop:         sudo systemctl stop ${SERVICE_NAME}"
echo "Status:       sudo systemctl status ${SERVICE_NAME}"
echo "Live logs:    journalctl -u ${SERVICE_NAME} -f"
