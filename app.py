from flask import Flask, render_template, request, jsonify, Response
import cv2
import numpy as np
from ultralytics import YOLO
import base64
import os
from PIL import Image, ImageGrab
import io
import threading
import time
from queue import Queue
from collections import Counter

app = Flask(__name__)

# 初始化YOLO模型
print("正在加载YOLO模型...")
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yolo11n.pt')
model = YOLO(model_path)
print("模型加载完成！")

# 全局变量
monitoring = False
processing = False  # 新增：控制处理线程状态
frame_queue = Queue(maxsize=10)
detection_queue = Queue(maxsize=10)
processing_complete = threading.Event()  # 新增：用于通知处理完成

def process_frame():
    """处理帧的函数"""
    global processing
    while monitoring:
        try:
            # 捕获屏幕
            screen = np.array(ImageGrab.grab())
            frame = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
            
            # 使用YOLO进行检测
            results = model(frame)
            
            # 统计检测到的对象
            detections = Counter()
            
            # 处理检测结果
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cls = box.cls[0].cpu().numpy()
                    cls_name = model.names[int(cls)]
                    
                    # 更新检测统计
                    detections[cls_name] += 1
                    
                    # 绘制边界框和标签
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    label = f'{cls_name} {conf:.2f}'
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 将处理后的帧放入队列
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # 更新帧队列
            if frame_queue.full():
                frame_queue.get()
            frame_queue.put(frame_base64)
            
            # 更新检测信息队列
            if detection_queue.full():
                detection_queue.get()
            detection_queue.put(dict(detections))
            
            time.sleep(0.05)  # 20 FPS
            
        except Exception as e:
            print(f"处理错误: {str(e)}")
            break
    
    # 处理完所有帧后设置事件
    processing = False
    processing_complete.set()

def generate_frames():
    """生成器函数，用于SSE流"""
    while monitoring or not frame_queue.empty():
        if not frame_queue.empty():
            frame = frame_queue.get()
            detections = detection_queue.get() if not detection_queue.empty() else {}
            yield f"data: {frame}\n\n"
            yield f"event: detections\ndata: {detections}\n\n"
        elif monitoring:  # 如果还在监控中，短暂等待新帧
            time.sleep(0.01)
        else:  # 如果停止监控且队列为空，结束生成
            break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_monitoring')
def start_monitoring():
    """开始监控"""
    global monitoring, processing
    if not monitoring:
        monitoring = True
        processing = True
        processing_complete.clear()
        threading.Thread(target=process_frame, daemon=True).start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/stop_monitoring')
def stop_monitoring():
    """停止监控"""
    global monitoring
    if monitoring:
        monitoring = False  # 停止接收新帧
        # 等待处理线程完成
        if processing:
            processing_complete.wait(timeout=5.0)  # 最多等待5秒
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'already_stopped'})

@app.route('/video_feed')
def video_feed():
    """视频流路由"""
    return Response(generate_frames(),
                   mimetype='text/event-stream')

@app.route('/detect', methods=['POST'])
def detect():
    try:
        # 获取上传的图片
        file = request.files['image']
        if file:
            # 读取图片
            image_bytes = file.read()
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 使用YOLO进行检测
            results = model(img)
            
            # 处理检测结果
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # 获取边界框坐标
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    # 获取置信度
                    conf = box.conf[0].cpu().numpy()
                    # 获取类别
                    cls = box.cls[0].cpu().numpy()
                    
                    # 在图像上绘制边界框
                    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    # 添加标签
                    label = f'{model.names[int(cls)]} {conf:.2f}'
                    cv2.putText(img, label, (int(x1), int(y1) - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 将处理后的图像转换为base64
            _, buffer = cv2.imencode('.jpg', img)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return jsonify({
                'success': True,
                'image': img_base64
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True) 