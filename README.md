# Ros_MiniProject

## 프로젝트 개요
본 프로젝트는 로봇 운영체제(ROS)의 표준 플랫폼인 터틀봇(TurtleBot)을 활용하여 로보틱스의 기초 메커니즘을 이해하고, 실시간 객체 추적(Object Tracking) 알고리즘을 설계하는 것을 목표로 합니다.

단순한 주행을 넘어, 로봇이 외부 환경을 인식하고 특정 대상을 끝까지 추적하는 과정을 직접 설계함으로써 자율주행 시스템의 핵심 파이프라인(인지-판단-제어)을 체계적으로 학습합니다.

PID 제어와 추적 알고리즘의 핵심 원리를 파악하고 전문성을 고양하는 데 기여할 것으로 기대됩니다.

## 실행 방법

### Robot 폴더
로봇에서 가상환경 /rapi/bin/activate 활성화하고  
ros2 launch turtlebot3_bringup.launch robot.launch.py 실행

### chase_object
ros2 환경 불러온 후
ros2 run chase_object yolo_ros_node 실행 후  
ros2 run chase_object control_rotate 실행
타겟을 변경하고 싶으면 yolo_ros_node에서 변경
ultralytics문제로 빌드가 안 될 경우 export PYTHONPATH=/home/mj/venv/ch_obj/lib/python3.12/site-packages:$PYTHONPATH 입력

---
- 원하는 물체를 카메라의 중심에 가도록하고 원하는 거리까지만 가도록 되어있습니다  
(전체 이미지에서 물체가 차지하고 있는 면적과 중심 픽셀에서의 좌우 거리차 사용)
<img width="538" height="426" alt="Screencast from 2026-05-14 16-02-32_1(1)" src="https://github.com/user-attachments/assets/04dab098-86be-45bc-aca1-bf20e291883e" />

시연 영상  
https://youtu.be/u7CR69-9iPM
