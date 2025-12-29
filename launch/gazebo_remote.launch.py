"""
Laptop-side Gazebo Launch File for Remote Simulation

This launch file runs Gazebo Fortress on your laptop while robot nodes run on Jetson.

Usage on LAPTOP:
    export ROS_DOMAIN_ID=42  # Match with Jetson
    ros2 launch jetank_simulation gazebo_remote.launch.py

Then on JETSON:
    export ROS_DOMAIN_ID=42  # Match with laptop
    ros2 launch jetank_simulation robot_remote.launch.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
import xacro


def generate_launch_description():
    # Get package directories
    pkg_jetank_simulation = get_package_share_directory('jetank_simulation')
    pkg_jetank_description = get_package_share_directory('jetank_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Paths
    world_file = os.path.join(pkg_jetank_simulation, 'worlds', 'empty_fortress.sdf')
    xacro_file = os.path.join(pkg_jetank_description, 'urdf', 'jetank_ros2_control.urdf.xacro')

    # Process xacro to URDF with simulation flag
    robot_description_config = xacro.process_file(
        xacro_file,
        mappings={'use_sim': 'true', 'use_ros2_control': 'true'}
    )
    robot_description_xml = robot_description_config.toxml()

    # Launch configuration variables
    world = LaunchConfiguration('world')

    # Declare launch arguments
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Full path to world file to load'
    )

    # Gazebo Fortress server (gz sim)
    # Note: This runs the physics simulation and GUI
    gz_sim_server = IncludeLaunchDescription(
        PathJoinSubstitution([pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py']),
        launch_arguments={
            'gz_args': [world, ' -r -v 4'],  # -r: run, -v: verbose level 4
            'on_exit_shutdown': 'true'
        }.items()
    )

    # ros_gz bridge for camera topics
    # This bridges Gazebo topics to ROS2 topics over the network
    from launch_ros.actions import Node
    bridge_camera = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/stereo_camera/left/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/stereo_camera/left/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            '/stereo_camera/right/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/stereo_camera/right/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'
        ],
        output='screen'
    )

    # Create launch description
    ld = LaunchDescription()

    # Declare arguments
    ld.add_action(declare_world_cmd)

    # Add nodes
    ld.add_action(gz_sim_server)
    ld.add_action(bridge_camera)

    return ld
