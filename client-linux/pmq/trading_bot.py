#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""交易机器人核心模块（支持多账号和代理）"""
import time
import requests
import json
from datetime import datetime
from typing import Dict, Optional, Callable, List
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY, SELL
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 禁用 SSL 警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

try:
    from .config import (
        CLOB_HOST, GAMMA_API_HOST, DATA_API_HOST, CHAIN_ID,
        USDC_ADDRESS_POLYGON, CTF_ADDRESS, GNOSIS_SAFE_FACTORY, POLYMARKET_PROXY_FACTORY
    )
except ImportError:
    from config import (
        CLOB_HOST, GAMMA_API_HOST, DATA_API_HOST, CHAIN_ID,
        USDC_ADDRESS_POLYGON, CTF_ADDRESS, GNOSIS_SAFE_FACTORY, POLYMARKET_PROXY_FACTORY
    )

# 从pm.py复制的ABI和常量
USDC_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
     "name": "allowance", "outputs": [{"name": "remaining", "type": "uint256"}], "type": "function"}
]

CTF_ABI = [
    {"constant": False, "inputs": [
        {"name": "collateralToken", "type": "address"},
        {"name": "parentCollectionId", "type": "bytes32"},
        {"name": "conditionId", "type": "bytes32"},
        {"name": "indexSets", "type": "uint256[]"}
    ], "name": "redeemPositions", "outputs": [], "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}, {"name": "id", "type": "uint256"}],
     "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

PROXY_FACTORY_ABI = [
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}],
     "name": "getProxy", "outputs": [{"name": "proxy", "type": "address"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}],
     "name": "proxies", "outputs": [{"name": "", "type": "address"}], "type": "function"}
]


