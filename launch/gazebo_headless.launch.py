import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, EnvironmentVariable
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    # Get package directories
    pkg_jetank_simulation = get_package_share_directory('jetank_simulation')
    pkg_jetank_description = get_package_share_directory('jetank_description')

    # Paths
    world_file = os.path.join(pkg_jetank_simulation, 'worlds', 'empty_fortress.sdf')
    xacro_file = os.path.join(pkg_jetank_description, 'urdf', 'jetank_ros2_control.urdf.xacro')

    # Process xacro to URDF with simulation flag
    robot_description_config = xacro.process_file(
        xacro_file,
        mappings={'use_sim': 'true', 'use_ros2_control': 'true'}
    )
    robot_description = {'robot_description': robot_description_config.toxml()}

    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')
    world = LaunchConfiguration('world')

    # Declare launch arguments
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Full path to world file to load'
    )

    # Set Gazebo plugin path to include ROS2 libraries
    set_gazebo_plugin_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_SYSTEM_PLUGIN_PATH',
        value='/opt/ros/humble/lib'
    )

    # Gazebo Fortress server (HEADLESS - no GUI)
    gz_sim_server = ExecuteProcess(
        cmd=['ign', 'gazebo', '-r', '-v', '4', '-s', world_file],
        output='screen'
    )

    # Robot state publisher
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

    # Spawn robot in Gazebo (using ros_gz spawn)
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

    # ros_gz bridge for camera topics
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

    # Joint state broadcaster
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen'
    )

    # Diff drive controller
    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )

    # Arm controller (optional - starts inactive, can be activated later)
    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager', '--inactive'],
        output='screen'
    )

    # Create launch description
    ld = LaunchDescription()

    # Declare arguments
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_world_cmd)

    # Set environment
    ld.add_action(set_gazebo_plugin_path)

    # Add nodes
    ld.add_action(gz_sim_server)
    ld.add_action(robot_state_publisher)
    ld.add_action(spawn_robot)
    ld.add_action(bridge_camera)
    ld.add_action(joint_state_broadcaster_spawner)
    ld.add_action(diff_drive_controller_spawner)
    ld.add_action(arm_controller_spawner)

    return ld
