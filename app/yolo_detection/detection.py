import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image, ImageGrab
import base64
import threading
import time
from queue import Queue
from collections import Counter
from flask import current_app
import json

class YOLODetection:
    def __init__(self):
        self.monitoring = False
        self.processing = False
        self.frame_queue = None
        self.detection_queue = None
        self.processing_complete = threading.Event()
        self.model = None
        self.detection_thread = None
        self.app = None
        self.fps = 20  # 默认帧率

    def initialize(self, app):
        """初始化检测器，设置队列大小"""
        self.app = app
        with app.app_context():
            self.frame_queue = Queue(maxsize=app.config['FRAME_QUEUE_SIZE'])
            self.detection_queue = Queue(maxsize=app.config['DETECTION_QUEUE_SIZE'])
            self.fps = app.config['DETECTION_FPS']

    def initialize_model(self, model_path):
        """初始化YOLO模型"""
        try:
            self.model = YOLO(model_path)
            return True, None
        except Exception as e:
            return False, str(e)

    def start_monitoring(self):
        """开始监控"""
        if not self.monitoring and self.model:
            self.monitoring = True
            self.processing = True
            self.processing_complete.clear()
            self.detection_thread = threading.Thread(target=self._process_frame, daemon=True)
            self.detection_thread.start()
            return True, None
        return False, "Already running or model not initialized"

    def stop_monitoring(self):
        """停止监控"""
        if self.monitoring:
            self.monitoring = False
            if self.processing:
                self.processing_complete.wait(timeout=5.0)
            return True, None
        return False, "Not running"

    def _process_frame(self):
        """处理帧的函数"""
        if not self.app:
            print("Error: Application context not initialized")
            return

        with self.app.app_context():
            while self.monitoring:
                try:
                    # 捕获屏幕
                    screen = np.array(ImageGrab.grab())
                    frame = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
                    
                    # 使用YOLO进行检测
                    results = self.model(frame)
                    
                    # 统计检测到的对象
                    detections = Counter()
                    
                    # 处理检测结果
                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = box.cls[0].cpu().numpy()
                            cls_name = self.model.names[int(cls)]
                            
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
                    if self.frame_queue.full():
                        self.frame_queue.get()
                    self.frame_queue.put(frame_base64)
                    
                    # 更新检测信息队列
                    if self.detection_queue.full():
                        self.detection_queue.get()
                    # 确保检测结果是有效的JSON字符串
                    detections_dict = dict(detections)
                    self.detection_queue.put(json.dumps(detections_dict))
                    
                    time.sleep(1.0 / self.fps)
                    
                except Exception as e:
                    print(f"处理错误: {str(e)}")
                    break
            
            self.processing = False
            self.processing_complete.set()

    def generate_frames(self):
        """生成器函数，用于SSE流"""
        try:
            while True:
                if not self.monitoring:
                    break
                    
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get()
                    detections = self.detection_queue.get() if not self.detection_queue.empty() else '{}'
                    
                    # 发送视频帧
                    yield f"data: {frame}\n\n"
                    
                    # 发送检测结果
                    yield f"event: detections\ndata: {detections}\n\n"
                else:
                    # 如果队列为空，发送心跳包保持连接
                    yield f"data: heartbeat\n\n"
                    time.sleep(0.1)
        except GeneratorExit:
            print("SSE connection closed")
        except Exception as e:
            print(f"SSE error: {str(e)}")

    def detect_image(self, image_bytes):
        """检测单张图片"""
        try:
            # 读取图片
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 使用YOLO进行检测
            results = self.model(img)
            
            # 处理检测结果
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cls = box.cls[0].cpu().numpy()
                    
                    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    label = f'{self.model.names[int(cls)]} {conf:.2f}'
                    cv2.putText(img, label, (int(x1), int(y1) - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 将处理后的图像转换为base64
            _, buffer = cv2.imencode('.jpg', img)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return True, img_base64
        except Exception as e:
            return False, str(e)

# 创建全局检测实例
detection = YOLODetection() 