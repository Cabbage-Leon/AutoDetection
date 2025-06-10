from flask import Blueprint, render_template, request, jsonify, Response
from .detection import detection
from flask import current_app
import time

bp = Blueprint('yolo_detection', __name__,
               template_folder='templates',
               url_prefix='/yolo-detection')

@bp.route('/')
def index():
    return render_template('yolo_detection/index.html')

@bp.route('/start')
def start_monitoring():
    success, error = detection.start_monitoring()
    return jsonify({'status': 'started' if success else 'error', 'error': error})

@bp.route('/stop')
def stop_monitoring():
    success, error = detection.stop_monitoring()
    return jsonify({'status': 'stopped' if success else 'error', 'error': error})

@bp.route('/video-feed')
def video_feed():
    """视频流路由"""
    return Response(detection.generate_frames(),
                   mimetype='text/event-stream')

@bp.route('/detect', methods=['POST'])
def detect():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file provided'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    success, result = detection.detect_image(file.read())
    if success:
        return jsonify({'success': True, 'image': result})
    else:
        return jsonify({'success': False, 'error': result}) 