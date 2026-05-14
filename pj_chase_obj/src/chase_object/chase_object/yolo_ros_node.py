import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from std_msgs.msg import Float64MultiArray
import cv2
import threading

# 직접 만드신 YOLO 모듈을 불러옵니다.
from chase_object.yolo_apps import YOLOTracker 


# ==========================================
# 🎯 핵심 해결책: 버퍼를 비우는 최신 프레임 스트리머
# ==========================================
class LatestFrameStream:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        self.ret = False
        self.frame = None
        self.running = True

        self.lock = threading.Lock()
        
        # 카메라가 열렸는지 확인
        if self.cap.isOpened():
            self.ret, self.frame = self.cap.read()
        
        # 메인 프로그램과 별개로 계속 돌아가는 백그라운드 스레드 시작
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        # 쉴 새 없이 cap.read()를 호출하여 버퍼가 쌓일 틈을 주지 않습니다.
        while self.running:
            if self.cap.isOpened():
                ret, frame = self.cap.read()

                with self.lock: 
                    self.ret = ret
                    if ret and frame is not None:
                        self.frame = frame.copy()

    def read(self):
        # 메인 코드에서 요청할 때는 묻지도 따지지도 않고 가장 '최신' 프레임만 줍니다.
        with self.lock: 
            if self.frame is not None:
                return self.ret, self.frame.copy()
            return self.ret, None

    def release(self):
        self.running = False
        self.thread.join() # 스레드가 안전하게 종료될 때까지 대기
        self.cap.release()
# ==========================================


class YoloVisionNode(Node):
    def __init__(self):
        super().__init__('yolo_vision_node')
        
        # 1. 오차를 발행할 Publisher 생성
        self.error_publisher = self.create_publisher(Float64MultiArray, 'yolo_error', 10)

        # 2. YOLO 추적기 인스턴스 생성 (초기 타겟 없음 = 자동 락온)
        self.tracker = YOLOTracker(target_name='mouse')
        
        # 3. 비디오 스트림 URL 연결
        url = "http://10.10.14.18:5000/video_feed"
        self.stream = LatestFrameStream(url)
        
        if not self.stream.cap.isOpened():
            self.get_logger().error(f"비디오 스트림을 열 수 없습니다: {url}")
            return
            
        self.get_logger().info("카메라 스트림 연결 완료! 타겟 탐지를 시작합니다.")
        
        # 4. ROS2 타이머 설정 (run 함수의 무한 루프를 대체합니다)
        # 0.05초(20Hz)마다 timer_callback 함수를 실행합니다.
        self.timer = self.create_timer(0.05, self.timer_callback)

    def timer_callback(self):
        # 1. 프레임 읽기
        ret, frame = self.stream.read()
        if not ret:
            self.get_logger().warning("프레임을 수신할 수 없습니다.")
            return

        # 2. yolo_apps.py의 핵심 로직 실행
        annotated_frame, error_x, target_percent = self.tracker.process_frame(frame)

        # 3. 오차값이 있으면(물체를 찾았으면) ROS2 Topic으로 발행
        if error_x is not None:
            msg = Float64MultiArray()
            msg.data = [float(error_x), float(target_percent)]
            self.error_publisher.publish(msg)

        # 4. 화면 출력
        cv2.imshow('YOLO Stream Tracker', annotated_frame)
        
        # OpenCV 창 업데이트를 위해 필수적인 waitKey (1ms)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.get_logger().info("'q' 입력됨. 프로그램 종료 대기...")
            rclpy.shutdown()

    def destroy_node(self):
        # 노드가 종료될 때 자원 깔끔하게 해제
        super().destroy_node()
        self.stream.release()
        cv2.destroyAllWindows()

def main(args=None):
    rclpy.init(args=args)
    node = YoloVisionNode()
    
    try:
        # rclpy.spin이 노드를 계속 살려두며 타이머를 작동시킵니다.
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("사용자에 의해 종료되었습니다.")
    finally:
        node.destroy_node()
        # 이미 rclpy.shutdown()이 호출되지 않았다면 호출
        if rclpy.ok(): 
            rclpy.shutdown()

if __name__ == '__main__':
    main()