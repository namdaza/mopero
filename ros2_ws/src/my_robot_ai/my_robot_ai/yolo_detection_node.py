#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import json
import numpy as np
import traceback
import cv2
import os
from ultralytics import YOLO

# --- TUYỆT CHIÊU MONKEY PATCHING (ÉP NHÂN HỆ THỐNG NHẬN KPT_SHAPE) ---
from ultralytics.nn.autobackend import AutoBackend
AutoBackend.kpt_shape = [17, 3]

class YoloDetectionNode(Node):
    def __init__(self):
        super().__init__('yolo_detection_node')
        self.declare_parameter('model_path', '/home/jetson/ros2_ws/src/yolov8n-pose.engine')
        model_path = self.get_parameter('model_path').value
        
        self.bridge = CvBridge()
        self.get_logger().info(f"🧠 Loading YOLO Engine: {model_path}")
        self.model = YOLO(model_path, task='pose')
        
        self.meta_yaml = '/tmp/pose_meta.yaml'
        with open(self.meta_yaml, 'w') as f:
            f.write("names:\n  0: person\nnc: 1\nkpt_shape: [17, 3]\n")
        
        self.frame_count = 0
        
        self.get_logger().info("🔥 Đang mồi GPU TensorRT ...")
        try:
            dummy_img = np.zeros((320, 320, 3), dtype=np.uint8)
            self.model.predict(dummy_img, data=self.meta_yaml, device=0, verbose=False)
            self.get_logger().info("✅ Warmup xong! Bộ nhớ đã ổn định!")
        except Exception as e:
            self.get_logger().error(f"❌ Lỗi Warmup: {traceback.format_exc()}")
        
        self.det_pub = self.create_publisher(String, '/yolo/detections', 10)
        self.debug_pub = self.create_publisher(Image, '/yolo/debug_image', 1)
        self.image_sub = self.create_subscription(Image, '/image_raw', self.image_cb, 1)

    def image_cb(self, msg):
        self.frame_count += 1
        if self.frame_count % 4 != 0:
            return
            
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            cv_img = cv2.resize(cv_img, (0, 0), fx=0.5, fy=0.5)

            results = self.model.predict(cv_img, data=self.meta_yaml, conf=0.5, classes=[0], device=0, verbose=False)
            
            annotated = results[0].plot()
            self.debug_pub.publish(self.bridge.cv2_to_imgmsg(annotated, "bgr8"))

            detections = []
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                detections.append({
                    'bbox': {'center_x': int((x1+x2)/2), 'width': int(x2-x1), 'height': int(y2-y1)},
                    'image_width': cv_img.shape[1], 'image_height': cv_img.shape[0]
                })
            
            if detections:
                self.det_pub.publish(String(data=json.dumps({'detections': detections})))
        except Exception as e:
            self.get_logger().error(f"[Loop Error]:\n{traceback.format_exc()}")

def main():
    rclpy.init()
    rclpy.spin(YoloDetectionNode())
    rclpy.shutdown()

if __name__ == '__main__':
    main()

