import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
import serial

class SonarBridge(Node):
    def __init__(self):
        super().__init__('sonar_bridge_node')
        
        # Mở cổng Serial cắm Arduino Nano
        # (LƯU Ý: Sửa '/dev/ttyUSB1' thành cổng thực tế của Nano)
        self.ser = serial.Serial('/dev/ttyUSB1', 115200, timeout=0.1)

        # Khai báo 3 topic Publisher
        self.pub_left = self.create_publisher(Range, '/sonar_left', 10)
        self.pub_center = self.create_publisher(Range, '/sonar_center', 10)
        self.pub_right = self.create_publisher(Range, '/sonar_right', 10)

        # Hẹn giờ đọc Serial (20Hz)
        self.timer = self.create_timer(0.05, self.read_serial_callback)

    def create_range_msg(self, frame_id, distance_cm):
        msg = Range()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = frame_id
        msg.radiation_type = Range.ULTRASOUND
        msg.field_of_view = 0.52 # Khoảng 30 độ mở 
        msg.min_range = 0.02     # 2cm
        msg.max_range = 2.0      # 2m
        # BẮT BUỘC LỌC NHIỄU DƯỚI 10cm! 
        # Vì Nav2 sử dụng Layer ghép dạng MAX(), Lidar KHÔNG rà quét chém bỏ lỗi của Sonar. Cảm biến Sonar tự dọn khoảng không của chính nó.
        # Nhiễu 2cm sẽ khiến Sonar tạo mìn vĩnh cửu. Phải chặn từ gốc.
        if distance_cm == 0 or distance_cm < 10:
            msg.range = 2.0
        else:
            msg.range = distance_cm / 100.0 # Đổi cm sang mét
            
        return msg

    def read_serial_callback(self):
        try:
            # Nếu có dữ liệu đang chờ trong cổng USB
            if self.ser.in_waiting > 0:
                # BƯỚC QUAN TRỌNG: Xả bỏ toàn bộ dữ liệu cũ bị kẹt
                self.ser.reset_input_buffer() 
                
                # Chờ một chút để đọc trọn vẹn 1 dòng mới nhất
                line = self.ser.readline().decode('utf-8').strip()
                data = line.split(',')
                
                # Check header là chữ 'S' và đủ 4 phần tử
                if len(data) == 4 and data[0] == 'S':
                    dist_l = int(data[1])
                    dist_c = int(data[2])
                    dist_r = int(data[3])

                    # Publish 3 thông điệp
                    self.pub_left.publish(self.create_range_msg('sonar_left_link', dist_l))
                    self.pub_center.publish(self.create_range_msg('sonar_center_link', dist_c))
                    self.pub_right.publish(self.create_range_msg('sonar_right_link', dist_r))
                    
        except Exception as e:
            pass # Bỏ qua các lỗi rác Serial

def main(args=None):
    rclpy.init(args=args)
    node = SonarBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

