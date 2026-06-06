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
