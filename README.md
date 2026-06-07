# jetank_simulation

Gazebo **Fortress** (Ignition, via `ros_gz`) worlds and bring-up for the JeTank
robot.

## Launch files

| File | GUI | Notes |
|---|---|---|
| `gazebo.launch.py` | ✅ | Server **+ GUI**, spawns robot, bridges sensors, spawns controllers |
| `gazebo_headless.launch.py` | ❌ | Server only (`ign gazebo -s`) — for CI / headless hosts |
| `gazebo_remote.launch.py` | ✅ | Laptop-side Gazebo (camera bridge only); pairs with `robot_remote.launch.py` on the Jetson |
| `robot_remote.launch.py` | — | Jetson-side robot spawn + controllers for the split setup |

```bash
# Default world is empty_fortress.sdf; pass a full path to change it.
ros2 launch jetank_simulation gazebo.launch.py
ros2 launch jetank_simulation gazebo.launch.py world:=/path/to/world.sdf use_sim_time:=true
ros2 launch jetank_simulation gazebo.launch.py start_arm_active:=true   # arm_controller active
```

To pick a named world without typing paths, use
`jetank_ros_main/gazebo_sim.launch.py world:=obstacle_course` (or the all-in-one
`jetank_ros_main/sim_demo.launch.py`).

## What `gazebo.launch.py` brings up

- `gz sim` server **and GUI**
- `robot_state_publisher` (URDF with `use_sim:=true`)
- robot spawn (`ros_gz_sim create`)
- `ros_gz_bridge`:
  - `/clock`, `/scan` (LaserScan), `/imu` (IMU)
  - `/stereo_camera/{left,right}/image_raw` + `camera_info`
- controller spawners: `joint_state_broadcaster`, `diff_drive_controller`,
  `gripper_controller`, `arm_controller` (`--inactive` unless `start_arm_active:=true`)

> Drive topic is `/diff_drive_controller/cmd_vel` (**TwistStamped**); odom on
> `/diff_drive_controller/odom`.

## Worlds (`worlds/`)

- `empty_fortress.sdf` — ground + sun, ogre2 / MinimalScene GUI (Fortress).
- `empty.world` — legacy SDF 1.6 empty world.

Obstacle/test worlds (`simple_test`, `obstacle_course`, `sock_arena`) live in
`jetank_ros_main/worlds/` and are selected via `gazebo_sim.launch.py world:=…`.
`obstacle_course` (5×5 m arena, walls + 8 cylinders) is the one to use for
**lidar / SLAM / Nav2** testing — verified `/scan` returns hits at 0.06–3.2 m.

## CMake install

`CMakeLists.txt` guards optional dirs (`worlds launch config models`) with
`if(EXISTS …)` so missing dirs don't hard-fail the build.

## Tests

`test/test_launch_import.py` — loads each of the four launch modules
(`gazebo`, `gazebo_headless`, `gazebo_remote`, `robot_remote`) by path and
calls their `generate_launch_description()` for real (exercising package-share
resolution and xacro processing). It asserts each module exposes a callable
`generate_launch_description`, that it returns a `LaunchDescription` with the
expected top-level action count (16 / 11 / 3 / 6), and that `gazebo.launch.py`
declares the `use_sim_time`, `world`, and `start_arm_active` arguments. Tests
that need installed package shares are skipped (not failed) when run outside
the colcon overlay.

Run via colcon (registered in `CMakeLists.txt` as an `ament_add_pytest_test`):

```bash
colcon test --packages-select jetank_simulation && colcon test-result --verbose
```

Or directly with pytest:

```bash
pixi run -- bash -c 'cd src/jetank_simulation && python -m pytest test/ -q'
```

---

## ROS 2 API

`jetank_simulation` has **no runtime nodes of its own**. It is a Gazebo Fortress (Ignition, via `ros_gz`) bring-up package: it ships **launch files** and **world (SDF) files** only — there is no `src/`, `include/`, `msg/`, `srv/`, or `action/`, and `package.xml` declares no node executables. All ROS interfaces below are produced by *other* packages' executables that these launch files start/configure (the `ros_gz_bridge`, `controller_manager` spawners, etc.). The wire names listed are the ones set in the launch files (the authoritative source for the bridged topics).

### Launch entrypoints

