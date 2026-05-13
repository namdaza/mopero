from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        # Khai báo argument cho cổng camera, mặc định là /dev/video0
        DeclareLaunchArgument(
            'video_device',
            default_value='/dev/video0',
            description='Path to the video device USB/CSI'
        ),
        
        # Node v4l2_camera
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera_node',
            output='screen',
            parameters=[{
                'video_device': LaunchConfiguration('video_device'),
                'image_size': [320, 240], # Hạ cực thấp độ phân giải để siêu mượt
                'pixel_format': 'YUYV',
                'camera_frame_id': 'camera_link_optical' # Khớp với TF rviz
            }]
        )
    ])
