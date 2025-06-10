from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化YOLO检测
    from app.yolo_detection.detection import detection
    detection.initialize(app)  # 先初始化队列
    success, error = detection.initialize_model(app.config['YOLO_MODEL_PATH'])
    if not success:
        print(f"YOLO模型初始化失败: {error}")
    else:
        print("YOLO模型初始化成功！")

    # 注册蓝图
    from app.yolo_detection.routes import bp as yolo_bp
    app.register_blueprint(yolo_bp)

    from app.browser_automation import bp as browser_automation_bp
    app.register_blueprint(browser_automation_bp)
    

    # 设置根路由重定向到YOLO检测页面
    @app.route('/')
    def index():
        return yolo_bp.url_prefix + '/'

    return app 