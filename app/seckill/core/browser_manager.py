"""
浏览器管理器
负责管理浏览器实例和页面操作，支持多任务并行执行
优化版本：支持页面状态缓存和智能复用
"""

import threading
import time
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import logging
from DrissionPage import ChromiumPage
from selenium.common.exceptions import WebDriverException

class PageState:
    """页面状态类"""
    def __init__(self, url: str):
        self.url = url
        self.last_loaded = None
        self.is_loaded = False
        self.load_count = 0
        self.last_activity = datetime.now()
        
    def update_activity(self):
        """更新活动时间"""
        self.last_activity = datetime.now()
        
    def mark_loaded(self):
        """标记页面已加载"""
        self.is_loaded = True
        self.last_loaded = datetime.now()
        self.load_count += 1
        self.update_activity()

class BrowserManager:
    """浏览器管理器（优化版）"""
    
    def __init__(self):
        self.browsers: Dict[str, ChromiumPage] = {}
        self.browser_locks: Dict[str, threading.Lock] = {}
        self.page_states: Dict[str, PageState] = {}  # 页面状态缓存
        self.max_browsers = 5  # 最大浏览器实例数
        self.page_cache_timeout = 300  # 页面缓存超时时间（秒）
        self.logger = logging.getLogger(__name__)
        
    def get_browser(self, task_id: str) -> Optional[ChromiumPage]:
        """获取浏览器实例"""
        if task_id in self.browsers:
            return self.browsers[task_id]
            
        # 创建新的浏览器实例
        if len(self.browsers) >= self.max_browsers:
            self.logger.warning("达到最大浏览器实例数限制")
            return None
            
        try:
            browser = ChromiumPage()
            browser.set.timeouts(30)  # 30秒超时
            
            self.browsers[task_id] = browser
            self.browser_locks[task_id] = threading.Lock()
            
            self.logger.info(f"创建浏览器实例: {task_id}")
            return browser
        except Exception as e:
            self.logger.error(f"创建浏览器实例失败: {str(e)}")
            return None
            
    def release_browser(self, task_id: str):
        """释放浏览器实例"""
        if task_id in self.browsers:
            try:
                browser = self.browsers[task_id]
                browser.quit()
                del self.browsers[task_id]
                del self.browser_locks[task_id]
                
                # 清理页面状态缓存
                if task_id in self.page_states:
                    del self.page_states[task_id]
                    
                self.logger.info(f"释放浏览器实例: {task_id}")
            except Exception as e:
                self.logger.error(f"释放浏览器实例失败: {str(e)}")
                
    def load_url(self, task_id: str, url: str, force_reload: bool = False) -> Tuple[bool, str]:
        """
        智能加载URL
        
        Args:
            task_id: 任务ID
            url: 目标URL
            force_reload: 是否强制重新加载
            
        Returns:
            (是否成功, 消息)
        """
        browser = self.get_browser(task_id)
        if not browser:
            return False, "无法获取浏览器实例"
            
        lock = self.browser_locks[task_id]
        
        with lock:
            try:
                # 检查页面状态缓存
                page_state = self.page_states.get(task_id)
                current_url = browser.url if hasattr(browser, 'url') else None
                
                # 判断是否需要重新加载
                need_reload = force_reload
                
                if not need_reload and page_state:
                    # 检查URL是否相同
                    if current_url == url and page_state.is_loaded:
                        # 检查缓存是否过期
                        if (datetime.now() - page_state.last_activity).seconds < self.page_cache_timeout:
                            self.logger.info(f"使用页面缓存: {task_id} -> {url}")
                            page_state.update_activity()
                            return True, "使用页面缓存"
                        else:
                            self.logger.info(f"页面缓存已过期: {task_id}")
                            need_reload = True
                    else:
                        need_reload = True
                else:
                    need_reload = True
                
                if need_reload:
                    self.logger.info(f"加载页面: {task_id} -> {url}")
                    
                    # 加载URL
                    browser.get(url)
                    
                    # 等待页面加载完成
                    browser.wait.doc_loaded()
                    time.sleep(2)  # 额外等待JavaScript加载
                    
                    # 验证页面是否真正加载完成
                    ready_state = browser.run_js('return document.readyState')
                    if ready_state != 'complete':
                        return False, "页面加载不完整"
                        
                    # 验证页面是否有效
                    body_check = browser.run_js('return document.body !== null')
                    if not body_check:
                        return False, "页面无效"
                    
                    # 更新页面状态缓存
                    self.page_states[task_id] = PageState(url)
                    self.page_states[task_id].mark_loaded()
                    
                    self.logger.info(f"页面加载成功: {url}")
                    
                return True, "URL加载成功"
                
            except Exception as e:
                self.logger.error(f"加载URL失败: {str(e)}")
                return False, str(e)
                
    def check_page_state(self, task_id: str, url: str) -> Tuple[bool, str]:
        """
        检查页面状态，不重新加载
        
        Args:
            task_id: 任务ID
            url: 目标URL
            
        Returns:
            (页面是否可用, 状态描述)
        """
        browser = self.get_browser(task_id)
        if not browser:
            return False, "无法获取浏览器实例"
            
        try:
            current_url = browser.url if hasattr(browser, 'url') else None
            
            if current_url != url:
                return False, f"页面URL不匹配: 期望 {url}, 实际 {current_url}"
                
            # 检查页面是否仍然有效
            ready_state = browser.run_js('return document.readyState')
            if ready_state != 'complete':
                return False, "页面状态异常"
                
            body_check = browser.run_js('return document.body !== null')
            if not body_check:
                return False, "页面无效"
                
            return True, "页面状态正常"
            
        except Exception as e:
            self.logger.error(f"检查页面状态失败: {str(e)}")
            return False, str(e)
            
    def find_element(self, task_id: str, selector_type: str, selector_value: str) -> Tuple[bool, str, List]:
        """查找元素"""
        browser = self.get_browser(task_id)
        if not browser:
            return False, "无法获取浏览器实例", []
            
        lock = self.browser_locks[task_id]
        
        with lock:
            try:
                # 根据选择器类型查找元素
                if selector_type == 'css':
                    elements = browser.eles(f'css:{selector_value}')
                elif selector_type == 'xpath':
                    elements = browser.eles(f'xpath:{selector_value}')
                elif selector_type == 'text':
                    elements = browser.eles(f'text:{selector_value}')
                elif selector_type == 'tag':
                    elements = browser.eles(f'tag:{selector_value}')
                else:
                    return False, "无效的选择器类型", []
                    
                if not elements:
                    return False, "未找到匹配的元素", []
                    
                # 获取元素信息
                results = []
                for element in elements:
                    element_info = {
                        'tag': element.tag,
                        'text': element.text,
                        'attributes': {
                            'id': element.attr('id'),
                            'class': element.attr('class'),
                            'name': element.attr('name'),
                            'value': element.attr('value'),
                            'href': element.attr('href'),
                            'src': element.attr('src'),
                            'type': element.attr('type')
                        }
                    }
                    # 移除None值的属性
                    element_info['attributes'] = {k: v for k, v in element_info['attributes'].items() if v is not None}
                    results.append(element_info)
                    
                return True, f"找到 {len(elements)} 个元素", results
                
            except Exception as e:
                self.logger.error(f"查找元素失败: {str(e)}")
                return False, str(e), []
                
    def click_element(self, task_id: str, selector_type: str, selector_value: str, 
                     click_count: int = 1, interval: float = 0.1) -> Tuple[bool, str]:
        """
        点击元素（支持连续点击）
        
        Args:
            task_id: 任务ID
            selector_type: 选择器类型
            selector_value: 选择器值
            click_count: 点击次数
            interval: 点击间隔（秒）
            
        Returns:
            (是否成功, 消息)
        """
        browser = self.get_browser(task_id)
        if not browser:
            return False, "无法获取浏览器实例"
            
        lock = self.browser_locks[task_id]
        
        with lock:
            try:
                # 查找元素
                if selector_type == 'css':
                    element = browser.ele(f'css:{selector_value}')
                elif selector_type == 'xpath':
                    element = browser.ele(f'xpath:{selector_value}')
                elif selector_type == 'text':
                    element = browser.ele(f'text:{selector_value}')
                elif selector_type == 'tag':
                    element = browser.ele(f'tag:{selector_value}')
                else:
                    return False, "无效的选择器类型"
                    
                if not element:
                    return False, "未找到目标元素"
                    
                # 执行点击
                success_count = 0
                for i in range(click_count):
                    try:
                        element.click()
                        success_count += 1
                        
                        if i < click_count - 1:  # 不是最后一次点击
                            time.sleep(interval)
                            
                    except Exception as e:
                        self.logger.warning(f"第{i+1}次点击失败: {str(e)}")
                        break
                        
                if success_count == click_count:
                    return True, f"连续点击成功: {click_count}次"
                elif success_count > 0:
                    return True, f"部分点击成功: {success_count}/{click_count}次"
                else:
                    return False, "所有点击都失败"
                    
            except Exception as e:
                self.logger.error(f"点击元素失败: {str(e)}")
                return False, str(e)
                
    def input_text(self, task_id: str, selector_type: str, selector_value: str, text: str) -> Tuple[bool, str]:
        """输入文本"""
        browser = self.get_browser(task_id)
        if not browser:
            return False, "无法获取浏览器实例"
            
        lock = self.browser_locks[task_id]
        
        with lock:
            try:
                # 查找元素
                if selector_type == 'css':
                    element = browser.ele(f'css:{selector_value}')
                elif selector_type == 'xpath':
                    element = browser.ele(f'xpath:{selector_value}')
                elif selector_type == 'text':
                    element = browser.ele(f'text:{selector_value}')
                elif selector_type == 'tag':
                    element = browser.ele(f'tag:{selector_value}')
                else:
                    return False, "无效的选择器类型"
                    
                if not element:
                    return False, "未找到目标元素"
                    
                # 清空并输入文本
                element.clear()
                element.input(text)
                time.sleep(0.5)  # 等待输入响应
                
                return True, "文本输入成功"
                
            except Exception as e:
                self.logger.error(f"输入文本失败: {str(e)}")
                return False, str(e)
                
    def get_page_info(self, task_id: str) -> Tuple[bool, str, dict]:
        """获取页面信息"""
        browser = self.get_browser(task_id)
        if not browser:
            return False, "无法获取浏览器实例", {}
            
        lock = self.browser_locks[task_id]
        
        with lock:
            try:
                page_info = {
                    'url': browser.url,
                    'title': browser.title,
                    'ready_state': browser.run_js('return document.readyState'),
                    'body_exists': browser.run_js('return document.body !== null'),
                    'timestamp': datetime.now().isoformat()
                }
                
                # 获取页面状态缓存信息
                if task_id in self.page_states:
                    state = self.page_states[task_id]
                    page_info.update({
                        'cached': True,
                        'last_loaded': state.last_loaded.isoformat() if state.last_loaded else None,
                        'load_count': state.load_count,
                        'last_activity': state.last_activity.isoformat()
                    })
                else:
                    page_info['cached'] = False
                    
                return True, "获取页面信息成功", page_info
                
            except Exception as e:
                self.logger.error(f"获取页面信息失败: {str(e)}")
                return False, str(e), {}
                
    def execute_script(self, task_id: str, script: str) -> Tuple[bool, str, any]:
        """执行JavaScript脚本"""
        browser = self.get_browser(task_id)
        if not browser:
            return False, "无法获取浏览器实例", None
            
        lock = self.browser_locks[task_id]
        
        with lock:
            try:
                result = browser.run_js(script)
                return True, "脚本执行成功", result
            except Exception as e:
                self.logger.error(f"执行脚本失败: {str(e)}")
                return False, str(e), None
                
    def wait_for_element(self, task_id: str, selector_type: str, selector_value: str, 
                        timeout: int = 10) -> Tuple[bool, str]:
        """等待元素出现"""
        browser = self.get_browser(task_id)
        if not browser:
            return False, "无法获取浏览器实例"
            
        lock = self.browser_locks[task_id]
        
        with lock:
            try:
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    # 查找元素
                    if selector_type == 'css':
                        element = browser.ele(f'css:{selector_value}')
                    elif selector_type == 'xpath':
                        element = browser.ele(f'xpath:{selector_value}')
                    elif selector_type == 'text':
                        element = browser.ele(f'text:{selector_value}')
                    elif selector_type == 'tag':
                        element = browser.ele(f'tag:{selector_value}')
                    else:
                        return False, "无效的选择器类型"
                        
                    if element:
                        return True, "元素已出现"
                        
                    time.sleep(0.5)  # 等待500ms后重试
                    
                return False, f"等待元素超时: {timeout}秒"
                
            except Exception as e:
                self.logger.error(f"等待元素失败: {str(e)}")
                return False, str(e)
                
    def close_all(self):
        """关闭所有浏览器实例"""
        for task_id in list(self.browsers.keys()):
            self.release_browser(task_id)
            
    def get_status(self) -> dict:
        """获取管理器状态"""
        return {
            'active_browsers': len(self.browsers),
            'max_browsers': self.max_browsers,
            'cached_pages': len(self.page_states),
            'browser_ids': list(self.browsers.keys()),
            'page_cache_timeout': self.page_cache_timeout
        }

# 全局实例
browser_manager = BrowserManager() 