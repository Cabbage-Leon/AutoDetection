"""
秒杀功能API路由
提供任务管理、元素选择、时间同步等API接口
"""

from flask import request, jsonify, render_template, current_app
from . import bp
from .core.scheduler import scheduler
from .core.time_sync import time_sync
from .core.browser_manager import browser_manager
from .core.element_selector import element_selector
from .models.task import SeckillTask
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@bp.route('/')
def index():
    """秒杀功能主页面"""
    return render_template('seckill/index.html')

@bp.route('/task-manager')
def task_manager():
    """任务管理页面"""
    return render_template('seckill/task_manager.html')

@bp.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务"""
    try:
        tasks = scheduler.get_all_tasks()
        return jsonify({
            'success': True,
            'data': tasks
        })
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['name', 'url', 'target_selector', 'target_type', 'execution_time']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必需字段: {field}'
                }), 400
        
        # 解析执行时间
        try:
            execution_time = datetime.fromisoformat(data['execution_time'])
        except ValueError:
            return jsonify({
                'success': False,
                'message': '执行时间格式无效'
            }), 400
        
        # 创建任务
        task = SeckillTask(
            name=data['name'],
            url=data['url'],
            target_selector=data['target_selector'],
            target_type=data['target_type'],
            execution_time=execution_time,
            countdown_selector=data.get('countdown_selector'),
            countdown_type=data.get('countdown_type'),
            frequency=data.get('frequency', 1),
            max_attempts=data.get('max_attempts', 10),
            timezone=data.get('timezone', 'Asia/Shanghai'),
            click_mode=data.get('click_mode', 'single'),
            click_count=data.get('click_count', 1),
            click_interval=data.get('click_interval', 0.1),
            countdown_threshold=data.get('countdown_threshold', 0)
        )
        
        # 添加到调度器
        if scheduler.add_task(task):
            return jsonify({
                'success': True,
                'message': '任务创建成功',
                'data': task.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务创建失败'
            }), 500
            
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取指定任务"""
    try:
        task_info = scheduler.get_task_status(task_id)
        if task_info:
            return jsonify({
                'success': True,
                'data': task_info
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
    except Exception as e:
        logger.error(f"获取任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    try:
        data = request.get_json()
        
        # 获取任务
        if task_id not in scheduler.tasks:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        task = scheduler.tasks[task_id]
        
        # 更新任务配置
        if 'execution_time' in data:
            task.execution_time = datetime.fromisoformat(data['execution_time'])
        
        # 更新其他字段
        update_fields = ['name', 'url', 'target_selector', 'target_type', 
                        'countdown_selector', 'countdown_type', 'frequency', 
                        'max_attempts', 'timezone', 'click_mode', 'click_count',
                        'click_interval', 'countdown_threshold']
        
        for field in update_fields:
            if field in data:
                setattr(task, field, data[field])
        
        return jsonify({
            'success': True,
            'message': '任务更新成功',
            'data': task.to_dict()
        })
        
    except Exception as e:
        logger.error(f"更新任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    try:
        if scheduler.remove_task(task_id):
            return jsonify({
                'success': True,
                'message': '任务删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务删除失败'
            }), 500
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/tasks/<task_id>/start', methods=['POST'])
def start_task(task_id):
    """启动任务"""
    try:
        if scheduler.start_task(task_id):
            return jsonify({
                'success': True,
                'message': '任务启动成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务启动失败'
            }), 500
    except Exception as e:
        logger.error(f"启动任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/tasks/<task_id>/stop', methods=['POST'])
def stop_task(task_id):
    """停止任务"""
    try:
        if scheduler.stop_task(task_id):
            return jsonify({
                'success': True,
                'message': '任务停止成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务停止失败'
            }), 500
    except Exception as e:
        logger.error(f"停止任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/tasks/<task_id>/reset', methods=['POST'])
def reset_task(task_id):
    """重置任务"""
    try:
        if task_id in scheduler.tasks:
            task = scheduler.tasks[task_id]
            task.reset()
            return jsonify({
                'success': True,
                'message': '任务重置成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
    except Exception as e:
        logger.error(f"重置任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/browser/load-url', methods=['POST'])
def load_url():
    """加载URL"""
    try:
        data = request.get_json()
        if not data or 'url' not in data or 'task_id' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数'
            }), 400
        
        success, message = browser_manager.load_url(data['task_id'], data['url'])
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"加载URL失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/browser/find-elements', methods=['POST'])
def find_elements():
    """查找元素"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data or 'selector_type' not in data or 'selector_value' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数'
            }), 400
        
        success, message, results = browser_manager.find_element(
            data['task_id'],
            data['selector_type'],
            data['selector_value']
        )
        
        return jsonify({
            'success': success,
            'message': message,
            'data': results
        })
    except Exception as e:
        logger.error(f"查找元素失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/browser/click-element', methods=['POST'])
def click_element():
    """点击元素"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data or 'selector_type' not in data or 'selector_value' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数'
            }), 400
        
        success, message = browser_manager.click_element(
            data['task_id'],
            data['selector_type'],
            data['selector_value']
        )
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"点击元素失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/browser/input-text', methods=['POST'])
def input_text():
    """输入文本"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data or 'selector_type' not in data or 'selector_value' not in data or 'text' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数'
            }), 400
        
        success, message = browser_manager.input_text(
            data['task_id'],
            data['selector_type'],
            data['selector_value'],
            data['text']
        )
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"输入文本失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/browser/page-info', methods=['POST'])
def get_page_info():
    """获取页面信息"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数'
            }), 400
        
        success, message, page_info = browser_manager.get_page_info(data['task_id'])
        return jsonify({
            'success': success,
            'message': message,
            'data': page_info
        })
    except Exception as e:
        logger.error(f"获取页面信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/time/sync', methods=['POST'])
def sync_time():
    """同步时间"""
    try:
        success = time_sync.sync_time()
        time_info = time_sync.get_time_info()
        
        return jsonify({
            'success': success,
            'message': '时间同步成功' if success else '时间同步失败',
            'data': time_info
        })
    except Exception as e:
        logger.error(f"时间同步失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/time/info', methods=['GET'])
def get_time_info():
    """获取时间信息"""
    try:
        time_info = time_sync.get_time_info()
        return jsonify({
            'success': True,
            'data': time_info
        })
    except Exception as e:
        logger.error(f"获取时间信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/time/countdown', methods=['POST'])
def get_countdown():
    """获取倒计时"""
    try:
        data = request.get_json()
        if not data or 'target_time' not in data:
            return jsonify({
                'success': False,
                'message': '缺少目标时间参数'
            }), 400
        
        target_time = datetime.fromisoformat(data['target_time'])
        countdown = time_sync.get_countdown(target_time)
        
        return jsonify({
            'success': True,
            'data': {
                'countdown': countdown,
                'target_time': target_time.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"获取倒计时失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/elements/generate-selectors', methods=['POST'])
def generate_selectors():
    """生成元素选择器"""
    try:
        data = request.get_json()
        if not data or 'element_info' not in data:
            return jsonify({
                'success': False,
                'message': '缺少元素信息'
            }), 400
        
        selectors = element_selector.generate_selectors(data['element_info'])
        optimized = element_selector.optimize_selectors(selectors)
        
        return jsonify({
            'success': True,
            'data': {
                'selectors': selectors,
                'optimized': optimized
            }
        })
    except Exception as e:
        logger.error(f"生成选择器失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/elements/validate-selector', methods=['POST'])
def validate_selector():
    """验证选择器"""
    try:
        data = request.get_json()
        if not data or 'selector_type' not in data or 'selector_value' not in data:
            return jsonify({
                'success': False,
                'message': '缺少选择器参数'
            }), 400
        
        is_valid, message = element_selector.validate_selector(
            data['selector_type'],
            data['selector_value']
        )
        
        return jsonify({
            'success': True,
            'data': {
                'is_valid': is_valid,
                'message': message
            }
        })
    except Exception as e:
        logger.error(f"验证选择器失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """获取调度器状态"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'is_running': scheduler.is_running,
                'total_tasks': len(scheduler.tasks),
                'running_tasks': len(scheduler.running_tasks)
            }
        })
    except Exception as e:
        logger.error(f"获取调度器状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """启动调度器"""
    try:
        scheduler.start()
        return jsonify({
            'success': True,
            'message': '调度器启动成功'
        })
    except Exception as e:
        logger.error(f"启动调度器失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """停止调度器"""
    try:
        scheduler.stop()
        return jsonify({
            'success': True,
            'message': '调度器停止成功'
        })
    except Exception as e:
        logger.error(f"停止调度器失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/demo')
def seckill_demo():
    """秒杀模拟Demo页面"""
    return render_template('seckill/demo.html') 