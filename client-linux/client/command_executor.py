#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""客户端命令执行器（串行下单）"""
import time
import random
import sys
import os
from typing import Dict, List, Optional
from datetime import datetime

# 添加路径以复用pmq的TradingBot
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# 尝试多种路径查找 pmq 目录
pmq_dirs = [
    os.path.join(parent_dir, 'pmq'),  # pms1/client -> pms1/pmq
    os.path.join(parent_dir, '..', 'pmq'),  # pms1/client -> pmq
    os.path.join(parent_dir, 'pmq'),  # client_deploy/client -> client_deploy/pmq
]

pmq_dir = None
for pmq_path in pmq_dirs:
    if os.path.exists(pmq_path):
        pmq_dir = pmq_path
        sys.path.insert(0, pmq_dir)
        break

if not pmq_dir:
    # 如果都找不到，尝试在当前目录的上级查找
    project_root = os.path.dirname(parent_dir)
    pmq_dir = os.path.join(project_root, 'pmq')
    if os.path.exists(pmq_dir):
        sys.path.insert(0, pmq_dir)
    else:
        # 最后尝试：在当前目录的上级目录查找
        alt_pmq = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'pmq')
        if os.path.exists(alt_pmq):
            sys.path.insert(0, alt_pmq)

try:
    from trading_bot import TradingBot
except ImportError as e:
    print(f"警告: 无法导入TradingBot: {e}")
    print(f"已尝试的路径: {pmq_dirs}")
    print(f"请确保pmq目录存在，或修改 command_executor.py 中的路径配置")
    raise

GAMMA_API_HOST = "https://gamma-api.polymarket.com"

