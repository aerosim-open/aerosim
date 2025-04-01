import rclpy
from rclpy.node import Node
from aerosim_data import Actor
from aerosim_data import types
print(types.VehicleType)

class VehicleSubscriber(Node):
    def __init__(self):
        super().__init__('vehicle_subscriber')
        self.subscription = self.create_subscription(
            Actor,
            'vehicle_topic',
            self.listener_callback,
            10)

    def listener_callback(self, msg):
        self.get_logger().info(f'Received vehicle update: {msg.id}, {msg.vehicle_type}')
        self.get_logger().info(f'Position: {msg.pose.position}')
        self.get_logger().info(f'Orientation: {msg.pose.orientation}')
        self.get_logger().info(f'Velocity: {msg.velocity}')
        self.get_logger().info(f'Acceleration: {msg.acceleration}')

def main(args=None):
    rclpy.init(args=args)
    vehicle_subscriber = VehicleSubscriber()
    rclpy.spin(vehicle_subscriber)
    vehicle_subscriber.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()