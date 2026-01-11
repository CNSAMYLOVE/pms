#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""客户端账号管理器（参考pmq实现）"""
import json
import os
from typing import List, Dict, Optional

# 数据存储目录（参考pmq的实现）
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
DATA_DIR = os.path.join(project_root, 'pms', 'data', 'client')
os.makedirs(DATA_DIR, exist_ok=True)
ACCOUNTS_FILE = os.path.join(DATA_DIR, 'accounts.json')

class AccountManager:
    """账号管理器（客户端）"""
    
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
        """添加账号（从服务端下传）"""
        account_id = account_data.get('id')
        if not account_id:
            return {'success': False, 'message': '缺少账号ID'}
        
        # 检查是否已存在
        for i, acc in enumerate(self.accounts):
            if acc.get('id') == account_id:
                # 更新账号信息
                for key, value in account_data.items():
                    if key != 'id':
                        self.accounts[i][key] = value
                self._save_accounts()
                return {'success': True, 'message': '账号已更新'}
        
        # 新增账号
        account = account_data.copy()
        self.accounts.append(account)
        self._save_accounts()
        return {'success': True, 'message': '账号添加成功'}
    
    def get_account(self, account_id: int) -> Optional[Dict]:
        """获取账号信息"""
        for acc in self.accounts:
            if acc.get('id') == account_id:
                return acc.copy()
        return None
    
    def get_all_accounts(self) -> List[Dict]:
        """获取所有账号"""
        return [acc.copy() for acc in self.accounts]
    
    def delete_account(self, account_id: int) -> Dict:
        """删除账号"""
        self.accounts = [acc for acc in self.accounts if acc.get('id') != account_id]
        self._save_accounts()
        return {'success': True, 'message': '账号删除成功'}


