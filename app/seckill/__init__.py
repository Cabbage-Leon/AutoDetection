"""
秒杀功能模块
提供智能秒杀、定时任务、元素选择等功能
"""

from flask import Blueprint

# 创建秒杀模块蓝图
bp = Blueprint('seckill', __name__, 
               template_folder='templates',
               url_prefix='/seckill')

# 导入路由
from . import routes 