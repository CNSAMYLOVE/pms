#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""账号管理模块"""
import json
import os
from typing import List, Dict, Optional
try:
    from .config import ACCOUNTS_FILE
except ImportError:
    from config import ACCOUNTS_FILE

class AccountManager:
    """账号管理器"""
    
    def __init__(self):
        self.accounts_file = ACCOUNTS_FILE
        self._load_accounts()
    
    def _load_accounts(self):
        """加载账号数据"""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
            except:
                self.accounts = []
        else:
            self.accounts = []
        self._save_accounts()
    
    def _save_accounts(self):
        """保存账号数据"""
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)
    
    def add_account(self, account_data: Dict) -> Dict:
        """添加账号
        
        Args:
            account_data: 账号数据字典，包含：
                - name: 账号名称
                - private_key: 私钥
                - proxy_wallet_address: 代理钱包地址（可选）
                - builder_api_key: Builder API Key
                - builder_api_secret: Builder API Secret
                - builder_api_passphrase: Builder API Passphrase
                - proxy_ip: 代理IP（格式：http://ip:port 或 http://user:pass@ip:port）
                - notes: 备注信息（可选）
        
        Returns:
            添加结果
        """
        # 生成账号ID
        if self.accounts:
            account_id = max([acc.get('id', 0) for acc in self.accounts]) + 1
        else:
            account_id = 1
        
        account = {
            'id': account_id,
            'name': account_data.get('name', f'账号{account_id}'),
            'private_key': account_data.get('private_key', ''),
            'proxy_wallet_address': account_data.get('proxy_wallet_address', ''),
            'builder_api_key': account_data.get('builder_api_key', ''),
            'builder_api_secret': account_data.get('builder_api_secret', ''),
            'builder_api_passphrase': account_data.get('builder_api_passphrase', ''),
            'proxy_ip': account_data.get('proxy_ip', ''),
            'notes': account_data.get('notes', ''),
            'status': 'active',  # active, paused, error
            'created_at': account_data.get('created_at', ''),
            'balance_usdc': 0.0,
            'total_orders': 0,
            'total_profit': 0.0
        }
        
        self.accounts.append(account)
        self._save_accounts()
        return {'success': True, 'account_id': account_id, 'message': '账号添加成功'}
    
    def update_account(self, account_id: int, account_data: Dict) -> Dict:
        """更新账号信息"""
        for i, acc in enumerate(self.accounts):
            if acc.get('id') == account_id:
                # 更新字段（保留原有字段）
                for key, value in account_data.items():
                    if key != 'id':  # 不允许修改ID
                        self.accounts[i][key] = value
                self._save_accounts()
                return {'success': True, 'message': '账号更新成功'}
        return {'success': False, 'message': '账号不存在'}
    
    def delete_account(self, account_id: int) -> Dict:
        """删除账号"""
        self.accounts = [acc for acc in self.accounts if acc.get('id') != account_id]
        self._save_accounts()
        return {'success': True, 'message': '账号删除成功'}
    
    def get_account(self, account_id: int) -> Optional[Dict]:
        """获取账号信息"""
        for acc in self.accounts:
            if acc.get('id') == account_id:
                return acc
        return None
    
    def get_all_accounts(self) -> List[Dict]:
        """获取所有账号"""
        return self.accounts
    
    def get_active_accounts(self) -> List[Dict]:
        """获取活跃账号"""
        return [acc for acc in self.accounts if acc.get('status') == 'active']
    
    def update_account_status(self, account_id: int, status: str) -> Dict:
        """更新账号状态"""
        for i, acc in enumerate(self.accounts):
            if acc.get('id') == account_id:
                self.accounts[i]['status'] = status
                self._save_accounts()
                return {'success': True, 'message': '状态更新成功'}
        return {'success': False, 'message': '账号不存在'}
    
    def update_account_balance(self, account_id: int, balance: float) -> Dict:
        """更新账号余额"""
        for i, acc in enumerate(self.accounts):
            if acc.get('id') == account_id:
                self.accounts[i]['balance_usdc'] = balance
                self._save_accounts()
                return {'success': True}
        return {'success': False}

