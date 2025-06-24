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
                try:
                    # 使用新的API等待页面加载
                    self.page.wait.doc_loaded()
                    
                    # 额外等待以确保JavaScript加载
                    time.sleep(2)
                    
                    # 验证页面是否真正加载完成
                    ready_state = self.page.run_js('return document.readyState')
                    if ready_state != 'complete':
                        raise Exception("Page not fully loaded")
                    
                    # 验证页面是否有效
                    body_check = self.page.run_js('return document.body !== null')
                    if not body_check:
                        raise Exception("Invalid page body")
                    
                    return True, "URL loaded successfully"
                    
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        current_app.logger.warning(f"Page load check failed (attempt {attempt + 1}): {str(e)}")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return False, f"Page load check failed: {str(e)}"
                        
            except Exception as e:
                current_app.logger.error(f"Failed to load URL (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self.initialize()  # 重新初始化浏览器
                else:
                    return False, str(e)

    def scrape_content(self, selector_type, selector_value, attribute=None):
        """抓取内容
        
        Returns:
            tuple: (success, message, results)
            - success: bool, 是否成功
            - message: str, 操作信息
            - results: list of dict, 每个字典包含：
                - content: 元素内容
                - type: 元素类型
                - tag: 元素标签名
                - attributes: 元素属性
        """
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

                # 获取元素内容和类型
                results = []
                for element in elements:
                    # 获取元素标签名
                    tag_name = element.tag

                    # 获取元素类型
                    element_type = self._get_element_type(element)
                    
                    # 获取元素内容
                    if attribute:
                        content = element.attr(attribute)
                    else:
                        content = element.text

                    # 获取重要属性
                    attrs = {
                        'id': element.attr('id'),
                        'class': element.attr('class'),
                        'name': element.attr('name'),
                        'value': element.attr('value'),
                        'href': element.attr('href') if tag_name == 'a' else None,
                        'src': element.attr('src') if tag_name in ['img', 'iframe', 'video'] else None,
                        'type': element.attr('type') if tag_name in ['input', 'button'] else None,
                        'placeholder': element.attr('placeholder') if tag_name in ['input', 'textarea'] else None
                    }
                    # 移除None值的属性
                    attrs = {k: v for k, v in attrs.items() if v is not None}

                    result = {
                        'content': content,
                        'type': element_type,
                        'tag': tag_name,
                        'attributes': attrs
                    }
                    results.append(result)

                return True, "Content scraped successfully", results
            except Exception as e:
                current_app.logger.error(f"Failed to scrape content (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self._ensure_connection()
                else:
                    return False, str(e), None

    def _get_element_type(self, element):
        """识别元素类型
        
        Args:
            element: DrissionPage元素对象
            
        Returns:
            str: 元素类型描述
        """
        tag_name = element.tag
        element_type = element.attr('type')
        
        # 输入框类型
        if tag_name == 'input':
            if not element_type:
                return '文本输入框'
            input_types = {
                'text': '文本输入框',
                'password': '密码输入框',
                'checkbox': '复选框',
                'radio': '单选框',
                'submit': '提交按钮',
                'button': '按钮',
                'file': '文件上传框',
                'hidden': '隐藏输入框',
                'number': '数字输入框',
                'email': '邮箱输入框',
                'tel': '电话输入框',
                'date': '日期选择框',
                'time': '时间选择框',
                'datetime-local': '日期时间选择框',
                'search': '搜索框'
            }
            return input_types.get(element_type, f'输入框({element_type})')
            
        # 其他元素类型
        element_types = {
            'button': '按钮',
            'a': '链接',
            'select': '下拉选择框',
            'textarea': '多行文本框',
            'img': '图片',
            'video': '视频',
            'audio': '音频',
            'iframe': '嵌入框架',
            'form': '表单',
            'table': '表格',
            'ul': '无序列表',
            'ol': '有序列表',
            'li': '列表项',
            'div': '区块',
            'span': '行内元素',
            'p': '段落',
            'h1': '一级标题',
            'h2': '二级标题',
            'h3': '三级标题',
            'h4': '四级标题',
            'h5': '五级标题',
            'h6': '六级标题',
            'label': '标签',
            'nav': '导航',
            'header': '页眉',
            'footer': '页脚',
            'main': '主要内容',
            'aside': '侧边栏',
            'article': '文章',
            'section': '区段'
        }
        
        return element_types.get(tag_name, tag_name)

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