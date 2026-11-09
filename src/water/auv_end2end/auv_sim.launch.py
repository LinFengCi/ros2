import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    world_path = os.path.join(
        get_package_share_directory('auv_end2end'),
        'worlds', 'underwater.world')

    # 启动 Gazebo 仿真（世界需包含 gazebo_ros_api_plugin 以提供服务 /gazebo/set_model_state）
    gazebo = ExecuteProcess(
        cmd=['gazebo', '--verbose', world_path],
        output='screen', name='gazebo_sim')

    # 速度桥接：把 /auv/cmd_vel 施加到 Gazebo 中的 'auv' 模型
    vel_ctrl = Node(
        package='auv_end2end', executable='auv_vel_ctrl',
        name='auv_vel_ctrl', output='screen',
        parameters=[{'use_sim_time': True}])

    # 视觉避障控制节点
    avoid = Node(
        package='auv_end2end', executable='auv_obstacle_avoid',
        name='auv_obstacle_avoid', output='screen',
        parameters=[{'use_sim_time': True}])

    return LaunchDescription([gazebo, vel_ctrl, avoid])
