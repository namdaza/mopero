import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():

    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/lidar',
        description='USB port of RPLidar'
    )
    arduino_port_arg = DeclareLaunchArgument(
        'serial_port', default_value='/dev/arduino_motor',
        description='USB port of Arduino'
    )
    sonar_port_arg = DeclareLaunchArgument(
        'sonar_port', default_value='/dev/arduino_sonar',
        description='USB port of Arduino Nano for Sonar'
    )
    map_yaml_arg = DeclareLaunchArgument(
        'map', default_value=os.path.join(
            get_package_share_directory('my_robot_nav'), 'maps', 'my_room_map.yaml'),
        description='Full path to map yaml file to load'
    )
    params_file_arg = DeclareLaunchArgument(
        'params_file', default_value=os.path.join(
            get_package_share_directory('my_robot_nav'), 'config', 'nav2_params.yaml'),
        description='Full path to the ROS2 parameters file to use for all launched nodes'
    )

    # --- Driver Arduino ---
    driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('my_robot_driver'), 'launch', 'robot_driver.launch.py')
        ]),
        launch_arguments={'serial_port': LaunchConfiguration('serial_port')}.items()
    )

    # --- Camera Driver ---
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('my_robot_driver'), 'launch', 'camera.launch.py')
        ])
    )

    # --- Sonar Driver ---
    sonar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('my_robot_driver'), 'launch', 'sonar.launch.py')
        ]),
        launch_arguments={'sonar_port': LaunchConfiguration('sonar_port')}.items()
    )

    # --- URDF → Robot State Publisher ---
    urdf_file = os.path.join(get_package_share_directory('my_robot_description'), 'urdf', 'robot.urdf')
    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': False}]
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
    )

    # --- Lidar A1: xuất ra /scan_raw → qua bộ lọc Python ---
    sllidar_node = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='sllidar_node',
        output='screen',
        parameters=[{
            'serial_port': LaunchConfiguration('lidar_port'),
            'serial_baudrate': 115200,
            'frame_id': 'lidar_link',
            'inverted': False,
            'angle_compensate': True,
        }],
        remappings=[('/scan', '/scan_raw')]
    )

    scan_filter_node = Node(
        package='my_robot_driver',
        executable='scan_filter',
        name='scan_angle_filter',
        output='screen',
        parameters=[{
            'angle_offset': 3.14159,
            'lower_angle': -1.2217,
            'upper_angle':  1.2217,
        }]
    )

    # --- Navigation 2 Bringup (thay thế SLAM) ---
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')
        ]),
        launch_arguments={
            'use_sim_time': 'False',
            'map': LaunchConfiguration('map'),
            'params_file': LaunchConfiguration('params_file')
        }.items()
    )

    return LaunchDescription([
        lidar_port_arg,
        arduino_port_arg,
        sonar_port_arg,
        map_yaml_arg,
        params_file_arg,
        driver_launch,
        camera_launch,
        sonar_launch,
        robot_state_publisher,
        joint_state_publisher,
        sllidar_node,
        scan_filter_node,
        nav2_bringup,
    ])
