import cv2
import time
import threading
import subprocess
import numpy as np
from flask import Flask, Response, render_template

app = Flask(__name__)

# 1. rpicam-vid를 실행하여 영상을 바이트 스트림으로 가져옵니다.
# rpicam-hello가 작동하는 환경이므로 이 명령어도 반드시 작동합니다.
command = [
    'rpicam-vid',
    '-t', '0',                # 무한 실행
    '--width', '640',         # 해상도 설정
    '--height', '480',
    '--mode', '1640:1232',    # 핵심: 센서 전체 면적을 사용하는 모드 강제
    '--inline',               # 헤더(SPS/PPS)를 매 프레임 포함
    '--nopreview',            # 터미널 창에 화면 안 띄움
    '--codec', 'mjpeg',       # 처리가 쉬운 MJPEG 포맷
    '--framerate', '20',      # 프레임 레이트 조절
    '-o', '-'                 # 출력을 파일이 아닌 표준 출력(stdout)으로 보냄
]

# rpicam-vid 프로세스 시작
proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10**6)

# 최신 프레임을 저장할 전역 변수와 락
global_frame = None
frame_lock = threading.Lock()

def capture_frames():
    """백그라운드 스레드: rpicam-vid의 출력(stdout)에서 JPEG 프레임을 잘라냄"""
    global global_frame
    buffer = b""
    
    while True:
        # 데이터를 4096바이트씩 읽어옴
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        buffer += chunk
        
        # JPEG 이미지의 시작(0xffd8)과 끝(0xffd9)을 찾습니다.
        a = buffer.find(b'\xff\xd8')
        b = buffer.find(b'\xff\xd9')
        
        if a != -1 and b != -1:
            # 하나의 JPEG 프레임 추출
            jpg = buffer[a:b+2]
            # 추출한 부분은 버퍼에서 삭제
            buffer = buffer[b+2:]
            
            with frame_lock:
                global_frame = jpg

# 백그라운드 스레드 시작
capture_thread = threading.Thread(target=capture_frames)
capture_thread.daemon = True
capture_thread.start()

def gen_frames():
    """웹 브라우저에 스트리밍 전달"""
    while True:
        with frame_lock:
            frame = global_frame
        
        if frame is None:
            time.sleep(0.01)
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.05) # 약 20 FPS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        # rpicam 엔진은 중복 실행에 민감하므로 use_reloader=False 필수
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    finally:
        # 종료 시 프로세스 살해
        proc.terminate()