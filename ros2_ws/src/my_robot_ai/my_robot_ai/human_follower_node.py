#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Range
import json
import time
import math
from collections import deque

class HumanFollowerNode(Node):
    def __init__(self):
        super().__init__('human_follower_node')

        self.declare_parameter('target_distance', 1.5)  # Dừng cách người 1.5m
        self.declare_parameter('max_linear_speed', 0.08) # Giới hạn 8 cm/s theo motor
        self.declare_parameter('max_angular_speed', 0.5)
        self.declare_parameter('emergency_distance', 0.30)
        self.declare_parameter('person_real_height', 1.70)
        self.declare_parameter('camera_vertical_fov', 1.047)

        self.target_dist = self.get_parameter('target_distance').value
        self.max_lin = self.get_parameter('max_linear_speed').value
        self.max_ang = self.get_parameter('max_angular_speed').value
        self.emergency_dist = self.get_parameter('emergency_distance').value
        self.person_height = self.get_parameter('person_real_height').value
        self.vfov = self.get_parameter('camera_vertical_fov').value

        self.sonar_ranges = {'left': 2.0, 'center': 2.0, 'right': 2.0}
        self.distance_history = deque(maxlen=5)
        self.last_person_time = 0.0
        self.last_person_bbox = None

        # ── Chống dao động (oscillation) do FPS thấp ─────────────────────────────
        self.smooth_error_x = 0.0    # EMA của error_x
        self.prev_angular   = 0.0    # Lưu angular lần trước để rate-limit

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.det_sub = self.create_subscription(String, '/yolo/detections', self.det_cb, 10)
        self.sonar_c_sub = self.create_subscription(Range, '/sonar_center', self.sonar_c_cb, 10)

        self.timer = self.create_timer(0.1, self.control_loop)
        self.get_logger().info("🚶 Human Follower JSON Version Đã Khởi Động!")

    def sonar_c_cb(self, msg): self.sonar_ranges['center'] = msg.range

    def det_cb(self, msg):
        try: data = json.loads(msg.data)
        except: return
        detections = data.get('detections', [])
        if not detections: return
        
        # Chọn người to nhất
        best = max(detections, key=lambda d: d['bbox']['width'] * d['bbox']['height'])
        self.last_person_bbox = best
        self.last_person_time = time.time()

    def control_loop(self):
        cmd = Twist()
        now = time.time()

        if self.sonar_ranges['center'] < self.emergency_dist:
            self.cmd_pub.publish(cmd)
            return

        if self.last_person_bbox is None or (now - self.last_person_time) > 2.0:
            self.cmd_pub.publish(cmd)
            self.distance_history.clear()
            return

        bbox = self.last_person_bbox['bbox']
        img_w = self.last_person_bbox['image_width']
        img_h = self.last_person_bbox['image_height']

        error_x = (bbox['center_x'] - img_w / 2.0) / img_w
        bbox_height = bbox['height']
        
        if bbox_height > 0:
            focal_length = img_h / (2.0 * math.tan(self.vfov / 2.0))
            raw_dist = (self.person_height * focal_length) / bbox_height
            self.distance_history.append(raw_dist)

        if not self.distance_history: return
        est_distance = sum(self.distance_history) / len(self.distance_history)

        # ── EMA smoothing trên error_x ──────────────────────────────────────────
        # alpha nhỏ = mượt hơn nhưng chậm hơn | alpha lớn = nhạy hơn nhưng dễ rung
        alpha = 0.2   # 0.4 → 0.3: mượt hơn
        self.smooth_error_x = alpha * error_x + (1 - alpha) * self.smooth_error_x

        # ── Angular deadband ──────────────────────────────────────────────────────
        # Nếu người gần giữa khung hình (err_x < 12%) thì không quay
        if abs(self.smooth_error_x) < 0.12:   # 0.08 → 0.12: deadband rộng hơn
            angular = 0.0
        else:
            angular = -2.0 * self.smooth_error_x   # Giảm gain 3.0 → 2.0
            angular = max(-self.max_ang, min(self.max_ang, angular))
            # Đảm bảo angular vượt ngưỡng tối thiểu motor
            if abs(angular) < 0.25:
                angular = math.copysign(0.25, angular)

        # ── Rate limiter: giới hạn tốc độ thay đổi angular mỗi bước ────────────────
        # Khi FPS thấp, mỗi 100ms không được đổi chiều đột ngột quá mạnh
        max_delta = 0.08   # rad/s mỗi bước — 0.10 → 0.08: đổi chiều chậm hơn
        delta = angular - self.prev_angular
        if abs(delta) > max_delta:
            angular = self.prev_angular + math.copysign(max_delta, delta)
        self.prev_angular = angular

        distance_error = est_distance - self.target_dist
        if abs(distance_error) < 0.15:       # deadzone nhỏ để robot dễ di chuyển hơn
            linear = 0.0
        else:
            linear = 0.4 * distance_error
            # Không cho lùi: clamp về [0, max_lin]
            linear = max(0.0, min(self.max_lin, linear))
            # Đảm bảo vượt ngưỡng tối thiểu motor nếu cần tiến
            if 0 < linear < 0.05:
                linear = 0.05

        # Chỉ giảm linear khi angular RẤT lớn (> 70% max), tránh triệt tiêu hoàn toàn
        if abs(angular) > self.max_ang * 0.7:
            linear *= 0.5

        cmd.linear.x = linear
        cmd.angular.z = angular
        self.cmd_pub.publish(cmd)

        # Debug log để theo dõi pipeline
        self.get_logger().info(
            f"dist={est_distance:.2f}m | err_x={error_x:.2f} | "
            f"lin={cmd.linear.x:.3f} ang={cmd.angular.z:.3f}"
        )

def main(args=None):
    rclpy.init(args=args)
    node = HumanFollowerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
