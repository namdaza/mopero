#!/usr/bin/env python3
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose, FollowPath


class UiGoalBridge(Node):
    def __init__(self):
        super().__init__('ui_goal_bridge')
        self._planner_client = ActionClient(
            self, ComputePathToPose, 'compute_path_to_pose')
        self._controller_client = ActionClient(
            self, FollowPath, 'follow_path')
        self.create_subscription(PoseStamped, 'goal_pose', self._on_goal_pose, 10)
        self.get_logger().info(
            'Waiting for UI goals on /goal_pose; using compute_path_to_pose -> follow_path')

    def _on_goal_pose(self, pose_msg):
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = pose_msg.header.frame_id or 'map'
        goal_pose.header.stamp = self.get_clock().now().to_msg()
        goal_pose.pose = pose_msg.pose

        self.get_logger().info(
            'UI goal received: x=%.3f y=%.3f frame=%s'
            % (
                goal_pose.pose.position.x,
                goal_pose.pose.position.y,
                goal_pose.header.frame_id,
            )
        )

        if not self._planner_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().error('Planner action server /compute_path_to_pose is not available')
            return

        goal_msg = ComputePathToPose.Goal()
        goal_msg.pose = goal_pose
        goal_msg.planner_id = 'GridBased'
        future = self._planner_client.send_goal_async(goal_msg)
        future.add_done_callback(self._on_planner_goal_response)

    def _on_planner_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Planner rejected the UI goal')
            return

        self.get_logger().info('Planner accepted the UI goal')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_planner_result)

    def _on_planner_result(self, future):
        result = future.result()
        if result.status != 4:
            self.get_logger().warn(
                'Planner failed with status %s' % result.status)
            return

        path = result.result.path
        if not path.poses:
            self.get_logger().warn('Planner returned an empty path')
            return

        self.get_logger().info('Planner returned path with %d poses' % len(path.poses))
        if not self._controller_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().error('Controller action server /follow_path is not available')
            return

        follow_goal = FollowPath.Goal()
        follow_goal.path = path
        follow_goal.controller_id = 'FollowPath'
        future = self._controller_client.send_goal_async(
            follow_goal,
            feedback_callback=self._on_controller_feedback,
        )
        future.add_done_callback(self._on_controller_goal_response)

    def _on_controller_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Controller rejected the path')
            return

        self.get_logger().info('Controller accepted the path')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_controller_result)

    def _on_controller_feedback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(
            'Distance remaining: %.2f m, speed: %.2f m/s'
            % (feedback.distance_to_goal, feedback.speed)
        )

    def _on_controller_result(self, future):
        result = future.result()
        self.get_logger().info('Controller finished with status %s' % result.status)


def main(args=None):
    rclpy.init(args=args)
    node = UiGoalBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
