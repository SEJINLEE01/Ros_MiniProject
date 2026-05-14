#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
# from turtlesim.msg import Pose
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from geometry_msgs.msg import TwistStamped
import math
from chase_object.control_apps import PID
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import Float64
from std_msgs.msg import Float64MultiArray

class TurtlePIDController(Node):
    def __init__(self):
        super().__init__('turtle_pid_controller')
        
        # Declare ROS2 parameters (PID parameters and tolerance)
        self.declare_parameter('P', 0.002)
        self.declare_parameter('I', 0.0)
        self.declare_parameter('D', 0.0)
        self.declare_parameter('max_state', 5.0)
        self.declare_parameter('min_state', -5.0)
        self.declare_parameter('tolerance', 20)
        
        # Get initial parameter values for PID and tolerance
        P = self.get_parameter('P').value
        I = self.get_parameter('I').value
        D = self.get_parameter('D').value
        max_state = self.get_parameter('max_state').value
        min_state = self.get_parameter('min_state').value
        self.tolerance = self.get_parameter('tolerance').value

        # Create PID instance and assign parameters
        self.pid = PID()
        self.pid.P = P
        self.pid.I = I
        self.pid.D = D
        self.pid.max_state = max_state
        self.pid.min_state = min_state

        # Target angle is received from the goal_theta topic (initially 0.0)
        self.target_theta = 0.0

        self.TARGET_PERCENT = 6.0 # 목표 점유율 20%
        self.THRESHOLD = 1.0 # 오차 범위 (18%~22% 사이면 정지)

        # PC(YOLOTracker)에서 보낸 화면 픽셀 오차값 구독
        self.error_subscriber = self.create_subscription(
            Float64MultiArray,
            'yolo_error', # PC 파이썬 코드에서 퍼블리시하는 토픽 이름
            self.yolo_error_callback,
            10)
        
        self.publisher = self.create_publisher(TwistStamped, 'cmd_vel', 10)
        
        self.error_publisher = self.create_publisher(Float64, 'error', 10)
        
        # Register parameter callback for dynamic reconfiguration (PID parameters and tolerance)
        self.add_on_set_parameters_callback(self.parameter_callback)

        # 🎯 추가됨: 가장 마지막으로 메시지를 받은 시간을 저장
        self.last_msg_time = self.get_clock().now()
        
        # 🎯 추가됨: 워치독 타이머 (0.1초마다 검사해서, 0.5초 이상 지났으면 정지)
        self.watchdog_timer = self.create_timer(0.1, self.watchdog_callback)
        self.timeout_sec = 0.5

    def parameter_callback(self, params):
        for param in params:
            if param.name == 'P':
                self.pid.P = param.value
                self.get_logger().info(f"Updated PID P: {param.value}")
            elif param.name == 'I':
                self.pid.I = param.value
                self.get_logger().info(f"Updated PID I: {param.value}")
            elif param.name == 'D':
                self.pid.D = param.value
                self.get_logger().info(f"Updated PID D: {param.value}")
            elif param.name == 'max_state':
                self.pid.max_state = param.value
                self.get_logger().info(f"Updated PID max_state: {param.value}")
            elif param.name == 'min_state':
                self.pid.min_state = param.value
                self.get_logger().info(f"Updated PID min_state: {param.value}")
            elif param.name == 'tolerance':
                self.tolerance = param.value
                self.get_logger().info(f"Updated tolerance: {param.value}")
        return SetParametersResult(successful=True)


    def yolo_error_callback(self, msg):
        # 메시지가 들어올 때마다 마지막 수신 시간을 현재 시간으로 갱신 (워치독 초기화)
        self.last_msg_time = self.get_clock().now()

        # 1. PC(YOLO)에서 계산되어 넘어온 픽셀 오차값(error_x)을 그대로 사용합니다.
        pixel_error = msg.data[0]
        target_percent = msg.data[1]
        
        # 모니터링을 위해 error 토픽 발행 (rqt_plot 등에서 그래프로 보기 위함)
        error_msg = Float64()
        error_msg.data = pixel_error
        self.error_publisher.publish(error_msg)
        
        twist_msg = TwistStamped()

        twist_msg.header.stamp = self.get_clock().now().to_msg() # 현재 시간
        twist_msg.header.frame_id = 'base_link' # 터틀봇3의 기본 프레임 이름
        
        # 2. 오차가 허용 범위(tolerance) 이내면 로봇 정지 (목표가 중앙에 있음)
        if abs(pixel_error) < self.tolerance:
            twist_msg.twist.angular.z = 0.0
            self.get_logger().info(f"Target is in the center! (Error: {pixel_error:.1f}px)")
        else:
            # 3. PID 제어기를 통해 회전 속도(Control Output) 계산
            angular_correction = self.pid.update(pixel_error)
            
            # 4. [매우 중요] 제어 방향 맞추기
            # 물체가 화면 우측에 있으면 error_x는 양수(+)입니다.
            # ROS에서 로봇이 우회전하려면 angular.z에 음수(-) 값을 주어야 합니다.
            # 따라서 계산된 PID 결과값의 부호를 반대로 뒤집어 줍니다.
            twist_msg.twist.angular.z = -angular_correction
            
        # 직진 속도는 0으로 고정 (물체를 향해 제자리 회전만 수행)
        # twist_msg.twist.linear.x = 0.0

        if target_percent < (self.TARGET_PERCENT - self.THRESHOLD):
            twist_msg.twist.linear.x = 0.05
        elif target_percent > (self.TARGET_PERCENT + self.THRESHOLD):
            twist_msg.twist.linear.x = -0.05  # 뒤로 이동
        else:
            twist_msg.twist.linear.x = 0.0
                
        # 모터 제어 명령(cmd_vel) 발행
        self.publisher.publish(twist_msg)
        
        # 터미널 창에 현재 상태 출력
        self.get_logger().info(
            f"YOLO Error: {pixel_error:.1f}px, "
            f"Control Output (angular.z): {twist_msg.twist.angular.z:.3f}"
        )
    
    def watchdog_callback(self):
        now = self.get_clock().now()
        
        # 마지막 메시지 수신 후 흐른 시간(초) 계산
        elapsed_time = (now - self.last_msg_time).nanoseconds / 1e9
        
        # 지정된 시간(0.5초) 이상 오차값이 들어오지 않으면 타겟을 놓친 것으로 간주
        if elapsed_time > self.timeout_sec:
            twist_msg = TwistStamped()
            twist_msg.header.stamp = now.to_msg()
            twist_msg.header.frame_id = 'base_link'
            
            # 속도를 0으로 만들어 정지 명령 발행
            twist_msg.twist.linear.x = 0.0
            twist_msg.twist.angular.z = 0.0
            self.publisher.publish(twist_msg)
            
            # 로그창이 도배되지 않게 1초에 한 번만 경고 출력
            self.get_logger().warning("Target lost! Stopping the robot.", throttle_duration_sec=1.0)

def main(args=None):
    rclpy.init(args=args)
    node = TurtlePIDController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Node interrupted")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()