#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import serial
import threading
import time
from sensor_msgs.msg import Range

class SonarNode(Node):
    def __init__(self):
        super().__init__('sonar_node')
        
        self.declare_parameter('serial_port', '/dev/ttyUSB1')
        self.declare_parameter('baud_rate', 115200)
        
        port = self.get_parameter('serial_port').value
        baud = self.get_parameter('baud_rate').value
        
        self.pub_left = self.create_publisher(Range, 'sonar_left', 10)
        self.pub_center = self.create_publisher(Range, 'sonar_center', 10)
        self.pub_right = self.create_publisher(Range, 'sonar_right', 10)
        
        self.msg_count = 0
        
        try:
            self.ser = serial.Serial(port, baud, timeout=1.0)
            time.sleep(2.0)  # Chờ Arduino Nano khởi động xong
            self.ser.reset_input_buffer()  # Xả dữ liệu rác ban đầu
            self.get_logger().info(f"✅ Kết nối siêu âm thành công: {port} @ {baud}")
        except Exception as e:
            self.get_logger().error(f"❌ Lỗi kết nối siêu âm: {e}")
            self.get_logger().error(f"   Kiểm tra: ls /dev/ttyUSB*")
            self.ser = None
            
        self.running = True
        self.read_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
        self.read_thread.start()

    def create_range_msg(self, frame_id, distance_cm):
        msg = Range()
        # Lùi thời gian về quá khứ 100ms để khớp nhịp vòng lặp TF (tránh lỗi Timeout của Nav2)
        now_ns = self.get_clock().now().nanoseconds
        past_ns = max(0, now_ns - 100000000)
        msg.header.stamp.sec = past_ns // 1000000000
        msg.header.stamp.nanosec = past_ns % 1000000000
        msg.header.frame_id = frame_id
        msg.radiation_type = Range.ULTRASOUND
        msg.field_of_view = 0.52  # ~30 degrees
        msg.min_range = 0.02
        msg.max_range = 2.0
        
        if distance_cm == 0:
            msg.range = 2.0  # Ngoài tầm = an toàn
        else:
            msg.range = min(distance_cm / 100.0, 2.0)  # Chuyển cm -> m, giới hạn tối đa 2m
            
        return msg

    def read_serial_loop(self):
        empty_count = 0
        while rclpy.ok() and self.running and self.ser:
            try:
                raw = self.ser.readline()
                if not raw:
                    empty_count += 1
                    if empty_count == 10:
                        self.get_logger().warn("🔇 Arduino Nano im lặng 10 lần liên tiếp, kiểm tra dây cắm và code!")
                    continue
                    
                line = raw.decode('utf-8', errors='ignore').strip()
                
                # Log 5 dòng đầu tiên để debug
                if self.msg_count < 5:
                    self.get_logger().info(f"📡 Serial raw: '{line}'")
                
                if line.startswith('S,'):
                    parts = line.split(',')
                    if len(parts) == 4:
                        try:
                            dL = int(parts[1])
                            dC = int(parts[2])
                            dR = int(parts[3])
                            
                            self.pub_left.publish(self.create_range_msg('sonar_left_link', dR))
                            self.pub_center.publish(self.create_range_msg('sonar_center_link', dC))
                            self.pub_right.publish(self.create_range_msg('sonar_right_link', dL))
                            
                            self.msg_count += 1
                            if self.msg_count == 1:
                                self.get_logger().info(f"🟢 Siêu âm hoạt động! L={dL}cm C={dC}cm R={dR}cm")
                            elif self.msg_count % 100 == 0:
                                self.get_logger().info(f"📊 Đã publish {self.msg_count} bản tin siêu âm")
                        except ValueError:
                            self.get_logger().warn(f"⚠️ Dữ liệu rác: '{line}'")
                    else:
                        if self.msg_count < 5:
                            self.get_logger().warn(f"⚠️ Sai format ({len(parts)} phần): '{line}'")
                else:
                    empty_count = 0  # Reset đếm nếu có data khác
                    if self.msg_count < 5:
                        self.get_logger().info(f"🔍 Dòng không phải sonar: '{line}'")
                        
            except Exception as e:
                self.get_logger().warn(f"❌ Lỗi đọc siêu âm: {e}")

    def destroy_node(self):
        self.running = False
        if self.ser:
            self.ser.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = SonarNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
