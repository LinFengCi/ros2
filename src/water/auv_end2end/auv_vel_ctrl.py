#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUV 速度控制桥接节点。

订阅 /auv/cmd_vel（geometry_msgs/Twist），通过 Gazebo 的
/gazebo/set_model_state 服务把速度施加到名为 'auv' 的模型上。

说明（可靠性要点）：
- 之前版本只拷贝了 linear.x 与 angular.z，导致 control 节点发布的
  linear.y（横向平移）被丢弃，AUV 永远无法侧移。这里补全了 y/z 分量。
- 之前用 call_async 但未跟踪 future，请求会在高频下堆积/丢失；
  改为同步 call 并对返回值做 success 检查与异常保护。
- 等待 Gazebo 服务增加了重试上限，避免在没有仿真时永久阻塞。
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gazebo_msgs.srv import SetModelState
from gazebo_msgs.msg import ModelState


class AuvVelController(Node):
    def __init__(self):
        super().__init__('auv_vel_ctrl')

        # 允许通过参数指定被控模型名与话题，避免硬编码
        self.declare_parameter('model_name', 'auv')
        self.declare_parameter('cmd_topic', '/auv/cmd_vel')
        self.model_name = self.get_parameter('model_name').value
        cmd_topic = self.get_parameter('cmd_topic').value

        # 等待 Gazebo 的 set_model_state 服务，带重试上限，避免永久阻塞
        self.cli = self.create_client(SetModelState, '/gazebo/set_model_state')
        retries = 0
        while not self.cli.wait_for_service(timeout_sec=2.0):
            retries += 1
            if retries > 30:
                self.get_logger().error(
                    '等待 /gazebo/set_model_state 超时（>60s），请确认 Gazebo 已启动且世界含 gazebo_ros_api_plugin。')
                raise RuntimeError('Gazebo set_model_state 服务不可用')
            self.get_logger().info('等待 Gazebo /gazebo/set_model_state 服务...')

        self.sub = self.create_subscription(Twist, cmd_topic, self.cmd_cb, 10)
        self.get_logger().info(f'AUV 速度控制节点已启动，订阅 {cmd_topic}，控制模型 "{self.model_name}"')

    def cmd_cb(self, msg: Twist):
        req = SetModelState.Request()
        state = ModelState()
        state.model_name = self.model_name
        # world 参考系：linear.x/y/z 与 angular.z 均在世界坐标系下解释
        state.reference_frame = 'world'
        state.twist.linear.x = float(msg.linear.x)
        state.twist.linear.y = float(msg.linear.y)
        state.twist.linear.z = float(msg.linear.z)
        state.twist.angular.z = float(msg.angular.z)
        req.model_state = state

        try:
            resp = self.cli.call(req)
            if not resp.success:
                self.get_logger().warn(f'set_model_state 失败: {resp.status_message}')
        except Exception as e:
            self.get_logger().error(f'调用 set_model_state 异常: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = AuvVelController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
