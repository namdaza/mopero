import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():

    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='Cổng USB kết nối với Arduino (/dev/ttyUSB0 hoặc /dev/ttyACM0)'
    )

    # ── 1. Camera (v4l2) ─────────────────────────────────────────────────────
    camera_node = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='camera_node',
        output='screen',
        parameters=[{
            'video_device': '/dev/video0',
            'image_size': [320, 240],
            'pixel_format': 'YUYV',
            'camera_frame_id': 'camera_link_optical',
        }]
    )

    # ── 2. YOLO Detection ─────────────────────────────────────────────────────
    yolo_node = Node(
        package='my_robot_ai',
        executable='yolo_detection',
        name='yolo_detection_node',
        output='screen'
    )

    # ── 3. Human Follower (tính toán cmd_vel) ─────────────────────────────────
    follower_node = Node(
        package='my_robot_ai',
        executable='human_follower',
        name='human_follower_node',
        output='screen'
    )

    # ── 4. Serial Bridge (gửi cmd_vel xuống Arduino) ──────────────────────────
    serial_bridge_node = Node(
        package='my_robot_driver',
        executable='serial_bridge',
        name='serial_bridge_node',
        output='screen',
        parameters=[{
            'serial_port':  LaunchConfiguration('serial_port'),  # ← nhận từ argument
            'baud_rate':    115200,
            'wheel_radius': 0.085,    # ← khớp với serial_bridge_node.py
            'wheel_base':   0.3846,   # ← khớp với serial_bridge_node.py
            'max_rpm':      23.0,
        }]
    )

    return LaunchDescription([
        serial_port_arg,
        camera_node,
        yolo_node,
        follower_node,
        serial_bridge_node,
    ])
