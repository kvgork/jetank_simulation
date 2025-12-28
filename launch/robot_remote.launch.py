"""
Jetson-side Robot Nodes Launch File for Remote Simulation

This launch file runs robot nodes on Jetson while Gazebo runs on laptop.

Usage on JETSON:
    export ROS_DOMAIN_ID=42  # Match with laptop
    export RMW_IMPLEMENTATION=rmw_fastrtps_cpp  # Recommended for network
    ros2 launch jetank_simulation robot_remote.launch.py

On LAPTOP (run first):
    export ROS_DOMAIN_ID=42  # Match with Jetson
    ros2 launch jetank_simulation gazebo_remote.launch.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    # Get package directories
    pkg_jetank_description = get_package_share_directory('jetank_description')

    # Paths
    xacro_file = os.path.join(pkg_jetank_description, 'urdf', 'jetank_ros2_control.urdf.xacro')

    # Process xacro to URDF with simulation flag
    robot_description_config = xacro.process_file(
        xacro_file,
        mappings={'use_sim': 'true', 'use_ros2_control': 'true'}
    )
    robot_description = {'robot_description': robot_description_config.toxml()}

    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')

    # Declare launch arguments
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation clock from Gazebo (on laptop)'
    )

    # Robot state publisher
    # Publishes robot's TF tree based on joint states
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            robot_description,
            {'use_sim_time': use_sim_time}
        ]
    )

    # Spawn robot in Gazebo (remote)
    # This sends the robot description to Gazebo running on laptop
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'jetank',
            '-topic', 'robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1'
        ],
        output='screen'
    )

    # Joint state broadcaster
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # Diff drive controller
    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # Arm controller (optional - starts inactive)
    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager', '--inactive'],
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # Create launch description
    ld = LaunchDescription()

    # Declare arguments
    ld.add_action(declare_use_sim_time_cmd)

    # Add nodes (NO Gazebo - it runs on laptop!)
    ld.add_action(robot_state_publisher)
    ld.add_action(spawn_robot)
    ld.add_action(joint_state_broadcaster_spawner)
    ld.add_action(diff_drive_controller_spawner)
    ld.add_action(arm_controller_spawner)

    return ld
