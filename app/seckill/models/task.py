"""
秒杀任务模型
定义秒杀任务的数据结构和行为
优化版本：支持通用倒计时解析和连续点击模式
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

class SeckillTask:
    """秒杀任务类"""
    
    def __init__(self, 
                 name: str,
                 url: str,
                 target_selector: str,
                 target_type: str,
                 execution_time: datetime,
                 task_id: str = None,
                 countdown_selector: str = None,
                 countdown_type: str = None,
                 frequency: int = 1,
                 max_attempts: int = 10,
                 timezone: str = 'Asia/Shanghai',
                 click_mode: str = 'single',  # single, continuous
                 click_count: int = 1,
                 click_interval: float = 0.1,
                 countdown_threshold: int = 0,
                 preload_seconds: int = 30,
                 countdown_end_flags: list = None,
                 **kwargs):
        """
        初始化秒杀任务
        
        Args:
            name: 任务名称
            url: 目标URL
            target_selector: 目标元素选择器
            target_type: 选择器类型 (css, xpath, text, tag)
            execution_time: 执行时间
            task_id: 任务ID（自动生成）
            countdown_selector: 倒计时元素选择器
            countdown_type: 倒计时选择器类型
            frequency: 执行频率（秒）
            max_attempts: 最大尝试次数
            timezone: 时区
            click_mode: 点击模式 (single: 单次点击, continuous: 连续点击)
            click_count: 连续点击次数
            click_interval: 点击间隔（秒）
            countdown_threshold: 倒计时阈值（秒）
            preload_seconds: 提前预热时间（秒）
            countdown_end_flags: 倒计时结束标志（列表）
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.name = name
        self.url = url
        self.target_selector = target_selector
        self.target_type = target_type
        self.execution_time = execution_time
        self.countdown_selector = countdown_selector
        self.countdown_type = countdown_type
        self.frequency = frequency
        self.max_attempts = max_attempts
        self.timezone = timezone
        self.click_mode = click_mode
        self.click_count = click_count
        self.click_interval = click_interval
        self.countdown_threshold = countdown_threshold
        self.preload_seconds = preload_seconds
        self.countdown_end_flags = countdown_end_flags or []
        
        # 任务状态
        self.attempts = 0
        self.success_count = 0
        self.is_running = False
        self.is_stopped = False
        self.created_at = datetime.now()
        self.last_execution = None
        self.next_execution = execution_time
        
        # 额外配置
        self.config = kwargs
        
        self.logger = logging.getLogger(__name__)
        
    def should_execute(self, current_time: datetime) -> bool:
        """检查是否应该执行任务"""
        if self.is_stopped:
            return False
            
        if self.attempts >= self.max_attempts:
            return False
            
        # 检查是否到达执行时间
        if current_time >= self.execution_time:
            return True
            
        return False
        
    def should_remind(self, current_time: datetime) -> bool:
        """检查是否应该发送提醒"""
        if self.is_stopped:
            return False
            
        # 提前2分钟提醒
        reminder_time = self.execution_time - timedelta(minutes=2)
        return current_time >= reminder_time and current_time < self.execution_time
        
    def get_next_execution(self) -> Optional[datetime]:
        """获取下次执行时间"""
        if self.is_stopped:
            return None
            
        if self.attempts >= self.max_attempts:
            return None
            
        if self.frequency <= 0:
            return None
            
        # 计算下次执行时间
        if self.last_execution:
            return self.last_execution + timedelta(seconds=self.frequency)
        else:
            return self.execution_time
            
    def execute(self) -> bool:
        """执行任务"""
        if self.is_stopped:
            return False
            
        if self.attempts >= self.max_attempts:
            self.logger.info(f"任务 {self.name} 已达到最大尝试次数")
            return False
            
        self.is_running = True
        self.attempts += 1
        self.last_execution = datetime.now()
        
        try:
            self.logger.info(f"开始执行任务: {self.name} (第{self.attempts}次)")
            
            # 执行秒杀逻辑
            success = self._execute_seckill_logic()
            
            if success:
                self.success_count += 1
                self.logger.info(f"任务执行成功: {self.name}")
            else:
                self.logger.warning(f"任务执行失败: {self.name}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"任务执行异常: {str(e)}")
            return False
        finally:
            self.is_running = False
            
    def stop(self):
        """停止任务"""
        self.is_stopped = True
        self.is_running = False
        self.logger.info(f"任务已停止: {self.name}")
        
    def resume(self):
        """恢复任务"""
        self.is_stopped = False
        self.logger.info(f"任务已恢复: {self.name}")
        
    def reset(self):
        """重置任务状态"""
        self.attempts = 0
        self.success_count = 0
        self.is_stopped = False
        self.is_running = False
        self.last_execution = None
        self.next_execution = self.execution_time
        self.logger.info(f"任务已重置: {self.name}")
        
    def _execute_seckill_logic(self) -> bool:
        """执行秒杀逻辑（支持自定义倒计时结束标志和提前预热）"""
        try:
            from ..core.browser_manager import browser_manager
            from ..core.countdown_parser import countdown_parser
            from ..core.time_sync import time_sync
            import time
            self.logger.info(f"开始执行秒杀逻辑: {self.name}")

            # 1. 提前预热：如果当前时间在执行时间前 preload_seconds 秒，先加载页面但不点击
            now = datetime.now()
            preload_time = self.execution_time - timedelta(seconds=self.preload_seconds)
            if now < preload_time:
                wait_seconds = (preload_time - now).total_seconds()
                self.logger.info(f"提前预热，等待 {wait_seconds:.2f} 秒后加载页面")
                time.sleep(wait_seconds)

            # 2. 加载页面（预热或正式执行都要加载）
            success, message = browser_manager.load_url(self.task_id, self.url, force_reload=False)
            if not success:
                self.logger.error(f"加载页面失败: {message}")
                return False
            self.logger.info(f"页面加载成功: {self.url}")

            # 3. 如果是预热阶段，加载后直接返回，等待调度器到正式执行时间再进入下一步
            now = datetime.now()
            if now < self.execution_time:
                wait_seconds = (self.execution_time - now).total_seconds()
                self.logger.info(f"页面已预热，等待 {wait_seconds:.2f} 秒到正式执行时间")
                time.sleep(wait_seconds)

            # 4. 检查倒计时（如果有）：轮询等待，支持自定义结束标志
            if self.countdown_selector and self.countdown_type:
                max_wait = 30  # 最多等待30秒
                poll_interval = 0.5
                waited = 0
                while waited < max_wait:
                    success, message, countdown_elements = browser_manager.find_element(
                        self.task_id, self.countdown_type, self.countdown_selector
                    )
                    if success and countdown_elements:
                        countdown_text = countdown_elements[0].get('text', '')
                        self.logger.info(f"倒计时文本: {countdown_text}")
                        is_ready, ready_message = countdown_parser.is_countdown_ready(
                            countdown_text, self.countdown_threshold, self.countdown_end_flags
                        )
                        if is_ready:
                            self.logger.info(f"倒计时已就绪: {ready_message}")
                            break
                        else:
                            self.logger.info(f"倒计时未就绪: {ready_message}")
                    else:
                        self.logger.warning(f"未找到倒计时元素: {message}")
                    time.sleep(poll_interval)
                    waited += poll_interval
                else:
                    self.logger.warning(f"倒计时等待超时，未检测到结束标志或阈值")
                    return False

            # 5. 查找目标元素
            success, message, elements = browser_manager.find_element(
                self.task_id, self.target_type, self.target_selector
            )
            if not success or not elements:
                self.logger.error(f"未找到目标元素: {message}")
                return False
            self.logger.info(f"找到目标元素: {len(elements)} 个")

            # 6. 根据点击模式执行点击
            if self.click_mode == 'continuous':
                success, message = browser_manager.click_element(
                    self.task_id, self.target_type, self.target_selector,
                    click_count=self.click_count, interval=self.click_interval
                )
                self.logger.info(f"连续点击结果: {message}")
            else:
                success, message = browser_manager.click_element(
                    self.task_id, self.target_type, self.target_selector
                )
                self.logger.info(f"单次点击结果: {message}")
            if not success:
                self.logger.error(f"点击元素失败: {message}")
                return False
            time.sleep(1)
            self.logger.info(f"秒杀执行完成: {self.name}")
            return True
        except Exception as e:
            self.logger.error(f"秒杀逻辑执行异常: {str(e)}")
            return False
        
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'url': self.url,
            'target_selector': self.target_selector,
            'target_type': self.target_type,
            'execution_time': self.execution_time.isoformat(),
            'countdown_selector': self.countdown_selector,
            'countdown_type': self.countdown_type,
            'frequency': self.frequency,
            'max_attempts': self.max_attempts,
            'timezone': self.timezone,
            'click_mode': self.click_mode,
            'click_count': self.click_count,
            'click_interval': self.click_interval,
            'countdown_threshold': self.countdown_threshold,
            'preload_seconds': self.preload_seconds,
            'countdown_end_flags': self.countdown_end_flags,
            'attempts': self.attempts,
            'success_count': self.success_count,
            'is_running': self.is_running,
            'is_stopped': self.is_stopped,
            'created_at': self.created_at.isoformat(),
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'next_execution': self.get_next_execution().isoformat() if self.get_next_execution() else None,
            'config': self.config
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'SeckillTask':
        """从字典创建任务"""
        # 解析时间字段
        execution_time = datetime.fromisoformat(data['execution_time'])
        created_at = datetime.fromisoformat(data['created_at'])
        last_execution = datetime.fromisoformat(data['last_execution']) if data.get('last_execution') else None
        
        # 创建任务实例
        task = cls(
            task_id=data['task_id'],
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
            countdown_threshold=data.get('countdown_threshold', 0),
            preload_seconds=data.get('preload_seconds', 30),
            countdown_end_flags=data.get('countdown_end_flags', []),
            **data.get('config', {})
        )
        
        # 设置状态
        task.attempts = data.get('attempts', 0)
        task.success_count = data.get('success_count', 0)
        task.is_running = data.get('is_running', False)
        task.is_stopped = data.get('is_stopped', False)
        task.created_at = created_at
        task.last_execution = last_execution
        
        return task
        
    def update_config(self, **kwargs):
        """更新任务配置"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.config[key] = value
                
        self.logger.info(f"任务配置已更新: {self.name}")
        
    def get_status_summary(self) -> Dict:
        """获取任务状态摘要"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'status': 'running' if self.is_running else ('stopped' if self.is_stopped else 'pending'),
            'progress': f"{self.attempts}/{self.max_attempts}",
            'success_rate': f"{self.success_count}/{self.attempts}" if self.attempts > 0 else "0/0",
            'next_execution': self.get_next_execution().isoformat() if self.get_next_execution() else None,
            'click_mode': self.click_mode,
            'click_count': self.click_count
        } 