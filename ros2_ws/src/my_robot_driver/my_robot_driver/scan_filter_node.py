#!/usr/bin/env python3
"""
Node lọc góc quét Lidar với circular shift (xoay vòng mảng).

Vấn đề với cách cũ (cộng góc + normalize):
  Các điểm gần ranh giới ±π bị "nhảy" sang bên kia → scan bị đứt đoạn.

Cách sửa đúng: Circular array shift
  Thay vì cộng góc, ta dịch chuyển MảNG RANGES theo index.
  Giữ nguyên angle_min/max/increment → không bao giờ có wrapping.

  angle_offset = π (180°): shift_idx = N/2
  → index 0 của output = index N/2 của input (điểm ở 180° = phía sau lidar)
  → Điểm ở 0° output = điểm ở 180° input = phía TRƯỚC robot ✓

Subscribe: /scan_raw  →  Publish: /scan
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import math

class ScanAngleFilter(Node):
    def __init__(self):
        super().__init__('scan_angle_filter')

        self.declare_parameter('angle_offset', 3.14159)  # 180° = đảo lidar gắn ngược
        self.declare_parameter('lower_angle', -1.2217)   # -70°
        self.declare_parameter('upper_angle',  1.2217)   #  70°

        self.offset = self.get_parameter('angle_offset').value
        self.lower  = self.get_parameter('lower_angle').value
        self.upper  = self.get_parameter('upper_angle').value

        self.sub = self.create_subscription(LaserScan, '/scan_raw', self.callback, 10)
        self.pub = self.create_publisher(LaserScan, '/scan', 10)

        self.get_logger().info(
            f'🔭 Scan Filter (circular shift): offset={math.degrees(self.offset):.0f}°, '
            f'giữ [{math.degrees(self.lower):.0f}°, {math.degrees(self.upper):.0f}°]'
        )

    def callback(self, msg: LaserScan):
        N = len(msg.ranges)
        if N == 0 or msg.angle_increment == 0:
            return

        # ─── Bước 1: Circular shift để xoay scan theo angle_offset ──────────
        # Thay vì cộng góc (gây wrapping), ta dịch chuyển INDEX của mảng.
        # shift_idx: số bước cần dịch để bù offset
        shift_idx = round(self.offset / abs(msg.angle_increment)) % N

        ranges_raw = list(msg.ranges)
        intens_raw = list(msg.intensities) if msg.intensities else []

        ranges_shifted = ranges_raw[shift_idx:] + ranges_raw[:shift_idx]
        intens_shifted = (intens_raw[shift_idx:] + intens_raw[:shift_idx]) if intens_raw else []

        # Sau khi shift, góc của mỗi index vẫn là angle_min + i * increment
        # (không thay đổi angle labels, chỉ xoay nội dung mảng)

        # ─── Bước 2: Lọc góc theo lower/upper ───────────────────────────────
        i_start = max(0, math.ceil( (self.lower - msg.angle_min) / msg.angle_increment))
        i_end   = min(N - 1, math.floor((self.upper - msg.angle_min) / msg.angle_increment))

        if i_start > i_end:
            self.get_logger().warn('Không có điểm nào trong vùng lọc! Kiểm tra lower/upper_angle.')
            return

        # ─── Bước 3: Đóng gói và publish ─────────────────────────────────────
        filtered = LaserScan()
        filtered.header          = msg.header
        filtered.angle_min       = msg.angle_min + i_start * msg.angle_increment
        filtered.angle_max       = msg.angle_min + i_end   * msg.angle_increment
        filtered.angle_increment = msg.angle_increment
        filtered.time_increment  = msg.time_increment
        filtered.scan_time       = msg.scan_time
        filtered.range_min       = msg.range_min
        filtered.range_max       = msg.range_max
        filtered.ranges          = ranges_shifted[i_start : i_end + 1]
        filtered.intensities     = intens_shifted[i_start : i_end + 1] if intens_shifted else []

        self.pub.publish(filtered)


def main(args=None):
    rclpy.init(args=args)
    node = ScanAngleFilter()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
