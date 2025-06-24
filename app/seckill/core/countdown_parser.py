"""
倒计时解析器
支持多种倒计时格式的智能识别和解析
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from enum import Enum

class CountdownFormat(Enum):
    """倒计时格式枚举"""
    TIME_FORMAT = "time_format"      # 时间格式: 23:59:59, 00:00:00
    TEXT_FORMAT = "text_format"      # 文本格式: 剩余时间10分钟, 还有1小时
    NUMBER_FORMAT = "number_format"  # 数字格式: 600, 3600 (秒数)
    MIXED_FORMAT = "mixed_format"    # 混合格式: 1天2小时30分钟

class CountdownParser:
    """倒计时解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 时间格式正则表达式
        self.time_patterns = [
            r'(\d{1,2}):(\d{1,2}):(\d{1,2})',  # 23:59:59
            r'(\d{1,2}):(\d{1,2})',            # 59:59
            r'(\d{1,2})时(\d{1,2})分(\d{1,2})秒',  # 中文时间格式
            r'(\d{1,2})h(\d{1,2})m(\d{1,2})s',     # 英文时间格式
        ]
        
        # 文本格式正则表达式
        self.text_patterns = [
            r'剩余时间[：:]\s*(\d+)\s*分钟',
            r'还有\s*(\d+)\s*分钟',
            r'(\d+)\s*分钟[后后]',
            r'剩余\s*(\d+)\s*分钟',
            r'(\d+)\s*min',
            r'(\d+)\s*分钟',
        ]
        
        # 混合格式正则表达式
        self.mixed_patterns = [
            r'(\d+)\s*天\s*(\d+)\s*小时\s*(\d+)\s*分钟',
            r'(\d+)\s*天\s*(\d+)\s*时\s*(\d+)\s*分',
            r'(\d+)\s*d\s*(\d+)\s*h\s*(\d+)\s*m',
            r'(\d+)\s*小时\s*(\d+)\s*分钟',
            r'(\d+)\s*时\s*(\d+)\s*分',
        ]
        
    def parse_countdown(self, text: str) -> Tuple[bool, Optional[int], str]:
        """
        解析倒计时文本
        
        Args:
            text: 倒计时文本
            
        Returns:
            (是否解析成功, 剩余秒数, 解析结果描述)
        """
        if not text or not text.strip():
            return False, None, "倒计时文本为空"
            
        text = text.strip()
        self.logger.debug(f"解析倒计时文本: {text}")
        
        # 1. 尝试时间格式解析
        result = self._parse_time_format(text)
        if result[0]:
            return result
            
        # 2. 尝试数字格式解析
        result = self._parse_number_format(text)
        if result[0]:
            return result
            
        # 3. 尝试文本格式解析
        result = self._parse_text_format(text)
        if result[0]:
            return result
            
        # 4. 尝试混合格式解析
        result = self._parse_mixed_format(text)
        if result[0]:
            return result
            
        return False, None, f"无法解析倒计时格式: {text}"
        
    def _parse_time_format(self, text: str) -> Tuple[bool, Optional[int], str]:
        """解析时间格式"""
        for pattern in self.time_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:  # HH:MM:SS
                        hours, minutes, seconds = map(int, groups)
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                    elif len(groups) == 2:  # MM:SS
                        minutes, seconds = map(int, groups)
                        total_seconds = minutes * 60 + seconds
                    else:
                        continue
                        
                    return True, total_seconds, f"时间格式解析成功: {text} -> {total_seconds}秒"
                except ValueError:
                    continue
                    
        return False, None, "时间格式解析失败"
        
    def _parse_number_format(self, text: str) -> Tuple[bool, Optional[int], str]:
        """解析数字格式"""
        # 提取纯数字
        numbers = re.findall(r'\d+', text)
        if numbers:
            try:
                # 取第一个数字作为秒数
                seconds = int(numbers[0])
                return True, seconds, f"数字格式解析成功: {text} -> {seconds}秒"
            except ValueError:
                pass
                
        return False, None, "数字格式解析失败"
        
    def _parse_text_format(self, text: str) -> Tuple[bool, Optional[int], str]:
        """解析文本格式"""
        for pattern in self.text_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    minutes = int(match.group(1))
                    seconds = minutes * 60
                    return True, seconds, f"文本格式解析成功: {text} -> {seconds}秒"
                except ValueError:
                    continue
                    
        return False, None, "文本格式解析失败"
        
    def _parse_mixed_format(self, text: str) -> Tuple[bool, Optional[int], str]:
        """解析混合格式"""
        for pattern in self.mixed_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:  # 天:时:分
                        days, hours, minutes = map(int, groups)
                        total_seconds = days * 86400 + hours * 3600 + minutes * 60
                    elif len(groups) == 2:  # 时:分
                        hours, minutes = map(int, groups)
                        total_seconds = hours * 3600 + minutes * 60
                    else:
                        continue
                        
                    return True, total_seconds, f"混合格式解析成功: {text} -> {total_seconds}秒"
                except ValueError:
                    continue
                    
        return False, None, "混合格式解析失败"
        
    def is_countdown_ready(self, text: str, threshold: int = 0, end_flags: list = None) -> Tuple[bool, str]:
        """
        检查倒计时是否准备就绪
        
        Args:
            text: 倒计时文本
            threshold: 阈值（秒），小于等于此值认为准备就绪
            end_flags: 自定义结束标志列表
            
        Returns:
            (是否准备就绪, 描述信息)
        """
        if end_flags:
            for flag in end_flags:
                if text.strip() == flag.strip():
                    return True, f"倒计时结束标志命中: {flag}"
        success, seconds, description = self.parse_countdown(text)
        
        if not success:
            return False, f"倒计时解析失败: {description}"
            
        if seconds is None:
            return False, "倒计时秒数为空"
            
        if seconds <= threshold:
            return True, f"倒计时准备就绪: {text} ({seconds}秒 <= {threshold}秒)"
        else:
            return False, f"倒计时未就绪: {text} ({seconds}秒 > {threshold}秒)"
            
    def get_countdown_info(self, text: str) -> Dict[str, Any]:
        """
        获取倒计时详细信息
        
        Args:
            text: 倒计时文本
            
        Returns:
            倒计时信息字典
        """
        success, seconds, description = self.parse_countdown(text)
        
        info = {
            'original_text': text,
            'parse_success': success,
            'description': description,
            'total_seconds': seconds,
        }
        
        if success and seconds is not None:
            # 计算详细时间
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = (seconds % 3600) // 60
            remaining_seconds = seconds % 60
            
            info.update({
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'seconds': remaining_seconds,
                'formatted_time': f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}",
                'is_ready': seconds <= 0
            })
            
        return info

# 全局实例
countdown_parser = CountdownParser() 