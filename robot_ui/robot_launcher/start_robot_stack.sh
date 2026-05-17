#!/bin/bash

set -euo pipefail

exec > >(tee -a /tmp/mopero_start_robot_stack.log) 2>&1
echo
echo "========== $(date '+%F %T') start_robot_stack =========="

BASE_DIR="/home/jetson/mopero"
ROBOT_UI_DIR="${BASE_DIR}/robot_ui"
ROS_WS_DIR="${BASE_DIR}/ros2_ws"

echo "[launcher] Khoi dong robot stack + UI"
cd "${ROBOT_UI_DIR}"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/jetson/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"

echo "[launcher] Doi desktop san sang"
for _ in $(seq 1 30); do
    if [ -S /tmp/.X11-unix/X0 ]; then
        break
    fi
    sleep 1
done

set +u
source /opt/ros/foxy/setup.bash
if [ -f "${ROS_WS_DIR}/install/setup.bash" ]; then
    source "${ROS_WS_DIR}/install/setup.bash"
fi
set -u

echo "[launcher] Don tien trinh cu"
pkill -f "ros2 launch my_robot_nav navigation.launch.py" 2>/dev/null || true
pkill -f "rosbridge_websocket" 2>/dev/null || true
pkill -f "rosapi_node" 2>/dev/null || true
pkill -f "ui_goal_bridge.py" 2>/dev/null || true
pkill -f "python3 /home/jetson/mopero/robot_ui/server.py" 2>/dev/null || true
pkill -f "python3 /home/jetson/mopero/robot_ui/run_app.py" 2>/dev/null || true
pkill -f "firefox.*http://localhost:5000" 2>/dev/null || true
pkill -f "chromium.*http://localhost:5000" 2>/dev/null || true
pkill -f "google-chrome.*http://localhost:5000" 2>/dev/null || true

echo "[launcher] Khoi dong ROS robot map stack"
(
    cd "${ROS_WS_DIR}"
    ros2 launch my_robot_nav navigation.launch.py enable_web_ui:=true
) > /tmp/robot_ros_stack.log 2>&1 &
ROS_PID=$!
echo "[launcher] ROS stack pid=${ROS_PID}, log=/tmp/robot_ros_stack.log"

echo "[launcher] Khoi dong AI server"
AI_PORT="${AI_PORT:-5001}" /usr/bin/python3 "${ROBOT_UI_DIR}/server.py" > /tmp/robot_ai_server.log 2>&1 &
AI_PID=$!
echo "[launcher] AI server pid=${AI_PID}, log=/tmp/robot_ai_server.log"

bash "${ROBOT_UI_DIR}/start_ui.sh"
