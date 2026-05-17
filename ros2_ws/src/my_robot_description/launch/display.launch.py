import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # Lấy đường dẫn tới share directory của package
    pkg_share = get_package_share_directory('my_robot_description')
    
    # Đường dẫn file URDF
    urdf_file = os.path.join(pkg_share, 'urdf', 'robot.urdf')
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()
        
    return LaunchDescription([
        # Node phát biến đổi tọa độ TF từ nội dung URDF
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_desc}]
        ),
        # Node hiển thị thanh trượt gạt chỉnh góc các khớp giả lập
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen'
        ),
        # Node khởi chạy RViz2
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        )
    ])
