#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""客户端配置管理器"""
import json
import os

# 配置文件路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 配置目录：client/data/client/
CONFIG_DIR = os.path.join(current_dir, 'data', 'client')
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_config(self):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """设置配置值"""
        self.config[key] = value
        self._save_config()
    
    def get_client_id(self) -> str:
        """获取客户端ID"""
        return self.get('client_id', '')
    
    def set_client_id(self, client_id: str):
        """设置客户端ID"""
        self.set('client_id', client_id)
    
    def get_server_url(self) -> str:
        """获取服务端URL（默认固定为服务端公网IP）"""
        return self.get('server_url', 'http://101.32.22.185:8000')
    
    def set_server_url(self, server_url: str):
        """设置服务端URL"""
        self.set('server_url', server_url)
    
    def has_config(self) -> bool:
        """检查是否已有配置"""
        return bool(self.get_client_id())
    
    def get_client_ip(self) -> str:
        """获取客户端IP（用于注册到服务端）"""
        return self.get('client_ip', '')
    
    def set_client_ip(self, client_ip: str):
        """设置客户端IP（用于注册到服务端）"""
        self.set('client_ip', client_ip)

