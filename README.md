# ROS2 Jetson Care Robot

ROS2 Jetson Care Robot is an integrated robot software stack for a Jetson Nano based care-assistant robot. The project combines ROS2 Foxy navigation, low-level robot drivers, lidar mapping, a browser-based robot map UI, and a Flask-based AI assistant interface.

The repository is organized as one deployment folder so the Jetson can boot into the main robot UI while starting the ROS2 backend in the background.

## Features

- ROS2 Foxy workspace for robot bringup, localization, mapping, and Nav2 navigation.
- Web robot map UI with live `/map`, AMCL pose display, initial pose setting, and navigation goal publishing.
- `rosbridge_server` WebSocket integration for browser-to-ROS communication.
- AI assistant web UI with a robot face interface and quick navigation buttons.
- Unified startup script for launching ROS navigation, rosbridge, the AI server, and the browser UI.
- Jetson-friendly shell scripts for startup, shutdown, and udev device rules.

## Repository Layout

```text
.
├── robot_ui/
│   ├── app/                         # Flask routes and admin logic
│   ├── robot_launcher/
│   │   ├── start_robot_stack.sh      # Main startup entrypoint
│   │   └── install_robot_stack_service.sh
│   ├── static/                      # UI CSS and JavaScript
│   ├── templates/                   # Main UI and map UI pages
│   ├── run_app.py
│   ├── server.py
│   └── start_ui.sh
└── ros2_ws/
    ├── src/
    │   ├── my_robot_ai/             # AI / human following ROS nodes
    │   ├── my_robot_description/    # URDF and meshes
    │   ├── my_robot_driver/         # Serial, sonar, scan filter, camera drivers
    │   ├── my_robot_nav/            # Mapping, AMCL, Nav2, map UI bridge
    │   └── sllidar_ros2/            # SLLIDAR ROS2 driver
    ├── install_udev_rules.sh
    └── stop_robot_stack.sh
```

## Runtime Architecture

```text
Browser UI
  ├── Main AI assistant page: http://localhost:5000/
  └── Robot map page:       http://localhost:5000/map

Flask backend
  └── robot_ui/server.py

ROS2 backend
  ├── my_robot_nav navigation.launch.py
  ├── map_server + AMCL + Nav2
  ├── rosbridge_server on ws://<jetson-ip>:9090
  └── ui_goal_bridge.py for browser navigation goals
```

The main UI includes a **Bản đồ** button that opens the robot map page. The map page connects to `rosbridge` on port `9090`, subscribes to the ROS map and robot pose, and publishes pose/goal commands.

## Hardware Assumptions

- Jetson Nano running Ubuntu 20.04 based JetPack.
- ROS2 Foxy installed at `/opt/ros/foxy`.
- Differential-drive robot base controlled through Arduino serial.
- SLLIDAR device available through the configured lidar port.
- Optional sonar Arduino device for range sensors.
- USB camera for the AI / camera node.

Device names are expected to be provided by udev rules, for example:

- `/dev/arduino_motor`
- `/dev/arduino_sonar`

## Installation

Clone this repository on the Jetson:

```bash
cd ~
git clone https://github.com/namdaza/ros2-jetson-care-robot.git mopero
cd ~/mopero
```

Install ROS2 Foxy and required ROS packages first. Typical required packages include:

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  ros-foxy-navigation2 \
  ros-foxy-nav2-bringup \
  ros-foxy-slam-toolbox \
  ros-foxy-robot-state-publisher \
  ros-foxy-joint-state-publisher \
  ros-foxy-v4l2-camera \
  ros-foxy-rosbridge-server
