# ROS2 Jetson Care Robot

![ROS 2](https://img.shields.io/badge/ROS%202-Foxy-22314E?logo=ros)
![Ubuntu](https://img.shields.io/badge/Ubuntu-20.04-E95420?logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-NVIDIA%20Jetson-76B900?logo=nvidia&logoColor=white)
![Status](https://img.shields.io/badge/Status-Prototype-yellow)

Robot chăm sóc/hỗ trợ chạy trên **NVIDIA Jetson + ROS 2 Foxy**, dùng Arduino để điều khiển đế vi sai, RPLIDAR để định vị và tránh vật cản, sonar để tăng an toàn, camera + YOLO để bám theo người, và giao diện Flask kiosk tích hợp trợ lý AI giọng nói tiếng Việt.

> Repository này đang ở giai đoạn prototype/thực nghiệm trên robot thật.

## Mục Lục

- [Tổng quan](#tổng-quan)
- [Tính năng](#tính-năng)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Phần cứng](#phần-cứng)
- [Yêu cầu phần mềm](#yêu-cầu-phần-mềm)
- [Cài đặt nhanh](#cài-đặt-nhanh)
- [Chạy ROS 2](#chạy-ros-2)
- [Chạy Robot UI và AI server](#chạy-robot-ui-và-ai-server)
- [Các topic ROS chính](#các-topic-ros-chính)
- [Arduino serial protocol](#arduino-serial-protocol)
- [Bảo mật và biến môi trường](#bảo-mật-và-biến-môi-trường)
- [Ghi chú trước khi public GitHub](#ghi-chú-trước-khi-public-github)
- [Troubleshooting](#troubleshooting)

## Tổng Quan

Dự án gồm hai phần chính:

- `ros2_ws`: workspace ROS 2 Foxy chứa driver robot, URDF, Nav2, SLAM, Lidar, sonar, camera và AI human following.
- `robot_ui`: giao diện Flask chạy kiosk trên Jetson, có màn hình điều khiển đơn giản và trợ lý AI giọng nói tiếng Việt.

Luồng hoạt động chính:

```text
Flask UI
  -> AI server / STT / TTS
  -> Người dùng tương tác bằng giọng nói

ROS 2
  -> Camera + YOLO pose
  -> Human follower
  -> /cmd_vel
  -> Serial bridge
  -> Arduino motor controller
  -> Encoder odometry /odom

RPLIDAR + Sonar
  -> /scan, /sonar_*
  -> SLAM / Nav2 costmap
  -> Navigation an toàn hơn
```

## Tính Năng

- Điều khiển robot differential drive qua `/cmd_vel`.
- Cầu nối serial ROS 2 <-> Arduino motor controller.
- Publish odometry `/odom` và TF `odom -> base_footprint`.
- Đọc RPLIDAR, xoay/lọc góc quét và publish `/scan`.
- Đọc 3 cảm biến siêu âm: trái, giữa, phải.
- Mapping với `slam_toolbox`.
- Navigation với Nav2 và map có sẵn.
- Camera V4L2 publish `/image_raw`.
- YOLO pose TensorRT để phát hiện người.
- Human follower tự tạo vận tốc bám theo người.
- Flask kiosk UI trên port `5000`.
- AI server trên port `5001` hỗ trợ:
  - Speech-to-text bằng Gemini.
  - Chat AI tiếng Việt.
  - Text-to-speech bằng gTTS.

## Kiến Trúc Hệ Thống

| Thành phần | Vai trò |
| --- | --- |
| Jetson Nano | Máy tính chính chạy ROS 2, AI, UI |
| Arduino Uno | Điều khiển motor và đọc encoder |
| Arduino Nano | Đọc sonar |
| RPLIDAR | Cảm biến scan cho SLAM/Nav2 |
| USB camera | Camera cho YOLO và microphone cho UI |
| `my_robot_driver` | Serial bridge, sonar, scan filter |
| `my_robot_description` | URDF, mesh, TF robot |
| `my_robot_nav` | SLAM, Nav2, map, costmap |
| `my_robot_ai` | YOLO detection và human follower |
| `robot_ui` | Giao diện kiosk và AI voice assistant |

## Cấu Trúc Thư Mục

```text
.
├── README.md
├── robot_ui/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   └── routes.py
│   ├── robot_launcher/
│   │   └── start_robot_stack.sh
│   ├── static/
│   │   ├── script.js
│   │   └── style.css
│   ├── templates/
│   │   └── index.html
│   ├── .env.example
│   ├── run_app.py
│   ├── server.py
│   ├── start_ui.sh
│   └── ROBOT_UI_AI_SETUP.md
└── ros2_ws/
    ├── arduino/
    │   └── motor_controller/
    ├── install_udev_rules.sh
    └── src/
        ├── my_robot_ai/
        ├── my_robot_description/
        ├── my_robot_driver/
        ├── my_robot_nav/
        └── sllidar_ros2/
```

## Phần Cứng

Phần cứng đang được cấu hình trong dự án:

- NVIDIA Jetson Nano.
- Arduino Uno R3 cho motor controller.
- Arduino Nano cho sonar.
- 2 động cơ DC 12V có encoder.
- 2 driver BTS7960.
- RPLIDAR.
- USB camera/webcam có microphone.
- Khung robot differential drive.

Thông số robot quan trọng:

| Thông số | Giá trị |
| --- | --- |
| Bán kính bánh | `0.085 m` |
| Khoảng cách hai bánh | `0.3846 m` |
| Tốc độ motor giới hạn | khoảng `23 RPM` |
| Base frame | `base_footprint` |
| Odom frame | `odom` |
| Map frame | `map` |

## Yêu Cầu Phần Mềm

Môi trường khuyến nghị:

- Ubuntu 20.04 trên Jetson.
- ROS 2 Foxy.
- Python 3.8.
- `colcon`.
- `v4l2_camera`.
- `slam_toolbox`.
- `navigation2` / `nav2_bringup`.
- `robot_state_publisher`.
- `joint_state_publisher`.
- `rviz2`.
- `pyserial`.
- `opencv-python`.
- `cv_bridge`.
- `ultralytics`.
- TensorRT runtime phù hợp với Jetson.
- Flask.
- gTTS.

## Cài Đặt Nhanh

Cài một số gói ROS thường dùng:

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  ros-foxy-v4l2-camera \
  ros-foxy-slam-toolbox \
  ros-foxy-navigation2 \
  ros-foxy-nav2-bringup \
  ros-foxy-robot-state-publisher \
  ros-foxy-joint-state-publisher \
  ros-foxy-rviz2
```

Cài dependency Python cho UI:

```bash
python3 -m pip install flask gTTS
```

Cài dependency cho YOLO:

```bash
python3 -m pip install ultralytics opencv-python numpy
```

Tạo file môi trường cho UI/AI:

```bash
cd ~/robot_ui
cp .env.example .env
nano .env
```

Ví dụ nội dung `.env`:

```text
API_KEY=your_real_gemini_api_key
AI_MODEL=gemini-2.5-flash
UI_ADMIN_PASSWORD=your_ui_admin_password
ADMIN_EXIT_PASSWORD=your_kiosk_exit_password
PORT=5000
AI_PORT=5001
```

## Chuẩn Bị Thiết Bị USB

Source ROS 2:

```bash
source /opt/ros/foxy/setup.bash
```

Tạo udev rules cho Lidar, Arduino motor và Arduino sonar:

```bash
cd ~/ros2_ws
sudo ./install_udev_rules.sh
```

Sau khi chạy script, các thiết bị được kỳ vọng có symlink:

```text
/dev/lidar
/dev/arduino_motor
/dev/arduino_sonar
```

## Build ROS 2 Workspace

```bash
cd ~/ros2_ws
source /opt/ros/foxy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Chạy ROS 2

### Robot Driver

Chạy driver Arduino motor:

```bash
ros2 launch my_robot_driver robot_driver.launch.py serial_port:=/dev/arduino_motor
```

Chạy camera:

```bash
ros2 launch my_robot_driver camera.launch.py video_device:=/dev/video0
```

Chạy sonar:

```bash
ros2 launch my_robot_driver sonar.launch.py sonar_port:=/dev/arduino_sonar
```

### Mapping Với SLAM

```bash
cd ~/ros2_ws
source install/setup.bash
ros2 launch my_robot_nav mapping.launch.py \
  lidar_port:=/dev/lidar \
  serial_port:=/dev/arduino_motor \
  sonar_port:=/dev/arduino_sonar
```

Lưu map sau khi mapping:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/src/my_robot_nav/maps/my_room_map
```

### Navigation Với Nav2

```bash
cd ~/ros2_ws
source install/setup.bash
ros2 launch my_robot_nav navigation.launch.py \
  lidar_port:=/dev/lidar \
  serial_port:=/dev/arduino_motor \
  sonar_port:=/dev/arduino_sonar
```

File map mặc định:

```text
ros2_ws/src/my_robot_nav/maps/my_room_map.yaml
```

File tham số Nav2:

```text
ros2_ws/src/my_robot_nav/config/nav2_params.yaml
```

### Human Following

Launch camera, YOLO pose, human follower và serial bridge:

```bash
cd ~/ros2_ws
source install/setup.bash
ros2 launch my_robot_ai human_following.launch.py serial_port:=/dev/arduino_motor
```

Mặc định YOLO node dùng model:

```text
/home/jetson/ros2_ws/src/yolov8n-pose.engine
```

Có thể override bằng ROS parameter:

```bash
ros2 run my_robot_ai yolo_detection --ros-args -p model_path:=/path/to/model.engine
```

## Chạy Robot UI Và AI Server

Chạy UI Flask:

```bash
cd ~/robot_ui
python3 run_app.py
```

Mở trình duyệt:

```text
http://localhost:5000
```

Chạy AI server:

```bash
cd ~/robot_ui
AI_PORT=5001 python3 server.py
```

Chạy launcher đầy đủ UI + AI server:

```bash
bash ~/robot_ui/robot_launcher/start_robot_stack.sh
```

Test endpoint chat:

```bash
curl -sS http://127.0.0.1:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"mấy giờ rồi"}'
```

## Các Topic ROS Chính

| Topic | Kiểu message | Mô tả |
| --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/Twist` | Lệnh vận tốc cho robot |
| `/odom` | `nav_msgs/Odometry` | Odometry từ encoder |
| `/tf` | `tf2_msgs/TFMessage` | Transform robot |
| `/scan_raw` | `sensor_msgs/LaserScan` | Scan gốc từ Lidar |
| `/scan` | `sensor_msgs/LaserScan` | Scan đã lọc/shift |
| `/image_raw` | `sensor_msgs/Image` | Ảnh camera |
| `/yolo/detections` | `std_msgs/String` | Detection JSON từ YOLO |
| `/yolo/debug_image` | `sensor_msgs/Image` | Ảnh debug có annotation |
| `/sonar_left` | `sensor_msgs/Range` | Sonar trái |
| `/sonar_center` | `sensor_msgs/Range` | Sonar giữa |
| `/sonar_right` | `sensor_msgs/Range` | Sonar phải |

## Arduino Serial Protocol

Firmware motor controller nằm ở:

```text
ros2_ws/arduino/motor_controller/motor_controller.ino
```

Giao thức serial:

```text
CMD,<left_rpm>,<right_rpm>
ENC,<left_ticks>,<right_ticks>,<left_rpm>,<right_rpm>
STOP
PID,<kp>,<ki>,<kd>
```

## Bảo Mật Và Biến Môi Trường

Repo này không nên chứa secret thật. Các giá trị nhạy cảm được cấu hình qua `.env` local:

| Biến | Mô tả |
| --- | --- |
| `API_KEY` | API key cho Gemini |
| `AI_MODEL` | Model Gemini dùng cho AI server |
| `UI_ADMIN_PASSWORD` | Mật khẩu mở trang quản lý UI |
| `ADMIN_EXIT_PASSWORD` | Mật khẩu thoát kiosk |
| `PORT` | Port của Flask UI |
| `AI_PORT` | Port của AI server |

File `.env` thật đã được ignore bằng `.gitignore`. Chỉ commit file mẫu:

```text
robot_ui/.env.example
```

Khuyến nghị:

- Không upload `.env`.
- Đổi API key nếu key từng bị đưa vào repo hoặc gửi cho người khác.
- Không commit model private hoặc file engine lớn nếu không cần.
- Nếu repo public, cân nhắc bind AI server về `127.0.0.1` khi không cần truy cập từ máy khác.

## Ghi Chú Trước Khi Public GitHub

Repo đã cấu hình `.gitignore` để loại các file không nên push:

- `robot_ui/.env`
- `__pycache__/`
- `*.pyc`
- `ros2_ws/build/`
- `ros2_ws/install/`
- `ros2_ws/log/`
- `.vscode/`
- `*.engine`
- `*.onnx`
- `*.pt`
- `*.bin`

Nếu cần chia sẻ model YOLO, nên dùng một trong các cách sau:

- Đưa link tải model trong README.
- Dùng Git LFS.
- Tạo script hướng dẫn build/export TensorRT engine trên Jetson.

## Troubleshooting

Kiểm tra thiết bị USB:

```bash
ls -l /dev/lidar /dev/arduino_motor /dev/arduino_sonar
ls /dev/ttyUSB* /dev/ttyACM*
```

Kiểm tra topic:

```bash
ros2 topic list
ros2 topic echo /cmd_vel
ros2 topic echo /odom
ros2 topic echo /scan
```

Kiểm tra TF:

```bash
ros2 run tf2_tools view_frames.py
```

Kiểm tra AI server:

```bash
ps aux | grep server.py | grep -v grep
tail -n 100 /tmp/robot_ai_server.log
```

Kiểm tra audio STT:

```bash
file /tmp/robot_last_stt_audio
aplay /tmp/robot_last_stt_audio
```

## License

Một số package trong workspace vẫn còn metadata `TODO` trong `package.xml`. Trước khi phát hành chính thức, nên cập nhật license, maintainer và mô tả package cho đồng bộ.
