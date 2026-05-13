from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        # Cấu hình cổng Serial (mặc định /dev/ttyUSB0, có thể override khi launch)
        DeclareLaunchArgument(
            'serial_port',
            default_value='/dev/ttyUSB0',
            description='Cổng USB kết nối với Arduino'
        ),

        # Node cầu nối Serial ↔ ROS 2
        Node(
            package='my_robot_driver',
            executable='serial_bridge',
            name='serial_bridge_node',
            output='screen',
            parameters=[{
                'serial_port': LaunchConfiguration('serial_port'),
                'baud_rate':   115200,
                'wheel_radius': 0.0813,
                'wheel_base':   0.37817,
                'max_rpm':      23.0,
            }]
        ),
    ])

