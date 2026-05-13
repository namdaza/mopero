#!/bin/bash

set -euo pipefail

echo "[launcher] Khoi dong UI"
cd /home/jetson/robot_ui

set +u
source /opt/ros/foxy/setup.bash
set -u

echo "[launcher] Khoi dong AI server"
pkill -f "python3 /home/jetson/robot_ui/server.py" 2>/dev/null || true
pkill -f "python3 server.py" 2>/dev/null || true
AI_PORT="${AI_PORT:-5001}" /usr/bin/python3 /home/jetson/robot_ui/server.py > /tmp/robot_ai_server.log 2>&1 &

bash /home/jetson/robot_ui/start_ui.sh




