from setuptools import setup

package_name = 'my_robot_driver'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/robot_driver.launch.py', 'launch/camera.launch.py', 'launch/sonar.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='nam',
    maintainer_email='nam@todo.todo',
    description='Serial bridge between ROS 2 and Arduino motor controller',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'serial_bridge = my_robot_driver.serial_bridge_node:main',
            'scan_filter   = my_robot_driver.scan_filter_node:main',
            'sonar         = my_robot_driver.sonar_node:main',
        ],
    },
)
