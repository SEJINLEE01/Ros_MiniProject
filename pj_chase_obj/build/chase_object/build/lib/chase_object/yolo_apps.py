from ultralytics import YOLO
import cv2

class YOLOTracker:
    def __init__(self,target_name=None):
        # 1. 초기 상태 및 변수 설정 (PID의 __init__과 동일)
        self.model = YOLO("yolo11n.pt")
        self.target_name = target_name
        self.tol = 20
        

    def process_frame(self, frame):
        # 2. 매 프레임마다 실행될 핵심 로직 (PID의 update와 동일)
        height, width, _ = frame.shape
        img_area = height * width
        self.center_x = width // 2  # 화면의 정중앙 X좌표 계산 (예: 640/2 = 320)

        results = self.model(frame, verbose=False)
        
        # 물체를 찾았을 때 반환할 오차값 (못 찾으면 None)
        target_percent = None
        error_x = None 

        found_targets = []
        
        # if self.target_name in results[0] :
        for box in results[0].boxes:
            class_id = int(box.cls[0])
            class_name = self.model.names[class_id]
            confidence = float(box.conf[0])

            # 자동 락온 기능
            if self.target_name is None and confidence > 0.6:
                self.target_name = class_name
                print(f"\n🎯 [락온 완료] '{self.target_name}' 추적을 시작합니다!\n")

            # 타겟 발견 및 좌표 계산
            if class_name == self.target_name and confidence > 0.1:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
               # 객체의 크기(면적) 계산 (너비 * 높이)
                area = (x2 - x1) * (y2 - y1)
                
                # 리스트에 (면적, 좌표들, 정확도) 순서로 묶어서 추가
                found_targets.append((area, x1, y1, x2, y2, confidence))

        # 🎯 추가됨: 타겟이 하나라도 발견되었다면?
        if found_targets:
            # 면적(area, 즉 0번째 원소)을 기준으로 내림차순(큰 것부터) 정렬
            found_targets.sort(key=lambda x: x[0], reverse=True)
            
            # 가장 큰 첫 번째 객체만 선택!
            best_target = found_targets[0]
            Area, x1, y1, x2, y2, conf = best_target

            # 오차값 계산 (현재 중심 좌표 - 화면 중앙 좌표)
            x0 = (x2 + x1 - 1) // 2
            error_x = x0 - self.center_x

            target_percent = (Area / img_area) * 100

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{self.target_name} {confidence:.2f} {target_percent:.1f}%", 
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 수정된 프레임과, 계산된 오차값을 같이 반환합니다.
        return frame, error_x , target_percent
    
    def run(self, camera_index=0):
        # 3. 웹캠 구동 및 무한 루프 처리
        url = "http://10.10.14.18:5000/video_feed"
        cap = cv2.VideoCapture(url) # url 사용
        # cap = cv2.VideoCapture(camera_index) # 카메라 사용
        if not cap.isOpened():
            print("웹캠을 열 수 없습니다.")
            return

        print("종료하려면 영상 창을 선택한 상태에서 'q' 키를 누르세요.")

        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 여기서 클래스 내부의 process_frame을 호출합니다.
            annotated_frame, error_x = self.process_frame(frame)
            
            # --- [핵심] 만약 PID 제어기와 연결한다면 여기서 합니다! ---
            # if error_x is not None:
            #     control_signal = pid.update(error_x)
            #     motor_move(control_signal)
            # -----------------------------------------------------

            cv2.imshow('Real-time YOLO Tracker', annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n프로그램을 종료합니다.")
                break

        cap.release()
        cv2.destroyAllWindows()