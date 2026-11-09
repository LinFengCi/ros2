# AUV 水下机器人仿真功能包（auv_end2end）

基于 **ROS2 (Humble) + Gazebo 11** 的水下机器人端到端仿真功能包，包含：

- **视觉避障**（`auv_obstacle_avoid`）：单目相机检测前方暗色障碍墙体，触发减速+侧向避让，带滞环与超时恢复。
- **矩形巡航**（`auv_rect_cruise`）：基于时间状态机的四段闭合矩形航迹（前进→右移→后退→左移）。
- **速度桥接**（`auv_vel_ctrl`）：把 `/auv/cmd_vel` 通过 Gazebo `set_model_state` 施加到仿真模型，是控制指令通向仿真的关键一环。
- **简易视觉控制**（`auv_vision_control`）：亮/暗区域巡游示例。
- **差速逆解**（`diff_drive`）：轮式底盘对照节点（非 AUV 主链路）。

## 环境依赖

- ROS2 Humble
- Gazebo 11.10
- Python 3.10+
- OpenCV + cv_bridge
- gazebo_ros（提供 `libgazebo_ros_api_plugin.so` / `libgazebo_ros_camera.so`）

## 坐标系说明

采用 **ENU 世界坐标系**：x 轴向前、y 轴向右、z 轴向上。控制指令在世界系下解释
（`auv_vel_ctrl` 以 `reference_frame='world'` 调用 `set_model_state`），
故 `linear.x`=前进、`linear.y`=右移（负 y）、`angular.z`=偏航。

## 目录结构

```
auv_end2end/
├── auv_end2end/            # Python 节点源码
│   ├── auv_obstacle_avoid.py
│   ├── auv_rect_cruise.py
│   ├── auv_vel_ctrl.py
│   ├── auv_vision_control.py
│   └── diff_drive.py
├── launch/                 # 启动文件
│   ├── auv_sim.launch.py          # Gazebo + vel_ctrl + 视觉避障
│   └── auv_rect_cruise.launch.py  # Gazebo + vel_ctrl + 矩形巡航
├── resource/auv_end2end    # ament 资源索引标记
├── worlds/underwater.world # 自包含仿真世界（含模型 auv、相机、障碍墙、雾效）
├── package.xml
├── setup.py
└── README.md
```

## 编译与运行

```bash
# 在 ROS2 工作区中（本包放到 src/water/auv_end2end）
colcon build --packages-select auv_end2end
source install/setup.bash

# 1) 视觉避障端到端仿真
ros2 launch auv_end2end auv_sim.launch.py

# 2) 矩形巡航端到端仿真
ros2 launch auv_end2end auv_rect_cruise.launch.py
```

> 启动文件已包含 Gazebo + `auv_vel_ctrl` 桥接，无需单独启动仿真或桥接节点。

## 可调参数（ROS 参数，无需改代码）

- `auv_obstacle_avoid`：`camera_topic`、`cmd_topic`、`obstacle_thresh`、`trigger_ratio`、
  `recover_ratio`、`forward_speed`、`side_speed`、`max_avoid_duration`、`roi_top`、`roi_bottom`
- `auv_rect_cruise`：`forward_speed`、`side_speed`、`forward_time`、`side_time`、`cmd_topic`
- `auv_vel_ctrl`：`model_name`、`cmd_topic`
- `auv_vision_control`：`camera_topic`、`cmd_topic`、`bright_thresh`

示例：把巡航前进时间改为 15s

```bash
ros2 param set /auv_rect_cruise_node forward_time 15.0
```

## 本次重点修复（可靠性）

| 模块 | 问题 | 修复 |
| --- | --- | --- |
| `auv_vel_ctrl` | 只拷贝 `linear.x`/`angular.z`，**丢失横向 `linear.y`**，AUV 无法侧移 | 补全 `linear.y/z` 映射；同步 `call` + 成功检查 + 异常保护；服务等待加超时上限 |
| `auv_obstacle_avoid` | 计时用整数秒，2s 超时窗口被压缩 | 改用 `nanoseconds()/1e9` 浮点秒；每帧 INFO 降为 DEBUG 防刷屏；参数化话题与阈值 |
| `auv_vision_control` | `cv2.imshow` 在无显示环境崩溃 | 检测显示能力 + 异常保护，headless 下自动关闭窗口 |
| `launch` | `auv_sim` 缺 `auv_vel_ctrl`，AUV 收到指令却不动；`auv_rect_cruise` 的 `executable` 误带 `.py` 后缀 | 两个 launch 均补齐 `auv_vel_ctrl` 与 `use_sim_time`，修正 executable 名称 |
| `package.xml` | 仍是 `TODO` 占位、缺 `std_msgs`/`gazebo_msgs` 依赖 | 补全依赖与元数据 |
| `setup.py` | 缺 `auv_vel_ctrl`/`auv_vision_control`/`diff_drive` 入口；误装 `.py` 到 `lib` | 补全 5 个入口脚本，移除错误 data_file |
| `underwater.world` | 原仓库世界文件缺失/重复 | 提供自包含世界：模型 `auv` + 前向相机(`/auv/camera/image_raw`) + 暗色障碍墙 + 雾效 |

## 已知注意点

- `underwater.world` 中相机朝向为 `pitch=90°`（镜头沿世界 +X 看向前方障碍墙）。
  若你的相机插件约定不同视轴，请微调 `<sensor><pose>` 的 `0 1.5708 0` 旋转。
- `set_model_state` 属于“速度注入”式控制，适用于作业演示；若需真实水动力，
  建议后续接入 `libgazebo_ros_planar_move` / 力-力矩插件。
