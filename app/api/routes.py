from flask import Blueprint, request, jsonify
from app.yolo_detection.detection import detection
import base64
import numpy as np
import cv2

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/detect', methods=['POST', 'OPTIONS'])
def extension_detect():
    """浏览器插件使用的检测接口"""
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        # 获取图像数据
        data = request.get_json()
        if not data or 'image' not in data:
            print("请求中缺少图像数据")
            return jsonify({'error': 'No image data provided'}), 400

        # 进行检测
        success, results = detection.extension_detect_image(data['image'])
        
        if not success:
            print(f"检测失败: {results}")
            return jsonify({'error': results}), 500

        print(f"浏览器插件检测成功，返回 {len(results['detections'])} 个结果")
        response = jsonify(results)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        print(f"API错误: {str(e)}")
        response = jsonify({'error': str(e)}), 500
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

@bp.route('/web-detect', methods=['POST'])
def web_detect():
    """网页应用使用的检测接口"""
    try:
        # 获取图像数据
        if 'image' not in request.files:
            print("请求中缺少图像文件")
            return jsonify({'error': 'No image file provided'}), 400

        image_file = request.files['image']
        if not image_file:
            print("图像文件为空")
            return jsonify({'error': 'Empty image file'}), 400

        # 读取图像数据
        image_bytes = image_file.read()
        print(f"网页应用检测请求 - 图像大小: {len(image_bytes)} 字节")

        # 进行检测
        success, results = detection.detect_image(image_bytes)
        
        if not success:
            print(f"检测失败: {results}")
            return jsonify({'error': results}), 500

        print(f"网页应用检测成功，返回 {len(results['detections'])} 个结果")
        return jsonify(results)

    except Exception as e:
        print(f"API错误: {str(e)}")
        return jsonify({'error': str(e)}), 500 