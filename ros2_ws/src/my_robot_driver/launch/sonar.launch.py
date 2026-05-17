from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        # Khai báo argument cho cổng nối Arduino Nano siêu âm, mặc định là /dev/ttyUSB1
        DeclareLaunchArgument(
            'sonar_port',
            default_value='/dev/ttyUSB1',
            description='Path to the Arduino Nano USB device for Sonars'
        ),
        
        # Node sonar
        Node(
            package='my_robot_driver',
            executable='sonar',
            name='sonar_node',
            output='screen',
            parameters=[{
                'serial_port': LaunchConfiguration('sonar_port'),
                'baud_rate': 115200,
            }]
        )
    ])
