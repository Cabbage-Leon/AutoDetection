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

@bp.route('/load-url', methods=['POST'])
def load_url():
    """加载URL"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL is required'})
    
    success, message = automation.load_url(url)
    return jsonify({'success': success, 'message': message})

@bp.route('/scrape', methods=['POST'])
def scrape_content():
    """抓取内容"""
    data = request.get_json()
    selector_type = data.get('selector_type')
    selector_value = data.get('selector_value')
    attribute = data.get('attribute')
    
    if not selector_type or not selector_value:
        return jsonify({'success': False, 'error': 'Selector type and value are required'})
    
    success, message, results = automation.scrape_content(selector_type, selector_value, attribute)
    return jsonify({
        'success': success,
        'message': message,
        'results': results if success else None
    })

@bp.route('/execute-action', methods=['POST'])
def execute_action():
    """执行元素操作"""
    data = request.get_json()
    selector_type = data.get('selector_type')
    selector_value = data.get('selector_value')
    action = data.get('action')
    
    if not all([selector_type, selector_value, action]):
        return jsonify({'success': False, 'error': 'Selector type, value and action are required'})
    
    # 获取额外参数
    kwargs = {}
    if action == 'input':
        kwargs['input_text'] = data.get('input_text')
    elif action == 'select':
        kwargs['option_value'] = data.get('option_value')
    
    success, message = automation.execute_action(selector_type, selector_value, action, **kwargs)
    return jsonify({'success': success, 'message': message})

@bp.route('/close', methods=['POST'])
def close_browser():
    """关闭浏览器"""
    success = automation.close()
    return jsonify({'success': success}) 