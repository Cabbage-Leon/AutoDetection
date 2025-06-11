from flask import Blueprint, request, jsonify, render_template
from .automation import BrowserAutomation

bp = Blueprint('browser_automation', __name__, 
               template_folder='templates',
               url_prefix='/browser-automation')
automation = BrowserAutomation()

@bp.route('/')
def index():
    """渲染浏览器自动化页面"""
    return render_template('browser_automation/index.html')

@bp.route('/seckill')
def seckill():
    return render_template('browser_automation/seckill.html')

@bp.route('/load-url', methods=['POST'])
def load_url():
    """加载URL"""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'success': False, 'message': 'URL is required'})
    
    success, message = automation.load_url(data['url'])
    return jsonify({'success': success, 'message': message})

@bp.route('/scrape', methods=['POST'])
def scrape():
    """抓取内容"""
    data = request.get_json()
    if not data or 'selector_type' not in data or 'selector_value' not in data:
        return jsonify({'success': False, 'message': 'Selector type and value are required'})
    
    success, message, results = automation.scrape_content(
        data['selector_type'],
        data['selector_value'],
        data.get('attribute')
    )
    return jsonify({'success': success, 'message': message, 'results': results})

@bp.route('/execute-action', methods=['POST'])
def execute_action():
    """执行元素操作"""
    data = request.get_json()
    if not data or 'selector_type' not in data or 'selector_value' not in data or 'action' not in data:
        return jsonify({'success': False, 'message': 'Selector type, value and action are required'})
    
    success, message = automation.execute_action(
        data['selector_type'],
        data['selector_value'],
        data['action'],
        **{k: v for k, v in data.items() if k not in ['selector_type', 'selector_value', 'action']}
    )
    return jsonify({'success': success, 'message': message})

@bp.route('/close', methods=['POST'])
def close():
    """关闭浏览器"""
    success = automation.close()
    return jsonify({'success': success}) 