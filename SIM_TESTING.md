# Testing the JeTank in Gazebo (Fortress / Ignition)

How to bring up the full robot in simulation and exercise every component:
mobile base, 2D lidar, IMU, and stereo camera. Arm/MoveIt is covered separately.

The whole stack runs inside the pixi env — prefix everything with `pixi run`
(or enter `pixi shell` once). Gazebo target is **Fortress** (`ign gazebo`,
Gazebo Sim 6.16) via `ros_gz` + `ign_ros2_control`.

## 1. Launch the simulation

```bash
# GUI
pixi run bash -c "ros2 launch jetank_simulation gazebo.launch.py"

# Headless (CI / no display)
pixi run bash -c "ros2 launch jetank_simulation gazebo_headless.launch.py"

# Walled world for mapping (full path to any world)
WORLD=$(ros2 pkg prefix jetank_ros_main)/share/jetank_ros_main/worlds/obstacle_course.sdf
pixi run bash -c "ros2 launch jetank_simulation gazebo_headless.launch.py world:=$WORLD"
```

What comes up: `ign gazebo` server, `robot_state_publisher`, robot spawn,
`ros_gz_bridge` (camera + lidar + imu + clock), and `controller_manager` with
`joint_state_broadcaster` + `diff_drive_controller` active (`arm_controller`
loaded inactive).

> The world **must** load the Ignition `Sensors` (ogre2) and `Imu` systems or
> the camera/lidar/IMU produce nothing. All shipped worlds now include them.

## 2. Per-component smoke test

| Component | Topic | Quick check |
|---|---|---|
| Base odometry | `/diff_drive_controller/odom` | `ros2 topic echo … --once` → frame `odom`, child `base_footprint` |
| Lidar | `/scan` | `ros2 topic hz /scan`; `--field header` → `frame_id: laser` |
| IMU | `/imu` | `ros2 topic hz /imu` → ~100 Hz, frame `imu_link` |
| Camera (L/R) | `/stereo_camera/{left,right}/image_raw` | `ros2 topic hz …` → ~30 Hz |
| Camera info | `/stereo_camera/{left,right}/camera_info` | `ros2 topic echo … --once` → non-zero `k` |
| Joint states | `/joint_states` | published by `joint_state_broadcaster` |
| TF | `/tf`,`/tf_static` | `ros2 run tf2_ros tf2_echo odom laser` resolves |

### Drive the base
The diff-drive controller has `use_stamped_vel=true`, so it listens on
**`/diff_drive_controller/cmd_vel`** as **`geometry_msgs/msg/TwistStamped`**
(a plain `Twist` is silently ignored):
```bash
ros2 topic pub -r 10 /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_link}, twist: {linear: {x: 0.3}, angular: {z: 0.5}}}"
```
Verified: 5 s of this command moves the robot ~1.5 m (checked via
`/diff_drive_controller/odom`).

### Move the arm + gripper
The sim launch loads `arm_controller` **inactive** and does **not** spawn the
gripper controller. Bring them up, then command them:
```bash
# activate arm, spawn gripper
ros2 control set_controller_state arm_controller active
ros2 run controller_manager spawner gripper_controller --controller-manager /controller_manager

# arm trajectory (4-DOF: S1,S2,S3,S5)
ros2 topic pub --once /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
  "{joint_names: [S1_joint,S2_joint,S3_joint,S5_joint], points: [{positions: [0.6,0.4,-0.4,0.5], time_from_start: {sec: 2}}]}"

# gripper (parallel: left,right) — position controller
ros2 topic pub --once /gripper_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.015, 0.015]}"
```
Verified: arm and gripper joints track the commanded positions in `/joint_states`
while the base drives simultaneously.

## 3. SLAM demo (acceptance test)

In three shells (all under `pixi run`/`pixi shell`):
```bash
# 1) sim with a walled world
WORLD=$(ros2 pkg prefix jetank_ros_main)/share/jetank_ros_main/worlds/obstacle_course.sdf
ros2 launch jetank_simulation gazebo_headless.launch.py world:=$WORLD

# 2) slam_toolbox on simulated /scan, sim clock
ros2 launch jetank_navigation slam.launch.py use_sim_time:=true

# 3) drive around (TwistStamped!), then save the map
ros2 topic pub -r 10 /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_link}, twist: {linear: {x: 0.3}, angular: {z: 0.3}}}"
ros2 run nav2_map_server map_saver_cli -f ~/maps/jetank_map --ros-args -p use_sim_time:=true
```
A populated `~/maps/jetank_map.pgm` (black walls, white free space) confirms the
lidar → SLAM → map pipeline works end-to-end in sim.

Nav2 (after a map exists): `ros2 launch jetank_navigation nav2_bringup.launch.py use_sim_time:=true`.
Nav2's controller publishes `/cmd_vel` — remap it to `/diff_drive_controller/cmd_vel`
(or add a relay) so velocity commands reach the diff-drive controller.

## Troubleshooting

- **No `/scan`, `/imu`, or images** — the world is missing the `Sensors`/`Imu`
  systems, or the render engine failed. Check the `ign` log; headless rendering
  needs a GPU/EGL or an X display.
- **`Failed to load system plugin libign_ros2_control-system.so`** — the
  Ignition system-plugin search path doesn't include the conda env lib. The
  launch files set `IGN_GAZEBO_SYSTEM_PLUGIN_PATH=$CONDA_PREFIX/lib`; make sure
  you launched from inside the pixi env.
- **Controllers never activate** (`Could not contact /controller_manager`) — the
  ros2_control system plugin failed to load (see above); nothing spawns without
  the controller manager.
