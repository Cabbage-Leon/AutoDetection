"""
元素选择器模块
支持可视化选择DOM元素，自动生成多种选择器
"""

import re
from typing import List, Dict, Optional, Tuple
import logging

class ElementSelector:
    """元素选择器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def generate_selectors(self, element_info: Dict) -> Dict[str, str]:
        """为元素生成多种选择器
        
        Args:
            element_info: 元素信息字典，包含tag、attributes等
            
        Returns:
            Dict[str, str]: 各种选择器的字典
        """
        selectors = {}
        
        try:
            tag = element_info.get('tag', '')
            attributes = element_info.get('attributes', {})
            
            # 1. ID选择器（最高优先级）
            if 'id' in attributes and attributes['id']:
                selectors['id'] = f"#{attributes['id']}"
                
            # 2. 类选择器
            if 'class' in attributes and attributes['class']:
                classes = attributes['class'].split()
                if classes:
                    # 使用第一个类名
                    selectors['class'] = f".{classes[0]}"
                    # 如果有多个类名，生成组合选择器
                    if len(classes) > 1:
                        selectors['multi_class'] = f".{'.'.join(classes)}"
                        
            # 3. 属性选择器
            for attr_name, attr_value in attributes.items():
                if attr_value and attr_name not in ['id', 'class']:
                    selectors[f'attr_{attr_name}'] = f"[{attr_name}='{attr_value}']"
                    
            # 4. 标签+属性组合选择器
            if tag:
                selectors['tag'] = tag
                if 'id' in attributes and attributes['id']:
                    selectors['tag_id'] = f"{tag}#{attributes['id']}"
                if 'class' in attributes and attributes['class']:
                    classes = attributes['class'].split()
                    selectors['tag_class'] = f"{tag}.{classes[0]}"
                    
            # 5. 文本内容选择器（如果有文本）
            text = element_info.get('text', '').strip()
            if text and len(text) < 100:  # 限制文本长度
                # 转义特殊字符
                escaped_text = re.escape(text)
                selectors['text'] = f"text={escaped_text}"
                
            # 6. 位置选择器（基于父元素）
            if 'parent_info' in element_info:
                parent_info = element_info['parent_info']
                if parent_info.get('tag'):
                    selectors['parent'] = f"{parent_info['tag']} > {tag}"
                    
        except Exception as e:
            self.logger.error(f"生成选择器失败: {str(e)}")
            
        return selectors
        
    def validate_selector(self, selector_type: str, selector_value: str) -> Tuple[bool, str]:
        """验证选择器是否有效
        
        Args:
            selector_type: 选择器类型 (css, xpath, text, tag)
            selector_value: 选择器值
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            if selector_type == 'css':
                return self._validate_css_selector(selector_value)
            elif selector_type == 'xpath':
                return self._validate_xpath_selector(selector_value)
            elif selector_type == 'text':
                return self._validate_text_selector(selector_value)
            elif selector_type == 'tag':
                return self._validate_tag_selector(selector_value)
            else:
                return False, "不支持的选择器类型"
                
        except Exception as e:
            return False, f"验证选择器异常: {str(e)}"
            
    def _validate_css_selector(self, selector: str) -> Tuple[bool, str]:
        """验证CSS选择器"""
        if not selector:
            return False, "CSS选择器不能为空"
            
        # 基本CSS选择器验证
        css_patterns = [
            r'^[.#]?[a-zA-Z][a-zA-Z0-9_-]*$',  # 类名或ID
            r'^[a-zA-Z][a-zA-Z0-9_-]*$',  # 标签名
            r'^\[[a-zA-Z][a-zA-Z0-9_-]*(?:[~|^$*]?=.*?)?\]$',  # 属性选择器
            r'^[a-zA-Z][a-zA-Z0-9_-]*[.#][a-zA-Z][a-zA-Z0-9_-]*$',  # 标签+类/ID
            r'^[.#][a-zA-Z][a-zA-Z0-9_-]*[.#][a-zA-Z][a-zA-Z0-9_-]*$',  # 多类选择器
        ]
        
        for pattern in css_patterns:
            if re.match(pattern, selector):
                return True, "CSS选择器有效"
                
        return False, "CSS选择器格式无效"
        
    def _validate_xpath_selector(self, selector: str) -> Tuple[bool, str]:
        """验证XPath选择器"""
        if not selector:
            return False, "XPath选择器不能为空"
            
        # 基本XPath选择器验证
        xpath_patterns = [
            r'^//[a-zA-Z][a-zA-Z0-9_-]*$',  # 简单路径
            r'^//[a-zA-Z][a-zA-Z0-9_-]*\[.*?\]$',  # 带条件的路径
            r'^//[a-zA-Z][a-zA-Z0-9_-]*\[@[a-zA-Z][a-zA-Z0-9_-]*.*?\]$',  # 带属性的路径
            r'^//[a-zA-Z][a-zA-Z0-9_-]*\[contains\(.*?\)\]$',  # 包含函数
            r'^//[a-zA-Z][a-zA-Z0-9_-]*\[text\(\)=.*?\]$',  # 文本匹配
        ]
        
        for pattern in xpath_patterns:
            if re.match(pattern, selector):
                return True, "XPath选择器有效"
                
        return False, "XPath选择器格式无效"
        
    def _validate_text_selector(self, selector: str) -> Tuple[bool, str]:
        """验证文本选择器"""
        if not selector:
            return False, "文本选择器不能为空"
            
        if len(selector) > 200:
            return False, "文本选择器过长"
            
        return True, "文本选择器有效"
        
    def _validate_tag_selector(self, selector: str) -> Tuple[bool, str]:
        """验证标签选择器"""
        if not selector:
            return False, "标签选择器不能为空"
            
        # 验证是否为有效的HTML标签名
        valid_tags = [
            'div', 'span', 'p', 'a', 'button', 'input', 'form', 'table', 'tr', 'td',
            'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img', 'video',
            'audio', 'iframe', 'textarea', 'select', 'option', 'label', 'fieldset',
            'legend', 'nav', 'header', 'footer', 'main', 'section', 'article',
            'aside', 'details', 'summary', 'dialog', 'menu', 'menuitem'
        ]
        
        if selector.lower() in valid_tags:
            return True, "标签选择器有效"
        else:
            return False, "无效的HTML标签名"
            
    def get_selector_priority(self, selector_type: str, selector_value: str) -> int:
        """获取选择器优先级
        
        Args:
            selector_type: 选择器类型
            selector_value: 选择器值
            
        Returns:
            int: 优先级分数（越高越优先）
        """
        priority = 0
        
        if selector_type == 'css':
            if selector_value.startswith('#'):
                priority = 100  # ID选择器最高优先级
            elif selector_value.startswith('.'):
                priority = 80   # 类选择器
            elif '[' in selector_value:
                priority = 60   # 属性选择器
            else:
                priority = 40   # 标签选择器
        elif selector_type == 'xpath':
            if 'contains(' in selector_value:
                priority = 70   # 包含函数
            elif '@' in selector_value:
                priority = 65   # 属性选择
            else:
                priority = 50   # 简单路径
        elif selector_type == 'text':
            priority = 30       # 文本选择器
        elif selector_type == 'tag':
            priority = 20       # 标签选择器
            
        return priority
        
    def optimize_selectors(self, selectors: Dict[str, str]) -> List[Tuple[str, str, int]]:
        """优化选择器列表，按优先级排序
        
        Args:
            selectors: 选择器字典
            
        Returns:
            List[Tuple[str, str, int]]: 排序后的选择器列表 (类型, 值, 优先级)
        """
        optimized = []
        
        for selector_type, selector_value in selectors.items():
            # 映射选择器类型
            if selector_type.startswith('attr_'):
                actual_type = 'css'
                actual_value = selector_value
            elif selector_type in ['id', 'class', 'multi_class', 'tag_id', 'tag_class', 'parent']:
                actual_type = 'css'
                actual_value = selector_value
            elif selector_type == 'text':
                actual_type = 'text'
                actual_value = selector_value
            elif selector_type == 'tag':
                actual_type = 'tag'
                actual_value = selector_value
            else:
                continue
                
            priority = self.get_selector_priority(actual_type, actual_value)
            optimized.append((actual_type, actual_value, priority))
            
        # 按优先级降序排序
        optimized.sort(key=lambda x: x[2], reverse=True)
        
        return optimized
        
    def create_xpath_from_element(self, element_info: Dict) -> str:
        """根据元素信息创建XPath选择器
        
        Args:
            element_info: 元素信息
            
        Returns:
            str: XPath选择器
        """
        try:
            tag = element_info.get('tag', '')
            attributes = element_info.get('attributes', {})
            
            if not tag:
                return ""
                
            # 构建XPath
            xpath = f"//{tag}"
            
            # 添加属性条件
            conditions = []
            
            if 'id' in attributes and attributes['id']:
                conditions.append(f"@id='{attributes['id']}'")
                
            if 'class' in attributes and attributes['class']:
                conditions.append(f"contains(@class, '{attributes['class']}')")
                
            for attr_name, attr_value in attributes.items():
                if attr_value and attr_name not in ['id', 'class']:
                    conditions.append(f"@{attr_name}='{attr_value}'")
                    
            # 添加文本条件
            text = element_info.get('text', '').strip()
            if text and len(text) < 50:
                conditions.append(f"text()='{text}'")
                
            if conditions:
                xpath += f"[{' and '.join(conditions)}]"
                
            return xpath
            
        except Exception as e:
            self.logger.error(f"创建XPath失败: {str(e)}")
            return ""
            
    def get_element_description(self, element_info: Dict) -> str:
        """获取元素的描述信息
        
        Args:
            element_info: 元素信息
            
        Returns:
            str: 元素描述
        """
        try:
            tag = element_info.get('tag', '')
            attributes = element_info.get('attributes', {})
            text = element_info.get('text', '').strip()
            
            description_parts = []
            
            if tag:
                description_parts.append(f"<{tag}>")
                
            if 'id' in attributes and attributes['id']:
                description_parts.append(f"ID: {attributes['id']}")
                
            if 'class' in attributes and attributes['class']:
                description_parts.append(f"Class: {attributes['class']}")
                
            if text:
                # 截断过长的文本
                display_text = text[:30] + "..." if len(text) > 30 else text
                description_parts.append(f"Text: {display_text}")
                
            if not description_parts:
                description_parts.append("未知元素")
                
            return " | ".join(description_parts)
            
        except Exception as e:
            self.logger.error(f"获取元素描述失败: {str(e)}")
            return "元素描述获取失败"

# 全局元素选择器实例
element_selector = ElementSelector() 