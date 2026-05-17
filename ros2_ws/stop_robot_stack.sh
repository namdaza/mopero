#!/usr/bin/env bash
set -e

pkill -f "ros2 launch my_robot_nav navigation.launch.py" >/dev/null 2>&1 || true
pkill -f "rosbridge_websocket" >/dev/null 2>&1 || true
pkill -f "rosapi_node" >/dev/null 2>&1 || true
pkill -f "ui_goal_bridge.py" >/dev/null 2>&1 || true
pkill -f "python3 -m http.server 8000" >/dev/null 2>&1 || true
pkill -f "sllidar_node" >/dev/null 2>&1 || true
pkill -f "serial_bridge" >/dev/null 2>&1 || true
pkill -f "amcl" >/dev/null 2>&1 || true
pkill -f "controller_server" >/dev/null 2>&1 || true
pkill -f "planner_server" >/dev/null 2>&1 || true
pkill -f "bt_navigator" >/dev/null 2>&1 || true
pkill -f "python3 /home/jetson/mopero/robot_ui/server.py" >/dev/null 2>&1 || true
pkill -f "python3 /home/jetson/mopero/robot_ui/run_app.py" >/dev/null 2>&1 || true
pkill -f "firefox.*http://localhost:5000" >/dev/null 2>&1 || true
pkill -f "chromium.*http://localhost:5000" >/dev/null 2>&1 || true
pkill -f "google-chrome.*http://localhost:5000" >/dev/null 2>&1 || true

echo "Stopped old robot stack processes."
