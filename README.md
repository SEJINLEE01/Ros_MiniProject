# Ros_MiniProject
## Robot 폴더
로봇에서 가상환경 /rapi/bin/activate 활성화하고  
ros2 launch turtlebot3_bringup.launch robot.launch.py 실행

## chase_object
ros2 환경 불러온 후
ros2 run chase_object yolo_ros_node 실행 후  
ros2 run chase_object control_rotate 실행

타겟을 변경하고 싶으면 yolo_ros_node에서 변경

원하는 물체를 카메라의 중심에 가도록하고 원하는 거리까지만 가도록 되어있습니다  
(전체 이미지에서 물체가 차지하고 있는 면적과 중심 픽셀에서의 좌우 거리차 사용)
<img width="538" height="426" alt="Screencast from 2026-05-14 16-02-32_1(1)" src="https://github.com/user-attachments/assets/04dab098-86be-45bc-aca1-bf20e291883e" />

시연 영상  
https://youtu.be/u7CR69-9iPM
