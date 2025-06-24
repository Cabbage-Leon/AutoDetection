"""
时间同步模块
确保秒杀时间的精确性，支持北京时间同步和本地时间校准
"""

import time
import socket
import threading
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging
import requests

class TimeSync:
    """时间同步器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.time_offset = 0  # 本地时间与标准时间的偏移量（毫秒）
        self.last_sync_time = None
        self.sync_interval = 300  # 同步间隔（秒）
        self.ntp_servers = [
            'time.windows.com',
            'time.apple.com', 
            'time.google.com',
            'pool.ntp.org'
        ]
        self.is_syncing = False
        
    def sync_time(self) -> bool:
        """同步时间"""
        if self.is_syncing:
            return False
            
        self.is_syncing = True
        
        try:
            # 尝试多种同步方式
            if self._sync_with_ntp():
                self.logger.info("NTP时间同步成功")
                return True
            elif self._sync_with_http():
                self.logger.info("HTTP时间同步成功")
                return True
            else:
                self.logger.warning("时间同步失败，使用本地时间")
                return False
        finally:
            self.is_syncing = False
            
    def _sync_with_ntp(self) -> bool:
        """使用NTP协议同步时间"""
        for server in self.ntp_servers:
            try:
                offset = self._get_ntp_offset(server)
                if offset is not None:
                    self.time_offset = offset
                    self.last_sync_time = datetime.now()
                    return True
            except Exception as e:
                self.logger.debug(f"NTP同步失败 {server}: {str(e)}")
                continue
        return False
        
    def _sync_with_http(self) -> bool:
        """使用HTTP头同步时间"""
        try:
            # 使用多个时间API
            time_apis = [
                'http://worldtimeapi.org/api/timezone/Asia/Shanghai',
                'http://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp',
                'https://beijing-time.org/time.asp'
            ]
            
            for api in time_apis:
                try:
                    response = requests.get(api, timeout=5)
                    if response.status_code == 200:
                        # 解析响应获取时间
                        server_time = self._parse_http_time(response)
                        if server_time:
                            local_time = datetime.now()
                            offset = (server_time - local_time).total_seconds() * 1000
                            self.time_offset = offset
                            self.last_sync_time = local_time
                            return True
                except Exception as e:
                    self.logger.debug(f"HTTP同步失败 {api}: {str(e)}")
                    continue
        except Exception as e:
            self.logger.error(f"HTTP时间同步异常: {str(e)}")
            
        return False
        
    def _get_ntp_offset(self, server: str) -> Optional[float]:
        """获取NTP时间偏移量"""
        try:
            # 简化的NTP客户端实现
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            # NTP请求包
            ntp_request = bytearray(48)
            ntp_request[0] = 0x1B  # NTP v3, client mode
            
            # 发送请求
            sock.sendto(ntp_request, (server, 123))
            
            # 接收响应
            data, addr = sock.recvfrom(1024)
            sock.close()
            
            if len(data) >= 48:
                # 解析NTP响应
                transmit_time = self._ntp_to_timestamp(data[40:48])
                receive_time = self._ntp_to_timestamp(data[32:40])
                
                # 计算往返延迟和偏移
                local_time = time.time()
                delay = (local_time - receive_time) + (transmit_time - local_time)
                offset = ((receive_time - local_time) + (transmit_time - local_time)) / 2
                
                return offset * 1000  # 转换为毫秒
                
        except Exception as e:
            self.logger.debug(f"NTP请求失败 {server}: {str(e)}")
            
        return None
        
    def _ntp_to_timestamp(self, ntp_bytes: bytes) -> float:
        """将NTP时间戳转换为Unix时间戳"""
        if len(ntp_bytes) != 8:
            return 0
            
        # NTP时间戳从1900年开始，需要减去70年的秒数
        ntp_epoch = 2208988800
        
        # 解析整数和小数部分
        integer_part = int.from_bytes(ntp_bytes[:4], byteorder='big')
        fraction_part = int.from_bytes(ntp_bytes[4:], byteorder='big')
        
        # 转换为秒
        timestamp = integer_part - ntp_epoch + fraction_part / 2**32
        return timestamp
        
    def _parse_http_time(self, response) -> Optional[datetime]:
        """解析HTTP响应中的时间"""
        try:
            # 尝试从响应头获取时间
            if 'date' in response.headers:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(response.headers['date'])
                
            # 尝试从响应体解析时间
            content = response.text
            if 'datetime' in content:
                import re
                match = re.search(r'"datetime":"([^"]+)"', content)
                if match:
                    return datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
                    
        except Exception as e:
            self.logger.debug(f"解析HTTP时间失败: {str(e)}")
            
        return None
        
    def get_synced_time(self) -> datetime:
        """获取同步后的时间"""
        if (self.last_sync_time is None or 
            (datetime.now() - self.last_sync_time).total_seconds() > self.sync_interval):
            self.sync_time()
            
        return datetime.now() + timedelta(milliseconds=self.time_offset)
        
    def get_beijing_time(self) -> datetime:
        """获取北京时间"""
        synced_time = self.get_synced_time()
        # 北京时间是UTC+8
        beijing_offset = timedelta(hours=8)
        return synced_time + beijing_offset
        
    def get_time_info(self) -> dict:
        """获取时间信息"""
        local_time = datetime.now()
        synced_time = self.get_synced_time()
        beijing_time = self.get_beijing_time()
        
        return {
            'local_time': local_time.isoformat(),
            'synced_time': synced_time.isoformat(),
            'beijing_time': beijing_time.isoformat(),
            'time_offset_ms': self.time_offset,
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_status': 'synced' if self.last_sync_time else 'not_synced'
        }
        
    def wait_until(self, target_time: datetime, precision_ms: int = 100) -> bool:
        """等待到指定时间"""
        """
        Args:
            target_time: 目标时间
            precision_ms: 精度（毫秒）
            
        Returns:
            bool: 是否成功等待到目标时间
        """
        try:
            while True:
                current_time = self.get_synced_time()
                time_diff = (target_time - current_time).total_seconds() * 1000
                
                if time_diff <= precision_ms:
                    # 到达目标时间
                    return True
                elif time_diff < 0:
                    # 已经过了目标时间
                    self.logger.warning(f"目标时间已过: {target_time}")
                    return False
                else:
                    # 等待
                    sleep_time = min(time_diff / 1000, 1.0)  # 最多等待1秒
                    time.sleep(sleep_time)
                    
        except Exception as e:
            self.logger.error(f"等待时间异常: {str(e)}")
            return False
            
    def get_countdown(self, target_time: datetime) -> str:
        """获取倒计时字符串"""
        current_time = self.get_synced_time()
        time_diff = target_time - current_time
        
        if time_diff.total_seconds() <= 0:
            return "00:00:00"
            
        # 计算时分秒
        total_seconds = int(time_diff.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# 全局时间同步器实例
time_sync = TimeSync() 