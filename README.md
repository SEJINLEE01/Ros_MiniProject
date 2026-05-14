# Ros_MiniProject
## Robot 폴더
로봇에서 가상환경 /rapi/bin/activate 활성화하고  
ros2 launch turtlebot3_bringup.launch robot.launch.py 실행

## chase_object
ros2 환경 불러온 후
ros2 run chase_object yolo_ros_node 실행 후
ros2 run chase_object control_rotate 실행

타겟을 변경하고 싶으면 yolo_ros_node에서 변경
