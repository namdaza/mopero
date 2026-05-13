# 📋 History — ROS2 Human Following Project

---

## 🗓️ 2026-04-19 — Debug & Fix Human Following

### Bối cảnh
Robot không di chuyển khi chạy `human_follower_node` dù YOLO đang nhận diện người.

---

### 🔍 Nguyên nhân phát hiện

| # | Vấn đề | File |
|---|--------|------|
| 1 | **Launch file thiếu `serial_bridge_node` và `camera_node`** → `/cmd_vel` publish nhưng không ai nhận | `human_following.launch.py` |
| 2 | **Deadzone quá nhỏ** (0.2m) trong khi ước tính khoảng cách bằng bbox dao động ±0.3m → `linear=0` liên tục | `human_follower_node.py` |
| 3 | **Angular gain quá nhỏ** (1.5) → angular chỉ 0.1–0.15 rad/s → tương đương ~2–3 RPM → không đủ thắng ma sát tĩnh motor | `human_follower_node.py` |
| 4 | **Không có ngưỡng tối thiểu** cho linear/angular → motor nhận lệnh quá nhỏ, không quay | `human_follower_node.py` |
| 5 | **`serial_port` hardcode** trong launch → truyền `serial_port:=/dev/ttyACM0` bị bỏ qua | `human_following.launch.py` |
| 6 | **`wheel_radius` sai** trong `robot_driver.launch.py` (0.0813 vs 0.085 trong code) | `robot_driver.launch.py` |
| 7 | **Angular ngặt giảm linear** khi `angular > 40% max` → `linear *= 0.3` = 0.024 m/s → motor không quay | `human_follower_node.py` |

---

### ✅ Các thay đổi đã thực hiện

#### `my_robot_ai/my_robot_ai/human_follower_node.py`

```
[THAY ĐỔI] target_distance:       1.5m  → 1.5m (reset sau khi test ở 1.0m)
[THAY ĐỔI] deadzone:              0.2m  → 0.15m
[THAY ĐỔI] angular gain:          1.5   → 3.0
[THÊM]     min angular speed:     none  → 0.25 rad/s (≈ 5 RPM)
[THÊM]     min linear speed:      none  → 0.05 m/s
[THAY ĐỔI] angular reduce thresh: 40%   → 70% max (bớt hung hãng)
[THAY ĐỔI] linear clamp:          [-max, max] → [0, max] (không cho lùi)
[THÊM]     debug log mỗi 100ms:   dist, err_x, lin, ang
```

#### `my_robot_ai/launch/human_following.launch.py`

```
[THÊM]    camera_node (v4l2_camera) — bị thiếu hoàn toàn
[THÊM]    serial_bridge_node        — bị thiếu hoàn toàn
[THÊM]    DeclareLaunchArgument('serial_port', default='/dev/ttyUSB0')
[SỬA]     serial_port hardcode → LaunchConfiguration('serial_port')
```

---

### 📊 Kết quả

- Robot **đã chạy** sau khi thêm `serial_bridge_node` vào launch file
- Robot **tiến theo người** và **dừng ở khoảng cách 1.5m**
- Robot **không lùi** khi người lại gần hơn 1.5m
- Motor angular hoạt động ổn định nhờ min threshold 0.25 rad/s

---

### 🚀 Lệnh khởi chạy

```bash
cd ~/ros2_ws
source install/setup.bash

# Mặc định (Arduino tại /dev/ttyUSB0):
ros2 launch my_robot_ai human_following.launch.py

# Nếu Arduino tại /dev/ttyACM0:
ros2 launch my_robot_ai human_following.launch.py serial_port:=/dev/ttyACM0
```

> **Lưu ý**: Package `my_robot_ai` đã được build với `--symlink-install`.
> Chỉ cần restart node sau khi sửa file `.py`, không cần build lại.

---

### 📐 Thông số hiện tại (sau tất cả fix)

| Tham số | Giá trị |
|---------|---------|
| `target_distance` | 1.5 m |
| `max_linear_speed` | 0.08 m/s |
| `max_angular_speed` | 0.5 rad/s |
| `min_linear_speed` | 0.05 m/s |
| `min_angular_speed` | 0.25 rad/s |
| `deadzone` | ±0.15 m |
| `emergency_distance` (sonar) | 0.30 m |
| `angular_gain` | 2.0 (giảm từ 3.0) |
| `angular_deadband` | 8% khung hình |
| `ema_alpha` | 0.4 |
| `rate_limit_angular` | 0.10 rad/s/cycle |
| Cho phép lùi | ❌ Không |

---

### 🗂️ Cấu trúc pipeline

```
[USB Camera /dev/video0]
        ↓ /image_raw
[yolo_detection_node]  ←  yolov8n-pose.engine (TensorRT)
        ↓ /yolo/detections (JSON String)
[human_follower_node]
        ↓ /cmd_vel (Twist)
[serial_bridge_node]
        ↓ Serial CMD,rpm_left,rpm_right
[Arduino] → Motor trái / Motor phải
```

---

## 🗓️ 2026-04-19 — Fix Oscillation (dao động trái/phải)

### Bối cảnh
Robot chạy được nhưng khi quay sang một bên, khung hình cập nhật không kịp (FPS thấp ~5-7 FPS thực tế) dẫn tới robot bị dao động trái-phải liên tục.

### 🔍 Nguyên nhân
YOLO chạy chậm → feedback loop latency ~150–200ms → robot quay xong mới nhận frame mới → đã overshoot → quay ngược lại → oscillation.

### ✅ Thay đổi — `human_follower_node.py`

```
[THÊM]     EMA smoothing trên error_x   alpha=0.4 (làm mịn tín hiệu qua các frame)
[THÊM]     Angular deadband             err_x < 8% → angular = 0 (không rung nhỏ)
[THAY ĐỔI] Angular gain                 3.0 → 2.0 (bớt aggressive)
[THÊM]     Rate limiter angular         max delta = 0.10 rad/s/cycle (không flip đột ngột)
[THÊM]     self.smooth_error_x          state variable EMA
[THÊM]     self.prev_angular            state variable rate limiter
```

### 📐 Cách hoạt động

| Lớp | Cơ chế | Tác dụng |
|-----|--------|----------|
| EMA filter | `smooth = 0.4*raw + 0.6*prev` | Loại bỏ nhiễu frame đơn lẻ |
| Deadband 8% | `if \|err_x\| < 0.08: angular=0` | Dừng rung khi người ≈ giữa hình |
| Rate limiter | `Δangular ≤ 0.10 rad/s/cycle` | Ngăn đổi chiều đột ngột |

### 💡 Tinh chỉnh nếu cần

| Hiện tượng | Điều chỉnh |
|------------|------------|
| Vẫn còn rung | Giảm `alpha` từ `0.4` → `0.25` |
| Phản ứng chậm quá | Tăng `alpha` từ `0.4` → `0.5` |
| Không chịu xoay | Giảm deadband từ `0.08` → `0.05` |
| Xoay quá nhiều | Tăng deadband từ `0.08` → `0.12` |
