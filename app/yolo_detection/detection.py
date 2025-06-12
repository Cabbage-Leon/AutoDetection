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
import os
import queue

class YOLODetection:
    def __init__(self):
        """初始化检测器"""
        self.model = None
        self.monitoring = False
        self.processing = False
        self.processing_complete = threading.Event()
        self.frame_queue = queue.Queue(maxsize=5)  # 增加队列大小以存储更多帧
        self.detection_queue = queue.Queue(maxsize=2)  # 检测结果队列保持较小
        self.display_fps = 30  # 显示帧率
        self.detect_fps = 5    # 检测帧率
        self.app = None
        self.last_frame_time = 0
        self.last_detect_time = 0
        self.frame_interval = 1.0 / self.display_fps
        self.detect_interval = 1.0 / self.detect_fps
        self.processing_thread = None
        self.capture_thread = None
        self.current_frame = None
        self.frame_lock = threading.Lock()

    def initialize(self, app):
        """初始化检测器，设置队列大小"""
        self.app = app
        with app.app_context():
            self.frame_queue = Queue(maxsize=app.config['FRAME_QUEUE_SIZE'])
            self.detection_queue = Queue(maxsize=app.config['DETECTION_QUEUE_SIZE'])
            self.display_fps = app.config['DETECTION_FPS']
            self.detect_fps = app.config['DETECTION_FPS']

    def initialize_model(self, model_path):
        """初始化YOLO模型"""
        try:
            # 设置资源目录
            resource_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'yolo')
            os.makedirs(resource_dir, exist_ok=True)
            
            # 初始化模型
            self.model = YOLO(model_path)
            
            # 设置资源目录
            self.model.source = resource_dir
            
            # 测试模型是否正常工作
            test_image = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self.model(test_image)
            
            return True, None
        except Exception as e:
            print(f"模型初始化错误: {str(e)}")
            return False, str(e)

    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return True, "监控已经在运行"
        
        try:
            self.monitoring = True
            self.processing = True
            self.processing_complete.clear()
            
            # 启动捕获线程
            self.capture_thread = threading.Thread(target=self._capture_frames)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            # 启动处理线程
            self.processing_thread = threading.Thread(target=self._process_frames)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            return True, "监控已启动"
        except Exception as e:
            self.monitoring = False
            self.processing = False
            return False, str(e)

    def _capture_frames(self):
        """捕获屏幕帧的线程函数"""
        while self.monitoring:
            try:
                # 捕获屏幕
                screen = np.array(ImageGrab.grab())
                frame = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
                
                # 更新当前帧
                with self.frame_lock:
                    self.current_frame = frame.copy()
                
                # 将原始帧放入队列
                if self.frame_queue.full():
                    self.frame_queue.get()
                self.frame_queue.put(frame)
                
                time.sleep(0.1)  # 短暂休眠以减少CPU使用
            except Exception as e:
                print(f"捕获错误: {str(e)}")
                break

    def _process_frames(self):
        """处理帧的线程函数"""
        if not self.app:
            print("Error: Application context not initialized")
            return

        with self.app.app_context():
            while self.monitoring:
                try:
                    current_time = time.time()
                    if current_time - self.last_detect_time < self.detect_interval:
                        time.sleep(0.01)
                        continue

                    # 获取当前帧
                    with self.frame_lock:
                        if self.current_frame is None:
                            continue
                        frame = self.current_frame.copy()
                    
                    # 使用YOLO进行检测
                    results = self.model(frame)
                    
                    # 处理检测结果
                    detections = []
                    
                    # 处理检测结果
                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = float(box.conf[0].cpu().numpy())
                            cls = int(box.cls[0].cpu().numpy())
                            cls_name = self.model.names[cls]
                            
                            # 添加到检测结果列表
                            detections.append({
                                'class': cls_name,
                                'confidence': conf,
                                'x': int(x1),
                                'y': int(y1),
                                'width': int(x2 - x1),
                                'height': int(y2 - y1)
                            })
                            
                            # 绘制边界框和标签
                            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                            label = f'{cls_name} {conf:.2f}'
                            cv2.putText(frame, label, (int(x1), int(y1) - 10), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # 更新检测信息队列
                    if self.detection_queue.full():
                        self.detection_queue.get()
                    self.detection_queue.put(json.dumps(detections))
                    
                    self.last_detect_time = current_time
                    
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
                    
                current_time = time.time()
                if current_time - self.last_frame_time < self.frame_interval:
                    time.sleep(0.1)
                    continue

                # 发送检测结果（如果有）
                if not self.detection_queue.empty():
                    detections = self.detection_queue.get()
                    yield f"event: detections\ndata: {detections}\n\n"
                
                # 发送视频帧
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get()
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    yield f"data: {frame_base64}\n\n"
                    self.last_frame_time = current_time
                else:
                    # 如果队列为空，发送心跳包保持连接
                    yield f"data: heartbeat\n\n"
                    time.sleep(0.01)
        except GeneratorExit:
            print("SSE connection closed")
        except Exception as e:
            print(f"SSE error: {str(e)}")

    def detect_image(self, image_data):
        """通用检测方法，用于向后兼容"""
        return self.web_detect_image(image_data)

    def web_detect_image(self, image_data):
        """网页应用使用的检测方法
        
        Args:
            image_data: 图像文件的二进制数据
            
        Returns:
            tuple: (success, result)
                - success: 布尔值，表示检测是否成功
                - result: 如果成功，返回带标注的图像；如果失败，返回错误信息
        """
        try:
            # 将图像数据转换为numpy数组
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return False, "无法解码图像数据"

            # 进行检测
            results = self.model(img)
            
            # 处理检测结果
            detections = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())
                    name = self.model.names[cls]
                    
                    detections.append({
                        'class': name,
                        'confidence': conf,
                        'x': int(x1),
                        'y': int(y1),
                        'width': int(x2 - x1),
                        'height': int(y2 - y1)
                    })

            # 在图像上绘制检测结果
            annotated_img = img.copy()
            for det in detections:
                x, y, w, h = det['x'], det['y'], det['width'], det['height']
                cv2.rectangle(annotated_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                label = f"{det['class']} {det['confidence']:.2f}"
                cv2.putText(annotated_img, label, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # 将标注后的图像转换为base64
            _, buffer = cv2.imencode('.jpg', annotated_img)
            img_base64 = base64.b64encode(buffer).decode('utf-8')

            return True, {
                'image': img_base64,
                'detections': detections
            }

        except Exception as e:
            print(f"检测过程出错: {str(e)}")
            return False, str(e)

    def extension_detect_image(self, image_data):
        """浏览器插件使用的检测方法
        
        Args:
            image_data: base64编码的图像数据
            
        Returns:
            tuple: (success, result)
                - success: 布尔值，表示检测是否成功
                - result: 如果成功，返回检测结果字典；如果失败，返回错误信息
        """
        try:
            # 解码base64图像数据
            if isinstance(image_data, str):
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data

            # 将图像数据转换为numpy数组
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return False, "无法解码图像数据"

            # 进行检测
            results = self.model(img)
            
            # 处理检测结果
            detections = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())
                    name = self.model.names[cls]
                    
                    detections.append({
                        'class': name,
                        'confidence': conf,
                        'x': int(x1),
                        'y': int(y1),
                        'width': int(x2 - x1),
                        'height': int(y2 - y1)
                    })

            # 在图像上绘制检测结果
            annotated_img = img.copy()
            for det in detections:
                x, y, w, h = det['x'], det['y'], det['width'], det['height']
                cv2.rectangle(annotated_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                label = f"{det['class']} {det['confidence']:.2f}"
                cv2.putText(annotated_img, label, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # 将标注后的图像转换为base64
            _, buffer = cv2.imencode('.jpg', annotated_img)
            img_base64 = base64.b64encode(buffer).decode('utf-8')

            return True, {
                'image': img_base64,
                'detections': detections
            }

        except Exception as e:
            print(f"检测过程出错: {str(e)}")
            return False, str(e)

    def stop_monitoring(self):
        """停止监控"""
        if not self.monitoring:
            return True, "监控未在运行"
        
        try:
            self.monitoring = False
            self.processing = False
            
            # 等待处理完成
            if self.processing_complete:
                self.processing_complete.wait(timeout=2.0)
            
            # 清空队列
            while not self.frame_queue.empty():
                self.frame_queue.get()
            while not self.detection_queue.empty():
                self.detection_queue.get()
            
            return True, "监控已停止"
        except Exception as e:
            return False, str(e)

# 创建全局检测实例
detection = YOLODetection() 