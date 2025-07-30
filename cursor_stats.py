#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cursor Stats Alfred Workflow - 简化版本
只使用 Python 标准库，无需第三方依赖

功能：
1. 查看剩余 Premium 请求次数
2. 查看使用量计费情况
3. 账户周期信息
4. 缓存机制
"""

import json
import os
import sys
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
import base64
import time
from datetime import datetime, timedelta
import subprocess

class CursorStatsSimple:
    def __init__(self):
        self.workflow_dir = os.path.expanduser('~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/cursor-stats')
        self.cache_file = os.path.join(self.workflow_dir, 'cache.json')
        self.config_file = os.path.join(self.workflow_dir, 'config.json')
        
        # 从环境变量读取配置，如果没有则使用默认值
        try:
            self.cache_duration = int(os.environ.get('cache_duration', '60'))
        except ValueError:
            self.cache_duration = 60
        
        # 确保工作目录存在
        os.makedirs(self.workflow_dir, exist_ok=True)
        
        # 默认配置，优先使用环境变量
        self.config = {
            'currency': os.environ.get('currency', 'USD'),
            'language': 'zh',
            'show_progress_bars': True,
            'refresh_interval': self.cache_duration
        }
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            self.log_error(f"加载配置失败: {e}")

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_error(f"保存配置失败: {e}")

    def log_error(self, message):
        """错误日志"""
        log_file = os.path.join(self.workflow_dir, 'error.log')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass  # 忽略日志写入错误

    def get_cursor_db_path(self):
        """获取 Cursor 数据库文件路径（macOS）"""
        possible_paths = [
            os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"),
            os.path.expanduser("~/Library/Application Support/Code/User/globalStorage/state.vscdb"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None

    def decode_jwt_payload(self, token):
        """简单的 JWT payload 解码（不验证签名）"""
        try:
            # JWT 格式: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # 解码 payload（第二部分）
            payload = parts[1]
            
            # 添加必要的 padding
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += '=' * (4 - missing_padding)
            
            # Base64 解码
            decoded_bytes = base64.urlsafe_b64decode(payload.encode('utf-8'))
            decoded_str = decoded_bytes.decode('utf-8')
            
            # 解析 JSON
            return json.loads(decoded_str)
            
        except Exception as e:
            self.log_error(f"JWT 解码失败: {e}")
            return None

    def get_cursor_token(self):
        """从 Cursor 数据库获取认证 token"""
        db_path = self.get_cursor_db_path()
        if not db_path:
            return None
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'cursorAuth/accessToken'")
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
            
            token = result[0]
            
            # 解析 JWT 获取用户 ID
            payload = self.decode_jwt_payload(token)
            if not payload or 'sub' not in payload:
                return None
            
            user_id = payload['sub'].split('|')[1]
            session_token = f"{user_id}%3A%3A{token}"
            
            return session_token
            
        except Exception as e:
            self.log_error(f"获取 token 失败: {e}")
            return None

    def make_http_request(self, url, token, method='GET', data=None):
        """发送 HTTP 请求"""
        try:
            headers = {
                'Cookie': f'WorkosCursorSessionToken={token}',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            if method == 'GET':
                req = urllib.request.Request(url, headers=headers)
            else:
                json_data = json.dumps(data or {}).encode('utf-8') if data else b'{}'
                req = urllib.request.Request(url, data=json_data, headers=headers)
                req.get_method = lambda: method
            
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
                
        except Exception as e:
            self.log_error(f"HTTP 请求失败 ({url}): {e}")
            return None

    def fetch_usage_stats(self, token):
        """获取使用量统计"""
        user_id = token.split('%3A%3A')[0]
        
        # 获取基本使用量数据
        usage_url = f"https://cursor.com/api/usage?user={user_id}"
        usage_data = self.make_http_request(usage_url, token)
        
        if not usage_data:
            return None
        
        # 获取当前月账单数据
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        # 使用量计费通常在每月 3 号更新
        if current_date.day < 3:
            if current_month == 1:
                current_month = 12
                current_year -= 1
            else:
                current_month -= 1
        
        invoice_data = self.make_http_request(
            "https://cursor.com/api/dashboard/get-monthly-invoice",
            token,
            method='POST',
            data={
                'month': current_month,
                'year': current_year,
                'includeUsageEvents': False
            }
        )
        
        # 获取使用限制
        limit_data = self.make_http_request(
            "https://cursor.com/api/dashboard/get-hard-limit",
            token,
            method='POST'
        )
        
        return {
            'usage': usage_data,
            'invoice': invoice_data,
            'limits': limit_data,
            'month': current_month,
            'year': current_year
        }

    def get_cached_data(self):
        """获取缓存数据"""
        try:
            if not os.path.exists(self.cache_file):
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # 检查缓存是否过期
            if time.time() - cache.get('timestamp', 0) > self.cache_duration:
                return None
            
            return cache.get('data')
            
        except Exception as e:
            self.log_error(f"读取缓存失败: {e}")
            return None

    def save_cached_data(self, data):
        """保存缓存数据"""
        try:
            cache = {
                'timestamp': time.time(),
                'data': data
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.log_error(f"保存缓存失败: {e}")

    def format_currency(self, amount):
        """格式化货币显示"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'CNY': '¥',
            'AUD': 'A$',
            'CAD': 'C$'
        }
        
        symbol = currency_symbols.get(self.config['currency'], '$')
        return f"{symbol}{amount:.2f}"

    def create_progress_bar(self, current, total, length=15):
        """创建进度条"""
        if total == 0:
            percentage = 0
        else:
            percentage = min(current / total * 100, 100)
        
        filled = int(length * percentage / 100)
        
        # 使用简洁的进度条样式
        bar = "▓" * filled + "░" * (length - filled)
        
        return f"{bar} {percentage:.1f}%"

    def parse_iso_date(self, iso_string):
        """解析 ISO 格式日期"""
        try:
            # 移除 Z 后缀并解析
            if iso_string.endswith('Z'):
                iso_string = iso_string[:-1] + '+00:00'
            
            # 简单解析 ISO 格式
            date_part = iso_string.split('T')[0]
            year, month, day = map(int, date_part.split('-'))
            return datetime(year, month, day)
            
        except Exception as e:
            self.log_error(f"日期解析失败: {e}")
            return datetime.now()

    def get_period_info(self, start_of_month):
        """获取周期信息"""
        try:
            start_date = self.parse_iso_date(start_of_month)
            
            # 计算下个月的第一天
            if start_date.month == 12:
                end_date = datetime(start_date.year + 1, 1, 1)
            else:
                end_date = datetime(start_date.year, start_date.month + 1, 1)
            
            current_date = datetime.now()
            total_days = (end_date - start_date).days
            elapsed_days = (current_date - start_date).days
            remaining_days = max(0, total_days - elapsed_days)
            
            return {
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days,
                'elapsed_days': elapsed_days,
                'remaining_days': remaining_days,
                'progress_percentage': min(elapsed_days / total_days * 100, 100) if total_days > 0 else 0
            }
            
        except Exception as e:
            self.log_error(f"解析周期信息失败: {e}")
            return {}

    def calculate_daily_remaining(self, current, total, remaining_days):
        """计算每日剩余请求数"""
        if remaining_days <= 0:
            return 0
        
        remaining_requests = max(0, total - current)
        return remaining_requests / remaining_days

    def generate_alfred_items(self, stats_data):
        """生成 Alfred 结果项"""
        items = []
        
        try:
            usage = stats_data.get('usage', {})
            invoice = stats_data.get('invoice', {})
            limits = stats_data.get('limits', {})
            
            # Premium 请求统计
            gpt4_data = usage.get('gpt-4', {})
            current_requests = gpt4_data.get('numRequests', 0)
            max_requests = gpt4_data.get('maxRequestUsage', 500)
            remaining_requests = max(0, max_requests - current_requests)
            usage_percentage = (current_requests / max_requests * 100) if max_requests > 0 else 0
            
            # 周期信息
            start_of_month = usage.get('startOfMonth', '')
            period_info = self.get_period_info(start_of_month) if start_of_month else {}
            
            # 主要统计项 - Premium 请求
            progress_bar = self.create_progress_bar(current_requests, max_requests)
            
            subtitle_parts = [
                f"已用 {current_requests}/{max_requests}",
                f"剩余 {remaining_requests} 次"
            ]
            
            if period_info.get('remaining_days', 0) > 0:
                daily_remaining = self.calculate_daily_remaining(
                    current_requests, max_requests, period_info['remaining_days']
                )
                subtitle_parts.append(f"每日可用 {daily_remaining:.1f} 次")
            
            # 添加周期进度
            if period_info:
                period_progress = period_info.get('progress_percentage', 0)
                subtitle_parts.append(f"周期进度 {period_progress:.1f}%")
            
            items.append({
                'uid': 'premium_requests',
                'title': f"Premium 请求 {progress_bar}",
                'subtitle': " | ".join(subtitle_parts),
                'arg': 'premium_requests',
                'mods': {
                    'cmd': {
                        'subtitle': f"复制: {current_requests}/{max_requests} ({usage_percentage:.1f}%)"
                    }
                }
            })
            
            # 使用量计费统计
            total_cost = 0
            if invoice and invoice.get('items'):
                for item in invoice['items']:
                    if item.get('cents') and 'Mid-month' not in item.get('description', ''):
                        total_cost += item['cents'] / 100
            
            hard_limit = limits.get('hardLimit', 0) if limits else 0
            
            if hard_limit > 0:
                cost_percentage = (total_cost / hard_limit * 100) if hard_limit > 0 else 0
                remaining_budget = max(0, hard_limit - total_cost)
                cost_progress_bar = self.create_progress_bar(int(total_cost * 100), int(hard_limit * 100))
                
                items.append({
                    'uid': 'usage_based_pricing',
                    'title': f"使用量计费 {cost_progress_bar}",
                    'subtitle': f"已花费 {self.format_currency(total_cost)} / {self.format_currency(hard_limit)} | 剩余预算 {self.format_currency(remaining_budget)}",
                    'arg': 'usage_based_pricing',
                    'mods': {
                        'cmd': {
                            'subtitle': f"复制: {self.format_currency(total_cost)} / {self.format_currency(hard_limit)} ({cost_percentage:.1f}%)"
                        }
                    }
                })
            
            # 账户信息 - 显示上次重置时间
            if start_of_month:
                try:
                    reset_date = self.parse_iso_date(start_of_month)
                    reset_date_str = reset_date.strftime('%Y-%m-%d')
                    days_since_reset = (datetime.now() - reset_date).days
                    
                    items.append({
                        'uid': 'account_info',
                        'title': f"账户周期信息",
                        'subtitle': f"上次重置: {reset_date_str} | 已过 {days_since_reset} 天",
                        'arg': 'account_info',
                        'mods': {
                            'cmd': {
                                'subtitle': f"复制: 上次重置时间 {reset_date_str}"
                            }
                        }
                    })
                except Exception as e:
                    self.log_error(f"解析重置时间失败: {e}")
            
            # 快速操作
            items.append({
                'uid': 'refresh',
                'title': '刷新数据',
                'subtitle': f'强制刷新 Cursor 使用量数据 (缓存: {self.cache_duration}s)',
                'arg': 'refresh'
            })
            
            items.append({
                'uid': 'open_cursor_settings',
                'title': '打开 Cursor 设置',
                'subtitle': '在浏览器中打开 Cursor 账户设置页面',
                'arg': 'open_cursor_settings'
            })
            
        except Exception as e:
            self.log_error(f"生成 Alfred 项目失败: {e}")
            items.append({
                'uid': 'error',
                'title': '获取数据失败',
                'subtitle': f'错误: {str(e)}',
                'arg': 'error'
            })
        
        return items

    def handle_action(self, action):
        """处理用户操作"""
        if action == 'refresh':
            # 删除缓存文件强制刷新
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            print("数据已刷新")
            
        elif action == 'open_cursor_settings':
            # 打开 Cursor 设置页面（macOS）
            subprocess.run(['open', 'https://www.cursor.com/settings'])
            
        elif action in ['premium_requests', 'usage_based_pricing', 'account_info']:
            # 这里可以实现复制到剪贴板的功能
            print(f"已选择 {action}")

    def run(self, query=''):
        """运行 workflow"""
        # 如果是操作命令（非显示统计信息的命令）
        if query and query in ['refresh', 'open_cursor_settings', 'premium_requests', 'usage_based_pricing', 'account_info']:
            self.handle_action(query)
            return
        
        # 获取 token
        token = self.get_cursor_token()
        if not token:
            result = {
                'items': [{
                    'uid': 'no_token',
                    'title': '未找到 Cursor 认证信息',
                    'subtitle': '请确保 Cursor 已登录并重试',
                    'arg': 'error'
                }]
            }
            print(json.dumps(result, ensure_ascii=False))
            return
        
        # 尝试从缓存获取数据
        stats_data = self.get_cached_data()
        
        # 如果没有缓存或需要刷新，获取新数据
        if not stats_data or query == 'refresh':
            stats_data = self.fetch_usage_stats(token)
            
            if stats_data:
                self.save_cached_data(stats_data)
            else:
                result = {
                    'items': [{
                        'uid': 'api_error',
                        'title': '获取数据失败',
                        'subtitle': '请检查网络连接和 Cursor 登录状态',
                        'arg': 'error'
                    }]
                }
                print(json.dumps(result, ensure_ascii=False))
                return
        
        # 生成 Alfred 结果
        items = self.generate_alfred_items(stats_data)
        
        result = {'items': items}
        print(json.dumps(result, ensure_ascii=False))

def main():
    workflow = CursorStatsSimple()
    
    # 获取查询参数
    query = sys.argv[1] if len(sys.argv) > 1 else ''
    
    workflow.run(query)

if __name__ == '__main__':
    main() 