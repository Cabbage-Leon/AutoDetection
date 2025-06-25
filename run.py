from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5000,       # 指定端口
        debug=True,      # 启用调试模式
        threaded=True,   # 启用多线程
    ) 