class CommandExecutor:
    """命令执行器（客户端）"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.accounts: Dict[int, TradingBot] = {}  # account_id -> TradingBot
        # 导入账号管理器
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        from account_manager import AccountManager
        self.account_manager = AccountManager()
        # 加载已存储的账号
        self._load_stored_accounts()
    
    def _load_stored_accounts(self):
        """从本地存储加载账号"""
        stored_accounts = self.account_manager.get_all_accounts()
        for account_data in stored_accounts:
            try:
                account_id = account_data.get('id')
                bot = TradingBot(account_data, proxy_ip=account_data.get('proxy_ip'))
                self.accounts[account_id] = bot
            except Exception as e:
                print(f"[客户端{self.client_id}] 加载存储账号失败: {e}")
    
    def load_account(self, account_data: Dict) -> bool:
        """加载账号到客户端（从服务端下传）"""
        try:
            account_id = account_data.get('id')
            if not account_id:
                print(f"[客户端{self.client_id}] 加载账号失败: 缺少账号ID")
                return False
            
            print(f"[客户端{self.client_id}] 开始加载账号: ID={account_id}")
            
            # 保存到本地
            add_result = self.account_manager.add_account(account_data)
            if not add_result.get('success', True):
                print(f"[客户端{self.client_id}] 保存账号到本地失败: {add_result.get('message', '未知错误')}")
            
            # 加载到内存
            print(f"[客户端{self.client_id}] 创建TradingBot实例...")
            bot = TradingBot(account_data, proxy_ip=account_data.get('proxy_ip'))
            self.accounts[account_id] = bot
            print(f"[客户端{self.client_id}] 账号加载成功: ID={account_id}")
            return True
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[客户端{self.client_id}] 加载账号失败: {e}")
            print(f"[客户端{self.client_id}] 错误详情:\n{error_detail}")
            return False
    
    def unload_account(self, account_id: int) -> bool:
        """卸载账号"""
        if account_id in self.accounts:
            del self.accounts[account_id]
            return True
        return False
    
    def get_account_ids(self) -> List[int]:
        """获取所有已加载的账号ID"""
        return list(self.accounts.keys())
    
    def execute_place_order(self, params: Dict) -> Dict:
        """执行下单命令（串行，带随机延迟）
        
        Args:
            params:
                - account_ids: 账号ID列表
                - market_info: 市场信息（可选，如果提供则直接使用）
                    {
                        "market_id": str,
                        "question": str,
                        "side": "YES" | "NO",
                        "token_id": str,  # YES或NO对应的token_id
                        "price": float    # YES或NO对应的价格
                    }
                - event_url: 事件URL（可选，如果不提供market_info则使用）
                - side: YES 或 NO（可选，如果不提供market_info则必须）
                - order_amount_usd: 下单数量（美元）
                - random_delay_min: 随机延迟最小值（秒）
                - random_delay_max: 随机延迟最大值（秒）
        """
        account_ids = params.get('account_ids', [])
        market_info = params.get('market_info')
        event_url = params.get('event_url', '')
        side = params.get('side', 'YES').upper()
        order_amount_usd = params.get('order_amount_usd', 2.0)
        random_delay_min = params.get('random_delay_min', 1)
        random_delay_max = params.get('random_delay_max', 5)
        
        if not account_ids:
            return {'success': False, 'message': '账号ID列表为空'}
        
        if not self.accounts:
            return {'success': False, 'message': '没有已加载的账号'}
        
        try:
            # 如果提供了market_info，直接使用
            if market_info:
                market_id = market_info.get('market_id')
                market_question = market_info.get('question', '未知市场')
                side = market_info.get('side', side).upper()
                token_id = market_info.get('token_id')
                price = market_info.get('price')
                
                if not token_id or price is None:
                    return {'success': False, 'message': 'market_info缺少token_id或price'}
                
                if side not in ['YES', 'NO']:
                    return {'success': False, 'message': '方向必须是YES或NO'}
                
                order_size = order_amount_usd / price
                
                order_info = {
                    "market_id": market_id,
                    "market_question": market_question,
                    "token_id": token_id,
                    "best_ask": price,
                    "order_size": order_size,
                    "order_amount_usd": order_amount_usd,
                    "side": "UP" if side == 'YES' else "DOWN"
                }
            else:
                # 否则通过event_url获取市场数据
                if side not in ['YES', 'NO']:
                    return {'success': False, 'message': '方向必须是YES或NO'}
                
                scan_bot = next(iter(self.accounts.values()))
                
                # 获取市场信息
                market_data = self._get_market_data(scan_bot, event_url)
                if not market_data:
                    return {'success': False, 'message': '无法获取市场数据'}
                
                market_id = market_data.get("id")
                market_question = market_data.get("question", "未知市场")
                
                # 获取价格和token
                yes_token_id, no_token_id = scan_bot.get_yes_no_token_ids(market_id, market_data)
                if not yes_token_id or not no_token_id:
                    return {'success': False, 'message': '无法获取市场token IDs'}
                
                yes_price, no_price = scan_bot.get_yes_no_prices_via_clob_spreads(market_id, market_data)
                if yes_price is None or no_price is None:
                    return {'success': False, 'message': '无法获取市场价格'}
                
                # 选择方向
                if side == 'YES':
                    price_used = yes_price
                    token_used = yes_token_id
                else:
                    price_used = no_price
                    token_used = no_token_id
                
                order_size = order_amount_usd / price_used
                
                order_info = {
                    "market_id": market_id,
                    "market_question": market_question,
                    "token_id": token_used,
                    "best_ask": price_used,
                    "order_size": order_size,
                    "order_amount_usd": order_amount_usd,
                    "side": "UP" if side == 'YES' else "DOWN"
                }
            
            strategy_config = {'order_amount_usd': order_amount_usd}
            
            # 串行下单（带随机延迟）
            success_count = 0
            fail_count = 0
            results = []
            
            print(f"[客户端{self.client_id}] 开始串行下单: {len(account_ids)}个账号, 市场={order_info.get('market_question')}, 方向={side}")
            
            for i, account_id in enumerate(account_ids):
                bot = self.accounts.get(account_id)
                if not bot:
                    fail_count += 1
                    results.append({'account_id': account_id, 'success': False, 'message': '账号未加载'})
                    continue
                
                # 执行下单
                try:
                    result = bot.place_buy_order(order_info, strategy_config, auto_confirm=True, skip_balance_check=True, verbose=False)
                    if result:
                        success_count += 1
                        results.append({'account_id': account_id, 'success': True, 'message': '下单成功'})
                        bot._log_status(f"下单{side}成功")
                    else:
                        fail_count += 1
                        results.append({'account_id': account_id, 'success': False, 'message': '下单失败'})
                        bot._log_error(f"下单{side}失败")
                except Exception as e:
                    fail_count += 1
                    results.append({'account_id': account_id, 'success': False, 'message': f'下单异常: {str(e)}'})
                    bot._log_error(f"下单异常: {e}")
                
                # 如果不是最后一个账号，等待随机延迟
                if i < len(account_ids) - 1:
                    delay = random.uniform(random_delay_min, random_delay_max)
                    print(f"[客户端{self.client_id}] 等待 {delay:.2f} 秒后执行下一个账号...")
                    time.sleep(delay)
            
            return {
                'success': success_count > 0,
                'success_count': success_count,
                'fail_count': fail_count,
                'total_count': len(account_ids),
                'results': results,
                'message': f'串行下单完成: 成功 {success_count}, 失败 {fail_count}'
            }
            
        except Exception as e:
            import traceback
            return {'success': False, 'message': f'下单执行异常: {str(e)}', 'traceback': traceback.format_exc()}
    
    def execute_sell(self, params: Dict) -> Dict:
        """执行出售命令
        
        Args:
            params:
                - account_ids: 账号ID列表（可选，不提供则出售所有账号）
        """
        account_ids = params.get('account_ids', [])
        if not account_ids:
            account_ids = list(self.accounts.keys())
        
        if not account_ids:
            return {'success': False, 'message': '没有要出售的账号'}
        
        success_count = 0
        fail_count = 0
        results = []
        
        for account_id in account_ids:
            bot = self.accounts.get(account_id)
            if not bot:
                fail_count += 1
                continue
            
            try:
                result = bot.sell_all_positions(verbose=False)
                if result.get('success'):
                    success_count += result.get('sold_count', 0)
                    fail_count += result.get('failed_count', 0)
                    results.append({'account_id': account_id, 'result': result})
                else:
                    fail_count += 1
                    results.append({'account_id': account_id, 'success': False, 'message': result.get('message', '出售失败')})
            except Exception as e:
                fail_count += 1
                results.append({'account_id': account_id, 'success': False, 'message': f'出售异常: {str(e)}'})
        
        return {
            'success': success_count > 0,
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results,
            'message': f'出售完成: 成功 {success_count}, 失败 {fail_count}'
        }
    
    def execute_redeem(self, params: Dict) -> Dict:
        """执行结算命令
        
        Args:
            params:
                - account_ids: 账号ID列表（可选，不提供则结算所有账号）
        """
        account_ids = params.get('account_ids', [])
        if not account_ids:
            account_ids = list(self.accounts.keys())
        
        if not account_ids:
            return {'success': False, 'message': '没有要结算的账号'}
        
        success_count = 0
        fail_count = 0
        results = []
        
        for account_id in account_ids:
            bot = self.accounts.get(account_id)
            if not bot:
                fail_count += 1
                continue
            
            try:
                result = bot.auto_redeem_positions()
                if result:
                    success_count += 1
                    results.append({'account_id': account_id, 'success': True, 'message': '结算成功'})
                else:
                    fail_count += 1
                    results.append({'account_id': account_id, 'success': False, 'message': '结算失败'})
            except Exception as e:
                fail_count += 1
                results.append({'account_id': account_id, 'success': False, 'message': f'结算异常: {str(e)}'})
        
        return {
            'success': success_count > 0,
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results,
            'message': f'结算完成: 成功 {success_count}, 失败 {fail_count}'
        }
    
    def execute_get_balance(self, params: Dict) -> Dict:
        """执行获取余额命令
        
        Args:
            params:
                - account_ids: 账号ID列表（可选，不提供则获取所有账号）
        """
        account_ids = params.get('account_ids', [])
        if not account_ids:
            account_ids = list(self.accounts.keys())
        
        if not account_ids:
            return {'success': False, 'message': '没有要查询的账号'}
        
        results = []
        for account_id in account_ids:
            bot = self.accounts.get(account_id)
            if not bot:
                results.append({'account_id': account_id, 'balance': 0.0, 'message': '账号未加载'})
                continue
            
            try:
                balance = bot.get_balance_usdc()
                results.append({'account_id': account_id, 'balance': balance, 'success': True})
            except Exception as e:
                results.append({'account_id': account_id, 'balance': 0.0, 'message': f'查询失败: {str(e)}'})
        
        return {
            'success': True,
            'results': results
        }
    
    def _get_market_data(self, bot: TradingBot, event_url: str = '') -> Optional[Dict]:
        """获取市场数据"""
        if event_url:
            # 从URL解析市场
            parse_info = self._parse_market_from_url(event_url)
            if parse_info:
                return bot.fetch_market_detail(parse_info)
        else:
            # 使用默认15分钟预测市场
            markets = bot.get_eth_15min_markets()
            if markets:
                market_id = markets[0].get("id")
                return bot.fetch_market_detail(market_id)
        return None
    
    def _parse_market_from_url(self, market_url: str) -> Optional[Dict]:
        """从URL解析市场信息"""
        if not market_url:
            return None
        
        import re
        if 'polymarket.com' in market_url:
            match = re.search(r'/event/([^/?]+)', market_url)
            if match:
                slug = match.group(1)
                return {'type': 'slug', 'value': slug}
            match = re.search(r'/(\d+)/?', market_url)
            if match:
                return {'type': 'id', 'value': match.group(1)}
        
        value = market_url.strip()
        if value.isdigit():
            return {'type': 'id', 'value': value}
        else:
            return {'type': 'slug', 'value': value}

