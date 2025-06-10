from DrissionPage import ChromiumPage
from flask import current_app
import time
from selenium.common.exceptions import WebDriverException

class BrowserAutomation:
    def __init__(self):
        self.page = None
        self.is_initialized = False
        self.max_retries = 3
        self.retry_delay = 1  # 重试延迟（秒）

    def initialize(self):
        """初始化浏览器"""
        try:
            # 如果已经初始化，先关闭现有浏览器
            if self.is_initialized and self.page:
                try:
                    self.page.quit()
                except:
                    pass
            
            # 设置浏览器启动参数
            self.page = ChromiumPage()
            # 设置页面加载超时
            self.page.set.timeouts(30)  # 30秒超时
            self.is_initialized = True
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to initialize browser: {str(e)}")
            self.is_initialized = False
            return False

    def _ensure_connection(self):
        """确保浏览器连接正常"""
        if not self.is_initialized:
            return self.initialize()
        
        try:
            # 尝试执行一个简单的操作来检查连接
            self.page.run_js('return document.readyState')
            return True
        except Exception:
            # 如果连接断开，重新初始化
            return self.initialize()

    def load_url(self, url):
        """加载URL"""
        # 每次加载新URL时都重新初始化浏览器
        if not self.initialize():
            return False, "Failed to initialize browser"
        
        for attempt in range(self.max_retries):
            try:
                # 加载URL
                self.page.get(url)
                
                # 等待页面加载完成
                self.page.wait.load_complete()
                
                # 等待页面完全加载（包括JavaScript执行）
                time.sleep(2)  # 给页面一些额外的时间来加载
                
                # 检查页面是否真正加载完成
                ready_state = self.page.run_js('return document.readyState')
                if ready_state != 'complete':
                    raise Exception("Page not fully loaded")
                
                return True, "URL loaded successfully"
            except Exception as e:
                current_app.logger.error(f"Failed to load URL (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self.initialize()  # 重新初始化浏览器
                else:
                    return False, str(e)

    def scrape_content(self, selector_type, selector_value, attribute=None):
        """抓取内容"""
        if not self._ensure_connection():
            return False, "Browser not initialized", None

        for attempt in range(self.max_retries):
            try:
                # 根据选择器类型获取元素
                if selector_type == 'css':
                    elements = self.page.eles(f'css:{selector_value}')
                elif selector_type == 'xpath':
                    elements = self.page.eles(f'xpath:{selector_value}')
                elif selector_type == 'text':
                    elements = self.page.eles(f'text:{selector_value}')
                elif selector_type == 'tag':
                    elements = self.page.eles(f'tag:{selector_value}')
                else:
                    return False, "Invalid selector type", None

                # 获取元素内容
                results = []
                for element in elements:
                    if attribute:
                        value = element.attr(attribute)
                        if value:
                            results.append(value)
                    else:
                        results.append(element.text)

                return True, "Content scraped successfully", results
            except Exception as e:
                current_app.logger.error(f"Failed to scrape content (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self._ensure_connection()
                else:
                    return False, str(e), None

    def execute_action(self, selector_type, selector_value, action, **kwargs):
        """执行元素操作"""
        if not self._ensure_connection():
            return False, "Browser not initialized"

        for attempt in range(self.max_retries):
            try:
                # 根据选择器类型获取元素
                if selector_type == 'css':
                    element = self.page.ele(f'css:{selector_value}')
                elif selector_type == 'xpath':
                    element = self.page.ele(f'xpath:{selector_value}')
                elif selector_type == 'text':
                    element = self.page.ele(f'text:{selector_value}')
                elif selector_type == 'tag':
                    element = self.page.ele(f'tag:{selector_value}')
                else:
                    return False, "Invalid selector type"

                if not element:
                    return False, "Element not found"

                # 执行操作
                if action == 'click':
                    element.click()
                    return True, "Element clicked successfully"
                elif action == 'input':
                    input_text = kwargs.get('input_text')
                    if not input_text:
                        return False, "No input text provided"
                    element.input(input_text)
                    return True, "Text input successfully"
                elif action == 'select':
                    option_value = kwargs.get('option_value')
                    if not option_value:
                        return False, "No option value provided"
                    element.select(option_value)
                    return True, "Option selected successfully"
                elif action == 'hover':
                    element.hover()
                    return True, "Hovered successfully"
                elif action == 'scroll':
                    element.scroll_into_view()
                    return True, "Scrolled into view successfully"
                else:
                    return False, "Invalid action"

            except Exception as e:
                current_app.logger.error(f"Failed to execute action (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self._ensure_connection()
                else:
                    return False, str(e)

    def close(self):
        """关闭浏览器"""
        if self.is_initialized and self.page:
            try:
                self.page.quit()
                self.is_initialized = False
                return True
            except Exception as e:
                current_app.logger.error(f"Failed to close browser: {str(e)}")
                return False
        return True 