| Launch file | GUI | Brings up |
|---|---|---|
| `gazebo.launch.py` | yes | `gz sim` server + GUI, `robot_state_publisher`, robot spawn, sensor bridges, controller spawners, gripper mimic relay |
| `gazebo_headless.launch.py` | no | `ign gazebo -s` (server only), same nodes as `gazebo.launch.py`, sequenced via `OnProcessExit` event handlers |
| `gazebo_remote.launch.py` | yes | Laptop-side `gz sim` server/GUI + camera/clock bridge only (pairs with `robot_remote.launch.py`) |
| `robot_remote.launch.py` | — | Jetson-side `robot_state_publisher`, robot spawn, and `joint_state_broadcaster`/`diff_drive_controller`/`arm_controller` spawners (no Gazebo) |

```bash
ros2 launch jetank_simulation gazebo.launch.py
ros2 launch jetank_simulation gazebo.launch.py world:=/path/to/world.sdf use_sim_time:=true
ros2 launch jetank_simulation gazebo.launch.py start_arm_active:=true
```

### Worlds (`worlds/`)

| World file | Notes |
|---|---|
| `empty_fortress.sdf` | Ground + sun; loads Physics, UserCommands, SceneBroadcaster, Sensors, and IMU system plugins; ogre2 / MinimalScene GUI (Fortress) |
| `empty.world` | Legacy SDF empty world |

### Bridged topics (`ros_gz_bridge parameter_bridge`)

These ROS topics are bridged from Ignition by the launch files. Direction is Ignition→ROS (the `[` bridge operator in every entry), i.e. they are **published** on the ROS side. The underlying sensors are defined in the robot URDF (`jetank_description`), not in this package.

| Topic | Type | Launch files |
|---|---|---|
| `/clock` | `rosgraph_msgs/msg/Clock` | gazebo, gazebo_headless, gazebo_remote |
| `/stereo_camera/left/image_raw` | `sensor_msgs/msg/Image` | gazebo, gazebo_headless, gazebo_remote |
| `/stereo_camera/left/camera_info` | `sensor_msgs/msg/CameraInfo` | gazebo, gazebo_headless, gazebo_remote |
| `/stereo_camera/right/image_raw` | `sensor_msgs/msg/Image` | gazebo, gazebo_headless, gazebo_remote |
| `/stereo_camera/right/camera_info` | `sensor_msgs/msg/CameraInfo` | gazebo, gazebo_headless, gazebo_remote |
| `/scan` | `sensor_msgs/msg/LaserScan` | gazebo, gazebo_headless |
| `/imu` | `sensor_msgs/msg/Imu` | gazebo, gazebo_headless |

Note: `gazebo_remote.launch.py` bridges only the 4 camera topics + `/clock` (no `/scan` or `/imu`).

### Controllers spawned (via `controller_manager` `spawner`)

These are loaded against `/controller_manager` (provided by the `ign_ros2_control`/`gz_ros2_control` system plugin in the URDF). They expose the usual `ros2_control` controller interfaces:

| Controller | Started in | State |
|---|---|---|
| `joint_state_broadcaster` | gazebo, gazebo_headless, robot_remote | active |
| `diff_drive_controller` | gazebo, gazebo_headless, robot_remote | active |
| `arm_controller` | gazebo, gazebo_headless, robot_remote | inactive by default; active if `start_arm_active:=true` (robot_remote always `--inactive`) |
| `gripper_controller` | gazebo, gazebo_headless | active |
| `gripper_right_mimic_controller` | gazebo, gazebo_headless | active (ForwardCommandController for the right finger) |

Robot base drive topic (from `diff_drive_controller`): `/diff_drive_controller/cmd_vel` (**TwistStamped**); odometry on `/diff_drive_controller/odom`. These are emitted by `ros2_controllers`' `diff_drive_controller`, not by this package.

### Helper node started (owned by another package)

`gazebo.launch.py` and `gazebo_headless.launch.py` also start the `gripper_mimic_relay` executable from **`jetank_ros_main`** (node name `gripper_mimic_relay`) — it subscribes to `/joint_states` and forwards the `gripper_left_joint` position to `/gripper_right_mimic_controller/commands` so both fingers actuate together (Gazebo Fortress does not enforce URDF `<mimic>`). This node belongs to `jetank_ros_main`, not `jetank_simulation`.

### Parameters (launch arguments)

| Argument | Default | Meaning |
|---|---|---|
| `use_sim_time` | `true` | Use Gazebo clock |
| `world` | `<share>/jetank_simulation/worlds/empty_fortress.sdf` | Full path to SDF world to load |
| `start_arm_active` | `false` | Start `arm_controller` active instead of inactive (`gazebo.launch.py` / `gazebo_headless.launch.py` only) |
