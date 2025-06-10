import os

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    
    # YOLO检测配置
    DETECTION_FPS = 20  # 提高帧率以获得更流畅的视频流
    FRAME_QUEUE_SIZE = 1000  # 增加队列大小以缓存更多帧
    DETECTION_QUEUE_SIZE = 1000
    YOLO_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yolo11n.pt')

class DevelopmentConfig(Config):
    DEBUG = True
    # 开发环境特定配置
    DETECTION_FPS = 20
    FRAME_QUEUE_SIZE = 1000
    DETECTION_QUEUE_SIZE = 1000

class ProductionConfig(Config):
    DEBUG = False
    # 生产环境特定配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    
    # 生产环境性能优化
    DETECTION_FPS = 15  # 提高帧率但仍保持合理性能
    FRAME_QUEUE_SIZE = 8  # 增加队列大小
    DETECTION_QUEUE_SIZE = 8

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 