class TradingBot:
    """交易机器人（支持代理IP）"""
    
    def __init__(self, account_data: Dict, proxy_ip: Optional[str] = None):
        """初始化交易机器人
        
        Args:
            account_data: 账号数据
            proxy_ip: 代理IP（格式：http://ip:port 或 http://user:pass@ip:port）
        """
        self.account_id = account_data.get('id')
        self.account_name = account_data.get('name', '')
        self.private_key = account_data.get('private_key', '')
        self.proxy_wallet_address = account_data.get('proxy_wallet_address', '')
        self.builder_api_key = account_data.get('builder_api_key', '')
        self.builder_api_secret = account_data.get('builder_api_secret', '')
        self.builder_api_passphrase = account_data.get('builder_api_passphrase', '')
        self.proxy_ip = proxy_ip or account_data.get('proxy_ip', '')
        
        # 配置代理
        self.proxies = None
        if self.proxy_ip:
            self.proxies = {
                'http': self.proxy_ip,
                'https': self.proxy_ip
            }
        
        # 初始化Web3（使用代理）
        self.w3 = None
        self.account = None
        self.client = None
        self.trading_client = None
        
        # 状态回调
        self.status_callback: Optional[Callable] = None
        
        self._init_clients()
    
    def _init_clients(self):
        """初始化客户端"""
        try:
            # 初始化Web3（如果配置了代理，需要通过代理连接）
            # 注意：Web3的HTTPProvider可能不支持代理，需要特殊处理
            if self.proxies:
                # 使用代理的RPC节点（如果有）
                rpc_url = "https://polygon-rpc.com"
                # 如果使用代理，可能需要通过代理访问RPC
                # 这里简化处理，实际可能需要使用代理池或代理中间件
                self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            else:
                self.w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
            
            if self.private_key:
                self.account = self.w3.eth.account.from_key(self.private_key)
            
            # 初始化CLOB客户端
            if self.private_key:
                # 创建临时客户端获取API凭证
                temp_client = ClobClient(
                    host=CLOB_HOST,
                    key=self.private_key,
                    chain_id=CHAIN_ID,
                    signature_type=2
                )
                
                # 获取API凭证
                user_api_creds = temp_client.create_or_derive_api_creds()
                
                # 确定钱包地址
                if self.proxy_wallet_address:
                    funder_address = self.proxy_wallet_address
                    signature_type = 2  # Gnosis Safe
                else:
                    funder_address = self.account.address
                    signature_type = 0  # EOA
                
                # 创建交易客户端
                self.trading_client = ClobClient(
                    host=CLOB_HOST,
                    key=self.private_key,
                    chain_id=CHAIN_ID,
                    creds=user_api_creds,
                    signature_type=signature_type,
                    funder=funder_address
                )
            
            # 基础客户端（用于读取数据）
            self.client = ClobClient(
                host=CLOB_HOST,
                key=self.private_key or ("0x" + "0" * 64),
                chain_id=CHAIN_ID,
                signature_type=2
            )
            
        except Exception as e:
            self._log_error(f"初始化客户端失败: {e}")
    
    def _log_status(self, message: str):
        """记录状态（同时输出到控制台和回调）"""
        log_msg = f"[账号{self.account_id}] {message}"
        print(log_msg)  # 输出到控制台，和pm.py一样
        if self.status_callback:
            self.status_callback(self.account_id, message)
    
    def _log_error(self, message: str):
        """记录错误（同时输出到控制台和回调）"""
        log_msg = f"[账号{self.account_id}] 错误: {message}"
        print(log_msg)  # 输出到控制台
        if self.status_callback:
            self.status_callback(self.account_id, f"错误: {message}")
    
    def _make_request(self, method: str, url: str, **kwargs):
        """发起HTTP请求（支持代理）"""
        if self.proxies:
            kwargs['proxies'] = self.proxies
        kwargs['verify'] = False
        kwargs['timeout'] = 10
        
        if method.upper() == 'GET':
            return requests.get(url, **kwargs)
        elif method.upper() == 'POST':
            return requests.post(url, **kwargs)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")
    
    def fetch_market_detail(self, market_id_or_market):
        """获取市场详情（支持从事件slug获取）"""
        try:
            mid = None
            slug = None
            raw_id = None
            is_event_slug = False
            
            # 如果传入的是解析后的字典（包含type和value）
            if isinstance(market_id_or_market, dict) and 'type' in market_id_or_market:
                parse_info = market_id_or_market
                if parse_info['type'] == 'slug':
                    slug = parse_info['value']
                    is_event_slug = True  # 从/event/提取的slug，使用events API
                elif parse_info['type'] == 'id':
                    raw_id = parse_info['value']
            elif isinstance(market_id_or_market, dict):
                raw_id = market_id_or_market.get("id")
                slug = market_id_or_market.get("slug")
                if isinstance(raw_id, (int,)):
                    mid = raw_id
                elif isinstance(raw_id, str) and raw_id.isdigit():
                    try:
                        mid = int(raw_id)
                    except Exception:
                        mid = None
            else:
                if isinstance(market_id_or_market, (int,)):
                    mid = market_id_or_market
                elif isinstance(market_id_or_market, str) and market_id_or_market.isdigit():
                    try:
                        mid = int(market_id_or_market)
                    except Exception:
                        mid = None
                else:
                    # 可能是slug字符串
                    slug = str(market_id_or_market)
            
            # 优先尝试使用事件slug API（从/event/提取的）
            if slug and is_event_slug:
                url = f"{GAMMA_API_HOST}/events/slug/{slug}"
                resp = self._make_request('GET', url)
                if resp.status_code == 200:
                    event_data = resp.json()
                    # 事件API返回的数据可能包含markets字段，需要提取第一个市场
                    if isinstance(event_data, dict):
                        markets = event_data.get('markets', [])
                        if markets and len(markets) > 0:
                            # 返回第一个市场
                            market_id = markets[0].get('id')
                            if market_id:
                                # 获取完整市场详情
                                return self.fetch_market_detail(market_id)
                        # 如果没有markets字段，可能事件数据本身就是市场数据
                        if 'id' in event_data:
                            return event_data
                    elif isinstance(event_data, list) and len(event_data) > 0:
                        # 如果是列表，取第一个
                        market_id = event_data[0].get('id')
                        if market_id:
                            return self.fetch_market_detail(market_id)
            
            # 使用数字ID获取市场
            if mid is not None:
                url = f"{GAMMA_API_HOST}/markets/{mid}"
                resp = self._make_request('GET', url)
                if resp.status_code == 200:
                    return resp.json()
            
            if raw_id and isinstance(raw_id, str):
                url_raw = f"{GAMMA_API_HOST}/markets/{raw_id}"
                resp_raw = self._make_request('GET', url_raw)
                if resp_raw.status_code == 200:
                    return resp_raw.json()
            
            # 使用市场slug获取（markets/slug）
            if slug and not is_event_slug:
                url2 = f"{GAMMA_API_HOST}/markets/slug/{slug}"
                resp2 = self._make_request('GET', url2)
                if resp2.status_code == 200:
                    return resp2.json()
            
            return None
        except Exception as e:
            self._log_error(f"获取市场详情失败: {e}")
            return None
    
    def get_market_remaining_seconds(self, market_data):
        """计算市场剩余时间（秒）"""
        try:
            end_time_fields = [
                "endDate", "end_date", "endTime", "end_time",
                "endDateTimestamp", "endDateTimestampSeconds",
                "resolutionDate", "resolution_date"
            ]
            end_time = None
            for field in end_time_fields:
                if field in market_data:
                    end_time = market_data[field]
                    break
            if end_time is None:
                return None
            
            if isinstance(end_time, (int, float)):
                if end_time > 1e12:
                    end_time = end_time / 1000.0
            elif isinstance(end_time, str):
                try:
                    from dateutil import parser
                    dt = parser.parse(end_time)
                    end_time = dt.timestamp()
                except:
                    return None
            
            current_time = time.time()
            remaining = end_time - current_time
            return max(0, remaining)
        except Exception as e:
            self._log_error(f"计算剩余时间失败: {e}")
            return None
    
    def get_yes_no_token_ids(self, market_id, market_data=None):
        """获取YES/NO token IDs"""
        try:
            md = market_data if isinstance(market_data, dict) else None
            if not md:
                md = self.fetch_market_detail(market_id or market_data)
                if not isinstance(md, dict):
                    return None, None
            
            outcomes = md.get("outcomes")
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except Exception:
                    outcomes = None
            
            yes_id = None
            no_id = None
            
            if isinstance(outcomes, list):
                for o in outcomes:
                    if not isinstance(o, dict):
                        continue
                    title = (o.get("title") or o.get("name") or o.get("outcome") or "").strip().lower()
                    tid = o.get("clobTokenId") or o.get("tokenId") or o.get("token_id")
                    if not tid:
                        continue
                    if title == "yes" or title.startswith("yes") or title == "up" or title.startswith("up"):
                        yes_id = tid
                    elif title == "no" or title.startswith("no") or title == "down" or title.startswith("down"):
                        no_id = tid
                if yes_id and no_id:
                    return yes_id, no_id
                
                ids_seq = []
                for o in outcomes:
                    if isinstance(o, dict):
                        tid = o.get("clobTokenId") or o.get("tokenId") or o.get("token_id")
                        if tid:
                            ids_seq.append(tid)
                if len(ids_seq) >= 2:
                    return ids_seq[0], ids_seq[1]
            
            clob_token_ids_str = md.get("clobTokenIds")
            clob_ids = []
            if clob_token_ids_str:
                if isinstance(clob_token_ids_str, str):
                    try:
                        clob_ids = json.loads(clob_token_ids_str)
                        if not isinstance(clob_ids, list):
                            clob_ids = [clob_ids]
                    except Exception:
                        clob_ids = [tid.strip() for tid in clob_token_ids_str.split(",") if tid.strip()]
                elif isinstance(clob_token_ids_str, list):
                    clob_ids = clob_token_ids_str
            
            if len(clob_ids) >= 2:
                return clob_ids[0], clob_ids[1]
            
            return None, None
        except Exception as e:
            self._log_error(f"获取token IDs失败: {e}")
            return None, None
    
    def get_yes_no_prices_via_clob_spreads(self, market_id, market_data=None):
        """获取YES/NO价格"""
        try:
            yes_id, no_id = self.get_yes_no_token_ids(market_id, market_data)
            if not yes_id or not no_id:
                return None, None
            
            # 优先使用客户端get_spreads
            spreads = None
            if self.client and hasattr(self.client, 'get_spreads'):
                try:
                    spreads = self.client.get_spreads([yes_id, no_id])
                except Exception:
                    spreads = None
            
            def extract(token_id):
                if spreads is None:
                    return None
                if isinstance(spreads, dict):
                    entry = spreads.get(token_id) or spreads.get(str(token_id))
                elif isinstance(spreads, list):
                    entry = None
                    for e in spreads:
                        tid = e.get('token_id') or e.get('tokenId') if isinstance(e, dict) else None
                        if tid and (tid == token_id or str(tid) == str(token_id)):
                            entry = e
                            break
                else:
                    entry = None
                
                if isinstance(entry, dict):
                    val = entry.get('ask') or entry.get('bestAsk') or entry.get('sell')
                    try:
                        return float(val) if val is not None else None
                    except Exception:
                        return None
                if hasattr(entry, 'ask'):
                    try:
                        return float(entry.ask)
                    except Exception:
                        return None
                return None
            
            yes_price = extract(yes_id)
            no_price = extract(no_id)
            
            # 回退到HTTP接口
            def fetch_summary_price(token_id):
                try:
                    url = f"{CLOB_HOST}/summary?token_id={token_id}"
                    resp = self._make_request('GET', url)
                    if resp.status_code != 200:
                        return None
                    data = resp.json()
                    val = None
                    if isinstance(data, dict):
                        val = data.get('ask') or data.get('bestAsk') or data.get('sell')
                    if val is None and isinstance(data, list) and data:
                        entry = data[0]
                        if isinstance(entry, dict):
                            val = entry.get('ask') or entry.get('bestAsk') or entry.get('sell')
                    
                    # 标准化价格
                    try:
                        price = float(val)
                        if price <= 0:
                            return None
                        if price > 1 and price <= 100:
                            price = price / 100.0
                        return price
                    except:
                        return None
                except Exception:
                    return None

            def fetch_best_ask_from_book(token_id):
                """回退到 /book 接口获取最优卖价"""
                try:
                    url = f"{CLOB_HOST}/book?token_id={token_id}"
                    resp = self._make_request('GET', url)
                    if resp.status_code != 200:
                        return None
                    data = resp.json()
                    asks = None
                    if isinstance(data, dict):
                        asks = data.get('asks') or data.get('ask')
                    if not asks or not isinstance(asks, list):
                        return None
                    best = None
                    for level in asks:
                        try:
                            price = float(level.get('price') or level.get('px') or level.get('ask') or level.get('bestAsk') or level.get('sell'))
                            if price > 1 and price <= 100:
                                price = price / 100.0
                            if price <= 0:
                                continue
                            if best is None or price < best:
                                best = price
                        except Exception:
                            continue
                    return best
                except Exception:
                    return None

            if yes_price is None:
                yes_price = fetch_summary_price(yes_id)
            if no_price is None:
                no_price = fetch_summary_price(no_id)
            if yes_price is None:
                yes_price = fetch_best_ask_from_book(yes_id)
            if no_price is None:
                no_price = fetch_best_ask_from_book(no_id)
            
            return yes_price, no_price
        except Exception as e:
            self._log_error(f"获取价格失败: {e}")
            return None, None
    
    def get_eth_15min_markets(self):
        """获取ETH 15分钟市场（使用代理，只返回剩余时间在0-15分钟之间的市场）"""
        try:
            current_time = time.time()
            interval_start = int(current_time // 900) * 900
            markets = []
            
            # 先按 slug 精准查：上一个 / 当前 / 下一个
            for offset in [-1, 0, 1]:
                timestamp = interval_start + offset * 900
                slug = f"eth-updown-15m-{timestamp}"
                url = f"{GAMMA_API_HOST}/markets/slug/{slug}"
                try:
                    resp = self._make_request('GET', url)
                    if resp.status_code == 200:
                        market = resp.json()
                        if market and not market.get('closed', False):
                            # 计算剩余时间
                            remaining_seconds = self.get_market_remaining_seconds(market)
                            if remaining_seconds is not None:
                                # 只保留剩余时间在0-15分钟（900秒）之间的市场
                                if 0 < remaining_seconds <= 900:
                                    markets.append(market)
                                    self._log_status(f"  找到市场: {slug} (剩余时间: {remaining_seconds:.0f}秒)")
                                # 跳过剩余时间为0或大于15分钟的市场
                except:
                    pass
            
            # 如果 slug 查不到，再用列表筛选
            if not markets:
                url = f"{GAMMA_API_HOST}/markets"
                params = {"limit": 100, "active": "true", "closed": "false"}
                resp = self._make_request('GET', url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    market_list = data if isinstance(data, list) else data.get("data", [])
                    for market in market_list:
                        slug = market.get("slug", "").lower()
                        if "eth-updown-15m-" in slug and not market.get("closed", False):
                            # 计算剩余时间并过滤
                            remaining_seconds = self.get_market_remaining_seconds(market)
                            if remaining_seconds is not None and 0 < remaining_seconds <= 900:
                                markets.append(market)
            
            self._log_status(f"找到 {len(markets)} 个活跃的ETH 15分钟预测市场")
            return markets
        except Exception as e:
            self._log_error(f"获取市场列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_proxy_wallet_address(self, eoa_address):
        """获取EOA地址对应的代理钱包地址"""
        try:
            if not self.w3 or not eoa_address:
                return None
            
            # 尝试从Gnosis Safe工厂查询（MetaMask用户）
            try:
                factory_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(GNOSIS_SAFE_FACTORY),
                    abi=PROXY_FACTORY_ABI
                )
                proxy_address = factory_contract.functions.getProxy(
                    Web3.to_checksum_address(eoa_address)
                ).call()
                if proxy_address and proxy_address != "0x0000000000000000000000000000000000000000":
                    return proxy_address
            except Exception:
                pass
            
            # 尝试从Polymarket代理工厂查询（MagicLink用户）
            try:
                factory_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(POLYMARKET_PROXY_FACTORY),
                    abi=PROXY_FACTORY_ABI
                )
                proxy_address = factory_contract.functions.getProxy(
                    Web3.to_checksum_address(eoa_address)
                ).call()
                if proxy_address and proxy_address != "0x0000000000000000000000000000000000000000":
                    return proxy_address
            except Exception:
                pass
            
            # 尝试使用proxies映射
            try:
                factory_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(GNOSIS_SAFE_FACTORY),
                    abi=PROXY_FACTORY_ABI
                )
                proxy_address = factory_contract.functions.proxies(
                    Web3.to_checksum_address(eoa_address)
                ).call()
                if proxy_address and proxy_address != "0x0000000000000000000000000000000000000000":
                    return proxy_address
            except Exception:
                pass
            
            return None
        except Exception as e:
            self._log_error(f"获取代理钱包地址失败: {e}")
            return None
    
    def get_exchange_address(self):
        """获取Polymarket Exchange合约地址"""
        try:
            url = f"{CLOB_HOST}/exchange"
            resp = self._make_request('GET', url)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    exchange_address = data.get("exchangeAddress") or data.get("exchange")
                    if exchange_address:
                        return exchange_address
            return "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
        except:
            return "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
    
    def check_balance_and_allowance(self, required_amount):
        """检查USDC余额和授权（优先使用L2 API方法，回退到直接查询智能合约）"""
        try:
            if not self.private_key or not self.w3 or not self.account:
                return False, False, 0.0, 0.0, None
            
            # 确定要检查的钱包地址（优先使用配置的代理钱包）
            if self.proxy_wallet_address:
                wallet_address = self.proxy_wallet_address
                self._log_status(f"检查代理钱包余额: {wallet_address}")
            else:
                # 尝试自动检测
                proxy_wallet_address = self.get_proxy_wallet_address(self.account.address)
                if proxy_wallet_address:
                    wallet_address = proxy_wallet_address
                    self._log_status(f"检查代理钱包余额: {wallet_address}")
                else:
                    wallet_address = self.account.address
                    self._log_status(f"检查EOA钱包余额: {wallet_address}")
            
            # 优先使用L2 API方法检查余额
            if self.trading_client:
                try:
                    if hasattr(self.trading_client, 'get_balances'):
                        balances = self.trading_client.get_balances()
                        if balances:
                            usdc_balance = None
                            for balance in balances:
                                if isinstance(balance, dict):
                                    token = balance.get('token') or balance.get('tokenAddress')
                                    if token and token.lower() == USDC_ADDRESS_POLYGON.lower():
                                        usdc_balance = balance.get('balance') or balance.get('amount')
                                        break
                                elif hasattr(balance, 'token'):
                                    if balance.token.lower() == USDC_ADDRESS_POLYGON.lower():
                                        usdc_balance = balance.balance or balance.amount
                                        break
                            
                            if usdc_balance is not None:
                                balance_usdc = float(usdc_balance) / 1e6
                                self._log_status(f"通过L2 API获取USDC余额: {balance_usdc:.2f} USDC")
                                
                                allowance_usdc = 0.0
                                if hasattr(self.trading_client, 'get_allowances'):
                                    try:
                                        allowances = self.trading_client.get_allowances()
                                        if allowances:
                                            for allowance in allowances:
                                                if isinstance(allowance, dict):
                                                    token = allowance.get('token') or allowance.get('tokenAddress')
                                                    if token and token.lower() == USDC_ADDRESS_POLYGON.lower():
                                                        allowance_usdc = float(allowance.get('allowance', 0)) / 1e6
                                                        break
                                                elif hasattr(allowance, 'token'):
                                                    if allowance.token.lower() == USDC_ADDRESS_POLYGON.lower():
                                                        allowance_usdc = float(allowance.allowance or 0) / 1e6
                                                        break
                                    except Exception:
                                        pass
                                
                                has_balance = balance_usdc >= required_amount
                                has_allowance = allowance_usdc >= required_amount
                                return has_balance, has_allowance, balance_usdc, allowance_usdc, wallet_address
                except Exception as e:
                    self._log_error(f"使用L2 API检查余额失败，回退到直接查询: {e}")
            
            # 回退：直接查询智能合约
            self._log_status(f"使用直接查询智能合约方法检查余额...")
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(USDC_ADDRESS_POLYGON),
                abi=USDC_ABI
            )
            
            balance_raw = usdc_contract.functions.balanceOf(
                Web3.to_checksum_address(wallet_address)
            ).call()
            balance_usdc = balance_raw / 1e6
            
            exchange_address = self.get_exchange_address()
            
            allowance_raw = usdc_contract.functions.allowance(
                Web3.to_checksum_address(wallet_address),
                Web3.to_checksum_address(exchange_address)
            ).call()
            allowance_usdc = allowance_raw / 1e6
            
            has_balance = balance_usdc >= required_amount
            has_allowance = allowance_usdc >= required_amount
            
            return has_balance, has_allowance, balance_usdc, allowance_usdc, wallet_address
        except Exception as e:
            self._log_error(f"检查余额和授权失败: {e}")
            import traceback
            traceback.print_exc()
            return False, False, 0.0, 0.0, None
    
    def place_buy_order(self, order_info: Dict, strategy_config: Dict, auto_confirm=True, skip_balance_check=True, verbose=False) -> Optional[Dict]:
        """下单（买入YES或NO份额）- 快速模式，跳过所有不必要的检查"""
        try:
            if not self.private_key:
                return None
            
            # 快速获取订单参数
            token_id = order_info.get('token_id') or order_info.get('yes_token_id') or order_info.get('condition_id')
            best_ask = order_info.get('best_ask') or order_info.get('yes_price')
            order_size = order_info.get('order_size')
            order_amount_usd = order_info.get('order_amount_usd', strategy_config.get('order_amount_usd', 2.0))
            
            if not token_id or best_ask is None:
                return None
            
            # 如果没有指定order_size，根据金额和价格计算
            if order_size is None:
                order_size = order_amount_usd / best_ask
            
            # 检查是否有交易客户端
            if not self.trading_client:
                return None
            
            # 快速下单：直接创建订单，不检查余额、不获取市场信息
            try:
                # 使用默认值
                tick_size = "0.01"
                neg_risk = True
                market_price = 0.99  # 市价单，确保立即成交
                
                order_args = OrderArgs(
                    token_id=token_id,
                    price=market_price,
                    size=order_size,
                    side=BUY,
                )
                
                # 创建订单（快速模式：直接创建，失败才尝试options）
                try:
                    order = self.trading_client.create_order(order_args)
                except Exception:
                    # 如果失败，尝试使用options
                    class SimpleOptions:
                        def __init__(self, tick_size, neg_risk):
                            self.tick_size = tick_size
                            self.neg_risk = neg_risk
                    try:
                        options = SimpleOptions(tick_size, neg_risk)
                        order = self.trading_client.create_order(order_args, options)
                    except Exception:
                        return None
                
                if not order:
                    return None
                
                # 直接提交订单
                result = self.trading_client.post_order(order)
                if result:
                    self._log_status("下单成功")
                else:
                    self._log_error("下单失败")
                return result if result else None
                    
            except Exception:
                return None
                
        except Exception:
            return None
    
    def get_balance_usdc(self) -> float:
        """获取USDC余额
        
        Returns:
            USDC余额（美元），如果查询失败返回0.0
        """
        try:
            if not self.w3:
                return 0.0
            
            # 确定要查询的钱包地址
            if self.proxy_wallet_address:
                wallet_address = self.proxy_wallet_address
            elif self.account:
                wallet_address = self.account.address
            else:
                return 0.0
            
            # 优先使用L2 API方法（如果trading_client已初始化）
            if self.trading_client:
                try:
                    if hasattr(self.trading_client, 'get_balances'):
                        balances = self.trading_client.get_balances()
                        if balances:
                            for balance in balances:
                                if isinstance(balance, dict):
                                    token = balance.get('token') or balance.get('tokenAddress')
                                    if token and token.lower() == USDC_ADDRESS_POLYGON.lower():
                                        usdc_balance = balance.get('balance') or balance.get('amount')
                                        if usdc_balance is not None:
                                            return float(usdc_balance) / 1e6  # USDC是6位小数
                                elif hasattr(balance, 'token'):
                                    if balance.token.lower() == USDC_ADDRESS_POLYGON.lower():
                                        usdc_balance = balance.balance or balance.amount
                                        if usdc_balance is not None:
                                            return float(usdc_balance) / 1e6
                except Exception:
                    pass
            
            # 回退：直接查询智能合约
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(USDC_ADDRESS_POLYGON),
                abi=USDC_ABI
            )
            
            balance_raw = usdc_contract.functions.balanceOf(
                Web3.to_checksum_address(wallet_address)
            ).call()
            
            return balance_raw / 1e6  # USDC是6位小数
            
        except Exception as e:
            self._log_error(f"获取余额失败: {e}")
            return 0.0
    
    def auto_redeem_positions(self) -> bool:
        """自动赎回持仓"""
        try:
            if not self.private_key or not self.w3 or not self.account:
                return False
            
            wallet_address = self.proxy_wallet_address or self.account.address
            
            # 获取可赎回持仓
            url = f"{DATA_API_HOST}/positions"
            params = {"user": wallet_address}
            resp = self._make_request('GET', url, params=params)
            
            if resp.status_code != 200:
                return False
            
            positions_data = resp.json()
            if isinstance(positions_data, dict):
                positions_data = positions_data.get("data", []) or positions_data.get("positions", [])
            
            redeemable_positions = [p for p in positions_data if p.get("redeemable") == True]
            if not redeemable_positions:
                return False
            
            # 按condition_id去重
            unique_condition_ids = set()
            for pos in redeemable_positions:
                condition_id = pos.get("conditionId") or pos.get("condition_id")
                if condition_id:
                    unique_condition_ids.add(str(condition_id))
            
            if not unique_condition_ids:
                return False
            
            # 构建赎回交易
            ctf_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CTF_ADDRESS),
                abi=CTF_ABI
            )
            
            # 使用Builder Relayer执行
            if self.builder_api_key and self.builder_api_secret and self.builder_api_passphrase:
                from py_builder_relayer_client.client import RelayClient
                from py_builder_relayer_client.models import SafeTransaction, OperationType
                from py_builder_signing_sdk.config import BuilderConfig, BuilderApiKeyCreds
                
                builder_config = BuilderConfig(
                    local_builder_creds=BuilderApiKeyCreds(
                        key=self.builder_api_key,
                        secret=self.builder_api_secret,
                        passphrase=self.builder_api_passphrase
                    )
                )
                
                relayer_client = RelayClient(
                    "https://relayer-v2.polymarket.com",
                    137,
                    private_key=self.private_key,
                    builder_config=builder_config
                )
                
                safe_transactions = []
                for condition_id_str in unique_condition_ids:
                    try:
                        if condition_id_str.startswith("0x"):
                            condition_id_bytes = bytes.fromhex(condition_id_str[2:].zfill(64))
                        else:
                            condition_id_bytes = bytes.fromhex(condition_id_str.zfill(64))
                        
                        parent_collection_id = bytes.fromhex("00" * 32)
                        function_data = ctf_contract.functions.redeemPositions(
                            Web3.to_checksum_address(USDC_ADDRESS_POLYGON),
                            parent_collection_id,
                            condition_id_bytes,
                            [1, 2]
                        )._encode_transaction_data()
                        
                        safe_tx = SafeTransaction(
                            to=CTF_ADDRESS,
                            operation=OperationType.Call,
                            data=function_data,
                            value="0"
                        )
                        safe_transactions.append(safe_tx)
                    except:
                        continue
                
                if safe_transactions:
                    response = relayer_client.execute(safe_transactions, "Auto redeem")
                    if response:
                        self._log_status("索取成功")
                        return True
                    else:
                        self._log_error("索取失败")
                        return False
            else:
                # 没有配置 Builder 凭证时，明确打日志，避免看起来“什么都没做”
                self._log_status(
                    "自动赎回跳过：未配置 Builder API 凭证（builder_api_key / secret / passphrase）"
                )
            
            return False
        except Exception as e:
            self._log_error(f"自动赎回失败: {e}")
            return False
    
    def get_positions(self, verbose=False) -> List[Dict]:
        """获取当前持仓（使用Data API的/positions端点）
        
        Returns:
            持仓列表，每个持仓包含 token_id, balance 等信息
        """
        positions = []
        try:
            if not self.w3 or not self.account:
                self._log_status("获取持仓跳过：账号未正确初始化")
                return positions
            
            # 确定要查询的钱包地址（优先使用代理钱包地址）
            wallet_address = None
            
            # 1. 优先使用配置的代理钱包地址
            if self.proxy_wallet_address and self.proxy_wallet_address.strip():
                wallet_address = self.proxy_wallet_address.strip()
                self._log_status(f"使用配置的代理钱包地址: {wallet_address}")
            # 2. 如果没有配置，尝试自动检测代理钱包地址
            elif self.account and self.account.address:
                detected_proxy = self.get_proxy_wallet_address(self.account.address)
                if detected_proxy:
                    wallet_address = detected_proxy
                    self._log_status(f"自动检测到代理钱包地址: {wallet_address}")
                else:
                    # 3. 最后回退到EOA地址（但这不是推荐的方式）
                    wallet_address = self.account.address
                    self._log_status(f"警告: 未找到代理钱包，使用EOA地址: {wallet_address}（可能无法获取持仓）")
            
            if not wallet_address:
                self._log_error("无法确定钱包地址，无法查询持仓")
                return positions
            
            self._log_status(f"查询持仓，使用地址: {wallet_address}")
            
            # 使用Data API获取持仓
            url = f"{DATA_API_HOST}/positions"
            params = {"user": wallet_address}
            resp = self._make_request('GET', url, params=params)
            
            if resp.status_code != 200:
                self._log_error(f"查询持仓失败，HTTP {resp.status_code}")
                try:
                    error_text = resp.text[:200]
                    self._log_error(f"错误响应: {error_text}")
                except:
                    pass
                return positions
            
            positions_data = resp.json()
            
            # 调试：显示原始返回数据
            self._log_status(f"Data API返回数据类型: {type(positions_data)}")
            if isinstance(positions_data, dict):
                self._log_status(f"返回数据键: {list(positions_data.keys())}")
                # 尝试从字典中提取列表
                positions_data = positions_data.get("data", []) or positions_data.get("positions", []) or positions_data.get("results", [])
            elif isinstance(positions_data, list):
                self._log_status(f"返回列表长度: {len(positions_data)}")
            
            if not isinstance(positions_data, list):
                self._log_error(f"返回数据不是列表格式: {type(positions_data)}")
                self._log_error(f"原始数据: {str(positions_data)[:500]}")
                return positions
            
            self._log_status(f"解析后的持仓列表长度: {len(positions_data)}")
            
            # 提取持仓信息
            for idx, pos in enumerate(positions_data):
                if not isinstance(pos, dict):
                    continue
                
                # 尝试多种可能的字段名获取token_id
                token_id = (
                    pos.get("tokenId") or pos.get("token_id") or 
                    pos.get("clobTokenId") or pos.get("clob_token_id") or
                    pos.get("asset") or pos.get("token") or
                    pos.get("id")
                )
                
                # 尝试多种可能的字段名获取余额/数量（优先使用size）
                balance = (
                    pos.get("size") or  # 优先使用size字段
                    pos.get("balance") or pos.get("amount") or 
                    pos.get("quantity") or pos.get("qty") or pos.get("value")
                )
                
                # 如果token_id为空，尝试从其他字段获取
                if not token_id:
                    if "token" in pos and isinstance(pos["token"], dict):
                        token_id = pos["token"].get("id") or pos["token"].get("tokenId")
                    if not token_id:
                        continue
                
                # 如果balance为空或为0，跳过
                if balance is None:
                    if "position" in pos and isinstance(pos["position"], dict):
                        balance = pos["position"].get("balance") or pos["position"].get("size")
                    if balance is None:
                        continue
                
                # 检查balance是否为0或空字符串
                if balance == 0 or balance == "0" or balance == "":
                    continue
                
                try:
                    # 处理余额（可能是字符串或数字）
                    if isinstance(balance, str):
                        balance_float = float(balance)
                    else:
                        balance_float = float(balance)
                    
                    # CTF token通常是18位小数，但如果balance已经很大，可能是原始值
                    if balance_float > 1e10:
                        balance_float = balance_float / 1e18
                    
                    # 过滤掉极小的余额
                    if balance_float > 0.000001:
                        positions.append({
                            'token_id': str(token_id),
                            'balance': balance_float,
                            'balance_raw': balance,
                            'market_id': pos.get("marketId") or pos.get("market_id") or pos.get("market"),
                            'market_question': pos.get("market") or pos.get("question") or pos.get("marketQuestion"),
                            'outcome': pos.get("outcome"),
                            'raw_data': pos
                        })
                        
                except (ValueError, TypeError):
                    continue
            
            return positions
        except Exception as e:
            self._log_error(f"获取持仓失败: {e}")
            import traceback
            traceback.print_exc()
            return positions
    
    def sell_all_positions(self, verbose=False) -> Dict:
        """出售所有持仓（立即卖出）
        
        Args:
            verbose: 是否输出详细日志
            
        Returns:
            {'success': bool, 'sold_count': int, 'failed_count': int, 'message': str}
        """
        try:
            if not self.trading_client:
                return {'success': False, 'sold_count': 0, 'failed_count': 0, 'message': '交易客户端未初始化'}
            
            # 获取持仓
            positions = self.get_positions(verbose=False)
            
            if not positions:
                return {'success': True, 'sold_count': 0, 'failed_count': 0, 'message': '没有持仓'}
            
            sold_count = 0
            failed_count = 0
            
            for pos in positions:
                token_id = pos.get('token_id')
                balance = pos.get('balance')
                
                if not token_id or not balance or balance <= 0:
                    continue
                
                try:
                    # 快速卖出：直接使用固定低价（市价单）
                    market_price = 0.01
                    
                    order_args = OrderArgs(
                        token_id=token_id,
                        price=market_price,
                        size=balance,
                        side=SELL,
                    )
                    
                    # 创建订单
                    order = None
                    try:
                        order = self.trading_client.create_order(order_args)
                    except Exception:
                        # 尝试使用options
                        class SimpleOptions:
                            def __init__(self, tick_size, neg_risk):
                                self.tick_size = tick_size
                                self.neg_risk = neg_risk
                        try:
                            options = SimpleOptions("0.01", True)
                            order = self.trading_client.create_order(order_args, options)
                        except Exception:
                            failed_count += 1
                            continue
                    
                    if not order:
                        failed_count += 1
                        continue
                    
                    # 提交订单
                    result = self.trading_client.post_order(order)
                    
                    # 检查结果
                    if result:
                        if isinstance(result, dict):
                            success = result.get('success', True)
                            error_msg = result.get('errorMsg') or result.get('error_message') or result.get('error')
                            status = result.get('status')
                            if not success or error_msg:
                                failed_count += 1
                            elif status and status.lower() in ['filled', 'open', 'pending']:
                                sold_count += 1
                            elif result.get('orderID') or result.get('order_id') or result.get('id'):
                                sold_count += 1
                            else:
                                failed_count += 1
                        elif hasattr(result, 'success'):
                            if result.success:
                                sold_count += 1
                            else:
                                failed_count += 1
                        else:
                            sold_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    if verbose:
                        self._log_error(f"出售 Token {token_id[:16]}... 时出错: {e}")
            
            if sold_count > 0:
                self._log_status(f"出售成功 {sold_count}/{len(positions)}")
            if failed_count > 0:
                self._log_error(f"出售失败 {failed_count}/{len(positions)}")
            
            return {
                'success': sold_count > 0,
                'sold_count': sold_count,
                'failed_count': failed_count,
                'total_count': len(positions),
                'message': f"出售完成: 成功 {sold_count}, 失败 {failed_count}, 总计 {len(positions)}"
            }
            
        except Exception as e:
            self._log_error(f"出售持仓失败: {e}")
            return {'success': False, 'sold_count': 0, 'failed_count': 0, 'message': f'出售失败: {str(e)}'}
    
    def _get_best_bid_price(self, token_id: str) -> Optional[float]:
        """获取token的最佳买价（bid price）- 使用和买入时获取卖价相同的逻辑，只是获取bid而不是ask
        
        Args:
            token_id: Token ID
            
        Returns:
            最佳买价，如果获取失败返回None
        """
        try:
            # 方法1: 使用get_spreads（和买入时使用相同的客户端方法）
            spreads = None
            if self.client and hasattr(self.client, 'get_spreads'):
                try:
                    spreads = self.client.get_spreads([token_id])
                except Exception:
                    spreads = None
            
            # 从spreads中提取bid价格（和买入时提取ask的逻辑一致）
            def extract_bid(token_id):
                if spreads is None:
                    return None
                # 可能是 dict 映射
                if isinstance(spreads, dict):
                    entry = spreads.get(token_id) or spreads.get(str(token_id))
                elif isinstance(spreads, list):
                    # 可能是列表[{token_id:..., bid:..., ask:...}, ...]
                    entry = None
                    for e in spreads:
                        tid = e.get('token_id') or e.get('tokenId') if isinstance(e, dict) else None
                        if tid and (tid == token_id or str(tid) == str(token_id)):
                            entry = e
                            break
                else:
                    entry = None
                
                if isinstance(entry, dict):
                    val = entry.get('bid') or entry.get('bestBid') or entry.get('buy')
                    try:
                        return float(val) if val is not None else None
                    except Exception:
                        return None
                # 对象形式
                if hasattr(entry, 'bid'):
                    try:
                        return float(entry.bid)
                    except Exception:
                        return None
                return None
            
            bid_price = extract_bid(token_id)
            
            # 方法2: 回退到HTTP Summary接口（和买入时一致）
            def fetch_summary_bid(token_id):
                try:
                    url = f"{CLOB_HOST}/summary?token_id={token_id}"
                    resp = self._make_request('GET', url)
                    if resp.status_code != 200:
                        return None
                    data = resp.json()
                    val = None
                    if isinstance(data, dict):
                        val = data.get('bid') or data.get('bestBid') or data.get('buy')
                    if val is None and isinstance(data, list) and data:
                        entry = data[0]
                        if isinstance(entry, dict):
                            val = entry.get('bid') or entry.get('bestBid') or entry.get('buy')
                    
                    # 标准化价格（和买入时一致）
                    try:
                        price = float(val)
                        if price <= 0:
                            return None
                        if price > 1 and price <= 100:
                            price = price / 100.0
                        return price
                    except:
                        return None
                except Exception:
                    return None
            
            # 方法3: 回退到/book接口获取最优买价（和买入时一致）
            def fetch_best_bid_from_book(token_id):
                """回退到 /book 接口获取最优买价"""
                try:
                    url = f"{CLOB_HOST}/book?token_id={token_id}"
                    resp = self._make_request('GET', url)
                    if resp.status_code != 200:
                        return None
                    data = resp.json()
                    bids = None
                    if isinstance(data, dict):
                        bids = data.get('bids') or data.get('bid')
                    if not bids or not isinstance(bids, list):
                        return None
                    best = None
                    for level in bids:
                        try:
                            price = float(level.get('price') or level.get('px') or level.get('bid') or level.get('bestBid') or level.get('buy'))
                            if price > 1 and price <= 100:
                                price = price / 100.0
                            if price <= 0:
                                continue
                            if best is None or price > best:  # 买价取最高
                                best = price
                        except Exception:
                            continue
                    return best
                except Exception:
                    return None
            
            # 按顺序尝试回退方法（和买入时一致）
            if bid_price is None:
                bid_price = fetch_summary_bid(token_id)
            if bid_price is None:
                bid_price = fetch_best_bid_from_book(token_id)
            
            return bid_price
        except Exception as e:
            self._log_error(f"获取买价失败: {e}")
            return None

