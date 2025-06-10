import os
from app import create_app
from config import config

# 获取环境配置
env = os.environ.get('FLASK_ENV', 'default')
app = create_app(config[env])

if __name__ == '__main__':
    app.run() 