"""
任务调度器
负责管理秒杀任务的执行、暂停、恢复等操作
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from flask import current_app
import logging

class SeckillScheduler:
    """秒杀任务调度器"""
    
    def __init__(self):
        self.tasks: Dict[str, 'SeckillTask'] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.preloading_tasks = set() # 正在预热的任务ID
        self.task_callbacks: Dict[str, List[Callable]] = {}
        self.scheduler_thread = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """启动调度器"""
        if self.is_running:
            return
            
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("秒杀调度器已启动")
        
    def stop(self):
        """停止调度器"""
        self.is_running = False
        # 停止所有运行中的任务
        for task_id in list(self.running_tasks.keys()):
            self.stop_task(task_id)
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("秒杀调度器已停止")
        
    def add_task(self, task: 'SeckillTask') -> bool:
        """添加秒杀任务"""
        try:
            self.tasks[task.task_id] = task
            self.task_callbacks[task.task_id] = []
            self.logger.info(f"添加任务成功: {task.name} (ID: {task.task_id})")
            return True
        except Exception as e:
            self.logger.error(f"添加任务失败: {str(e)}")
            return False
            
    def remove_task(self, task_id: str) -> bool:
        """移除秒杀任务，并释放关联的浏览器资源"""
        try:
            from .browser_manager import browser_manager
            # 先停止任务
            self.stop_task(task_id)

            # 释放浏览器资源
            browser_manager.release_browser(task_id)
            
            # 移除任务
            if task_id in self.tasks:
                task_name = self.tasks[task_id].name
                del self.tasks[task_id]
                self.logger.info(f"任务 '{task_name}' 已从调度器移除。")
            if task_id in self.task_callbacks:
                del self.task_callbacks[task_id]
                
            return True
        except Exception as e:
            self.logger.error(f"移除任务失败: {str(e)}")
            return False
            
    def start_task(self, task_id: str) -> bool:
        """启动指定任务"""
        if task_id not in self.tasks:
            self.logger.error(f"任务不存在: {task_id}")
            return False
            
        if task_id in self.running_tasks:
            self.logger.warning(f"任务已在运行: {task_id}")
            return True
            
        try:
            task = self.tasks[task_id]
            task.is_running = True # 立即更新任务自身状态
            task_thread = threading.Thread(
                target=self._execute_task,
                args=(task_id,),
                daemon=True
            )
            self.running_tasks[task_id] = task_thread
            task_thread.start()
            
            self.logger.info(f"启动任务成功: {task.name} (ID: {task_id})")
            return True
        except Exception as e:
            self.logger.error(f"启动任务失败: {str(e)}")
            return False
            
    def stop_task(self, task_id: str) -> bool:
        """停止指定任务"""
        if task_id not in self.running_tasks:
            return True
            
        try:
            task = self.tasks.get(task_id)
            if task:
                task.stop()
                
            # 等待线程结束
            thread = self.running_tasks[task_id]
            thread.join(timeout=5)
            
            del self.running_tasks[task_id]
            self.logger.info(f"停止任务成功: {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"停止任务失败: {str(e)}")
            return False
            
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
            
        task = self.tasks[task_id]
        is_running = task_id in self.running_tasks
        
        return {
            'task_id': task_id,
            'name': task.name,
            'status': 'running' if is_running else 'stopped',
            'execution_time': task.execution_time.isoformat(),
            'next_execution': task.get_next_execution().isoformat() if task.get_next_execution() else None,
            'attempts': task.attempts,
            'max_attempts': task.max_attempts,
            'success_count': task.success_count,
            'created_at': task.created_at.isoformat()
        }
        
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
        
    def add_callback(self, task_id: str, callback: Callable):
        """添加任务回调函数"""
        if task_id not in self.task_callbacks:
            self.task_callbacks[task_id] = []
        self.task_callbacks[task_id].append(callback)
        
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 创建任务列表的副本以安全迭代
                tasks_copy = list(self.tasks.items())

                # 检查需要预热的任务
                for task_id, task in tasks_copy:
                    if task.should_preload(current_time) and task_id not in self.preloading_tasks:
                        self.preloading_tasks.add(task_id)
                        preload_thread = threading.Thread(
                            target=self._preload_task_browser, 
                            args=(task_id,), 
                            daemon=True
                        )
                        preload_thread.start()

                # 检查需要执行的任务
                for task_id, task in tasks_copy:
                    if task_id in self.running_tasks:
                        continue
                        
                    # 检查是否到达执行时间
                    if task.should_execute(current_time):
                        self.start_task(task_id)
                        
                # 检查提醒时间
                for task_id, task in tasks_copy:
                    if task.should_remind(current_time):
                        self._send_reminder(task_id)
                        
                time.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                self.logger.error(f"调度器循环错误: {str(e)}")
                time.sleep(5)
                
    def _preload_task_browser(self, task_id: str):
        """执行浏览器预热"""
        task = self.tasks.get(task_id)
        if not task:
            self.preloading_tasks.discard(task_id)
            return

        self.logger.info(f"开始为任务预热浏览器: {task.name}")
        try:
            from .browser_manager import browser_manager
            # 不需要获取锁，因为load_url内部会处理
            browser = browser_manager.get_browser(task.task_id)
            if browser:
                success, message = browser_manager.load_url(task.task_id, task.url, force_reload=False)
                if success:
                    task.is_preloaded = True
                    self.logger.info(f"任务浏览器预热成功: {task.name}")
                else:
                    self.logger.error(f"任务浏览器预热失败: {task.name} - {message}")
            else:
                self.logger.error(f"预热失败：无法获取浏览器实例 for task {task.name}")
        except Exception as e:
            self.logger.error(f"任务浏览器预热异常: {task.name} - {str(e)}")
        finally:
            self.preloading_tasks.discard(task_id)

    def _execute_task(self, task_id: str):
        """执行任务"""
        task = self.tasks[task_id]
        
        task_execution_thread = threading.Thread(target=self._execute_and_cleanup, args=(task,), daemon=True)
        task_execution_thread.start()

    def _execute_and_cleanup(self, task):
        """在一个独立的线程中执行任务并确保清理"""
        try:
            self.logger.info(f"开始执行任务: {task.name} (ID: {task.task_id})")
            
            # 执行任务
            success = task.execute()
            
            if success:
                self.logger.info(f"任务执行成功: {task.name}")
            else:
                self.logger.warning(f"任务执行失败: {task.name}")
            
            # 触发回调
            if task.task_id in self.task_callbacks:
                for callback in self.task_callbacks[task.task_id]:
                    try:
                        callback(task.task_id, success)
                    except Exception as e:
                        self.logger.error(f"回调函数执行失败: {str(e)}")
                        
            self.logger.info(f"任务执行完成: {task.name}, 结果: {'成功' if success else '失败'}")
            
        except Exception as e:
            self.logger.error(f"任务执行异常: {task.name} - {str(e)}")
            import traceback
            self.logger.error(f"异常堆栈: {traceback.format_exc()}")
        finally:
            task.is_running = False # 确保任务状态被重置
            # 从运行列表中移除
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            self.logger.debug(f"Task {task.task_id} removed from running tasks.")

    def _send_reminder(self, task_id: str):
        """发送提醒"""
        task = self.tasks[task_id]
        self.logger.info(f"发送提醒: {task.name} 将在2分钟后开始执行")
        
        # 这里可以集成通知系统
        # 暂时只记录日志

# 全局调度器实例
scheduler = SeckillScheduler() 