```

Install Python dependencies for the UI as needed by the Flask application:

```bash
cd ~/mopero/robot_ui
python3 -m pip install -r requirements.txt
```

If `requirements.txt` is not present, install the app dependencies used by your current UI server manually.

## Configuration & Environment Setup

The Flask AI assistant server requires a Google Gemini API Key to handle Speech-to-Text (STT) and assistant response generation. Follow these steps to configure the environment:

1. Copy the `.env.example` file in `robot_ui` to a new file named `.env`:
   ```bash
   cd ~/mopero/robot_ui
   cp .env.example .env
   ```

2. Open the `.env` file and set your actual Gemini API key:
   ```env
   API_KEY=AIzaSyYourActualKeyHere
   ```
   > [!IMPORTANT]
   > You can get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/).
   > **Never commit your `.env` file containing the actual key!** The `.gitignore` is configured to isolate `.env` and prevent it from being pushed to GitHub.

3. Optional configuration parameters in `robot_ui/.env`:
   - `AI_MODEL`: Set a specific Gemini model (defaults to `gemini-2.5-flash`).
   - `AI_PORT`: Set the port on which the AI backend server runs (defaults to `5001`).

## Build ROS2 Workspace

Build from the new repository path:

```bash
cd ~/mopero/ros2_ws
source /opt/ros/foxy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Confirm the navigation package is visible:

```bash
ros2 pkg prefix my_robot_nav
```

Expected output:

```text
/home/jetson/mopero/ros2_ws/install/my_robot_nav
```

## Udev Rules

Install device rules after connecting the robot hardware:

```bash
cd ~/mopero/ros2_ws
./install_udev_rules.sh
```

Then reconnect USB devices or reload udev:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Check devices:

```bash
ls -l /dev/arduino_motor /dev/arduino_sonar
```

## Start The Robot Stack

The main entrypoint is:

```bash
cd ~/mopero/robot_ui/robot_launcher
./start_robot_stack.sh
```

It starts:

- ROS2 navigation stack.
- `rosbridge_server` on port `9090`.
- UI goal bridge.
- Flask AI assistant server on port `5000`.
- Browser kiosk page for the main UI.

Open from the Jetson:

```text
http://localhost:5000/
```

Open from another computer on the same network:

```text
http://<jetson-ip>:5000/
```

The robot map page is available at:

```text
http://<jetson-ip>:5000/map
```

## Stop The Robot Stack

```bash
cd ~/mopero/ros2_ws
./stop_robot_stack.sh
```

## Check Runtime Status

Check Flask UI:

```bash
ss -lntp | grep 5000
```

Check rosbridge:

```bash
ss -lntp | grep 9090
```

Check ROS startup logs:

```bash
tail -160 /tmp/robot_ros_stack.log
```

Check UI startup logs:

```bash
tail -160 /tmp/mopero_start_robot_stack.log
tail -160 /tmp/robot_ai_server.log
```

## Navigation Workflow

1. Start the robot stack.
2. Open the main UI.
3. Click **Bản đồ**.
4. Wait for the map page to show `Connected`.
5. Use **Initial Pose** to set the robot pose on the map.
6. Use **Nav Goal** to click a target pose.
7. Watch Nav2 logs for accepted goals and controller output.

Useful ROS checks:

```bash
ros2 topic list
ros2 topic echo /amcl_pose
ros2 action list | grep -E 'navigate|follow|compute'
ros2 node list
```

## Common Issues

### Robot map shows Disconnected

Check whether rosbridge is listening:

```bash
ss -lntp | grep 9090
```

If nothing is listening, inspect:

```bash
tail -160 /tmp/robot_ros_stack.log
```

### `Package 'my_robot_nav' not found`

The ROS workspace was not built from the current path. Rebuild:

```bash
cd ~/mopero/ros2_ws
rm -rf build install log
source /opt/ros/foxy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### Nav2 does not move after sending a goal

Check transforms and localization:

```bash
ros2 run tf2_tools view_frames.py
ros2 topic echo /amcl_pose
```

The robot must have a valid initial pose and the TF chain must include `map -> odom -> base_footprint`.

### Sonar device missing

If logs show `/dev/arduino_sonar` is missing, reconnect the sonar controller or update udev rules. Navigation can still start, but range-layer behavior may be degraded depending on configuration.

## Development Notes

- Do not commit `ros2_ws/build`, `ros2_ws/install`, or `ros2_ws/log`.
- Do not commit `.env` files or browser profile folders.
- Rebuild the ROS workspace after editing launch files, package manifests, scripts installed by CMake, or package dependencies.
- Keep `robot_ui/robot_launcher/start_robot_stack.sh` as the main startup entrypoint for boot and manual operation.

## License

This project currently does not declare a formal license. Add a license before publishing for external reuse.
