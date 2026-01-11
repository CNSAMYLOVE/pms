#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""任务调度器"""
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from .account_manager import AccountManager
    from .trading_bot import TradingBot
except ImportError:
    from account_manager import AccountManager
    from trading_bot import TradingBot

class TaskScheduler:
    """任务调度器（管理多个账号的监控任务）"""
    
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        self.bots: Dict[int, TradingBot] = {}  # account_id -> TradingBot
        self.scanner_thread: Optional[threading.Thread] = None  # 单一调度线程
        self.running = False  # 调度线程状态
        # 记录每个市场为哪些账号已经下过单，避免重复: {market_id(str): set(account_id)}
        self.ordered_markets: Dict[str, set] = {}
        # 线程锁，保护 ordered_markets 的并发访问
        self._order_lock = threading.Lock()
        # 线程池配置：并发下单的最大线程数
        self.max_workers = 10  # 可调整：50-200 之间，根据实际情况调整
        self.strategy_config = {
            'order_amount_usd': 2.0,
            'price_percentage_threshold': 0.85,
            'check_time_window_minutes': 2,
            'monitor_interval': 3,
            'redeem_interval': 30 * 60  # 30分钟
        }
    
    def set_strategy_config(self, config: Dict):
        """设置策略配置"""
        self.strategy_config.update(config)
    
    def start_account(self, account_id: int) -> Dict:
        """冷启动账号（只创建bot，不启动监控线程）"""
        account = self.account_manager.get_account(account_id)
        if not account:
            return {'success': False, 'message': '账号不存在'}
        
        if account.get('status') != 'active':
            return {'success': False, 'message': '账号未激活'}
        
        # 如果已经启动，直接返回
        if account_id in self.bots:
            return {'success': True, 'message': '账号已启动'}
        
        # 创建交易机器人（冷启动，不启动监控线程）
        bot = TradingBot(account, proxy_ip=account.get('proxy_ip'))
        self.bots[account_id] = bot
        
        return {'success': True, 'message': '账号冷启动成功（等待手动下单或自动监控启动）'}
    
    def start_auto_monitoring(self) -> Dict:
        """启动自动监控（为所有已启动的账号开始自动运行）"""
        if not self.bots:
            return {'success': False, 'message': '没有已启动的账号'}
        
        # 如果监控线程已经在运行，直接返回
        if self.running and self.scanner_thread and self.scanner_thread.is_alive():
            return {'success': True, 'message': f'自动监控已在运行（{len(self.bots)}个账号）'}
        
        # 启动调度线程（单线程统一扫描/下发）
        self.running = True
        self.scanner_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.scanner_thread.start()
        
        return {'success': True, 'message': f'自动监控已启动（{len(self.bots)}个账号）'}
    
    def stop_account(self, account_id: int) -> Dict:
        """停止账号的监控任务"""
        if account_id not in self.bots:
            return {'success': False, 'message': '账号未运行'}
        
        # 删除该账号的bot与已下单标记
        del self.bots[account_id]
        for mkt, accs in list(self.ordered_markets.items()):
            if account_id in accs:
                accs.discard(account_id)
            if not accs:
                self.ordered_markets.pop(mkt, None)
        
        # 如果没有账号在运行，停止调度线程
        if not self.bots:
            self.running = False
        
        return {'success': True, 'message': '账号停止成功'}
    
    def _monitor_loop(self):
        """单一调度线程：统一获取市场数据，命中后同时下发到所有运行账号"""
        last_redeem_time = 0
        self._log_global("调度线程启动")
        self._log_global(f"策略: 市场结束前倒数{self.strategy_config['check_time_window_minutes']}分钟内，如果UP或DOWN价格 > {self.strategy_config['price_percentage_threshold']*100}%，自动买入")
        self._log_global(f"监控间隔: {self.strategy_config['monitor_interval']}秒")
        self._log_global(f"自动索取: 每{int(self.strategy_config['redeem_interval']/60)}分钟自动索取一次可赎回持仓\n")

        while self.running:
            loop_start_time = time.time()  # 记录循环开始时间
            try:
                # 没有账号运行时，等待
                if not self.bots:
                    time.sleep(self.strategy_config['monitor_interval'])
                    continue

                # 选择一个bot用于拉取市场与打印全局日志（仅数据源/输出，不下单）
                scan_bot = next(iter(self.bots.values()))

                # 自动赎回：并发执行所有账号
                current_time = time.time()
                if current_time - last_redeem_time >= self.strategy_config['redeem_interval']:
                    self._log_global(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行自动索取（所有运行账号，并发执行）...")
                    self._redeem_all_accounts_concurrent()
                    last_redeem_time = current_time

                # 获取市场（统一）
                markets = scan_bot.get_eth_15min_markets()
                if not markets:
                    # 计算剩余等待时间
                    elapsed = time.time() - loop_start_time
                    sleep_time = max(0, self.strategy_config['monitor_interval'] - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    continue

                self._log_global(f"\n监控 {len(markets)} 个市场...\n")

                for i, market in enumerate(markets, 1):
                    try:
                        market_id = market.get("id")
                        market_id_str = str(market_id)
                        market_question = market.get("question", "未知市场")

                        # 获取完整市场数据
                        market_data = scan_bot.fetch_market_detail(market_id)
                        if not market_data:
                            continue

                        # 剩余时间
                        remaining_seconds = scan_bot.get_market_remaining_seconds(market_data)
                        if remaining_seconds is None or remaining_seconds <= 0:
                            self._log_global(f"[{i}] {market_question[:60]}... 跳过（无剩余时间）")
                            continue

                        remaining_minutes = remaining_seconds / 60.0
                        if remaining_minutes > self.strategy_config['check_time_window_minutes']:
                            self._log_global(f"[{i}] {market_question[:60]}... 跳过（不在时间窗口内）")
                            continue

                        # 价格与token
                        yes_token_id, no_token_id = scan_bot.get_yes_no_token_ids(market_id, market_data)
                        if not yes_token_id or not no_token_id:
                            self._log_global(f"[{i}] {market_question[:60]}... 跳过（无法获取token IDs）")
                            continue

                        yes_price, no_price = scan_bot.get_yes_no_prices_via_clob_spreads(market_id, market_data)
                        if yes_price is None or no_price is None:
                            self._log_global(f"[{i}] {market_question[:60]}... 跳过（无法获取价格）")
                            continue

                        up_token_id = yes_token_id
                        down_token_id = no_token_id
                        up_price = yes_price
                        down_price = no_price

                        self._log_global(f"[{i}] {market_question[:60]}...")
                        self._log_global(f"     剩余时间: {remaining_minutes:.2f}分钟 ({remaining_seconds:.0f}秒)")
                        self._log_global(f"     UP价格: {up_price:.4f} ({up_price*100:.2f}%), DOWN价格: {down_price:.4f} ({down_price*100:.2f}%)")

                        price_threshold = self.strategy_config['price_percentage_threshold']
                        should_buy_up = up_price >= price_threshold
                        should_buy_down = down_price >= price_threshold

                        if should_buy_up or should_buy_down:
                            side_label = "涨" if should_buy_up else "跌"
                            price_used = up_price if should_buy_up else down_price
                            token_used = up_token_id if should_buy_up else down_token_id

                            # 仅对未下过单的账号下发指令，避免重复下单
                            eligible_accounts = []
                            for acc_id in self.bots.keys():
                                ordered_set = self.ordered_markets.get(market_id_str, set())
                                if acc_id not in ordered_set:
                                    eligible_accounts.append(acc_id)

                            if not eligible_accounts:
                                self._log_global(f"     - 所有运行账号已为该市场下单，跳过重复下发")
                                continue

                            self._log_global(f"     ✓ {side_label.upper()} 价格 >= {price_threshold*100}%，准备为 {len(eligible_accounts)} 个账号并发买入'{side_label}'...")

                            # 使用线程池并发下单（几乎同时执行）
                            order_amount_usd = self.strategy_config['order_amount_usd']
                            order_size = order_amount_usd / price_used
                            order_info = {
                                "market_id": market_id,
                                "market_question": market_question,
                                "token_id": token_used,
                                "best_ask": price_used,
                                "order_size": order_size,
                                "order_amount_usd": order_amount_usd,
                                "side": "UP" if should_buy_up else "DOWN"
                            }
                            
                            # 统计成功/失败数量
                            success_count = 0
                            fail_count = 0
                            
                            # 使用线程池并发执行下单
                            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                                # 提交所有账号的下单任务
                                futures = {}
                                for acc_id in eligible_accounts:
                                    b = self.bots.get(acc_id)
                                    if not b:
                                        continue
                                    # 提交任务到线程池
                                    future = executor.submit(
                                        self._place_order_for_account,
                                        acc_id, b, order_info, side_label, market_id_str
                                    )
                                    futures[future] = acc_id
                                
                                # 等待所有任务完成（设置超时避免无限等待）
                                timeout = 30  # 30秒超时
                                try:
                                    for future in as_completed(futures, timeout=timeout):
                                        acc_id = futures[future]
                                        try:
                                            success = future.result()
                                            if success:
                                                success_count += 1
                                            else:
                                                fail_count += 1
                                        except Exception as e:
                                            fail_count += 1
                                            bot = self.bots.get(acc_id)
                                            if bot:
                                                bot._log_error(f"下单异常: {e}")
                                except TimeoutError:
                                    # 超时处理：标记未完成的任务为失败
                                    remaining = len(futures) - (success_count + fail_count)
                                    if remaining > 0:
                                        fail_count += remaining
                                        self._log_global(f"     ⚠ 警告: {remaining} 个账号下单超时（{timeout}秒）")
                            
                            # 输出统计结果
                            self._log_global(f"     [并发下单完成] 成功: {success_count}, 失败: {fail_count}, 总计: {len(eligible_accounts)}")
                        else:
                            self._log_global(f"     - 价格未达到阈值（需要 >= {price_threshold*100}%），当前 UP={up_price*100:.2f}% / DOWN={down_price*100:.2f}%")

                    except Exception as e:
                        self._log_global(f"  处理市场时出错: {e}")
                        import traceback
                        traceback.print_exc()
                        continue

                # 计算实际耗时，确保扫描间隔准确
                elapsed = time.time() - loop_start_time
                sleep_time = max(0, self.strategy_config['monitor_interval'] - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except KeyboardInterrupt:
                self._log_global("\n\n监控被用户中断")
                break
            except Exception as e:
                self._log_global(f"监控过程出错: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(self.strategy_config['monitor_interval'])

        self._log_global("调度线程停止")
        self.scanner_thread = None

    def _redeem_all_accounts_concurrent(self):
        """并发执行所有运行账号的自动索取"""
        if not self.bots:
            return
        
        success_count = 0
        fail_count = 0
        
        # 使用线程池并发执行索取
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for acc_id, bot in list(self.bots.items()):
                future = executor.submit(self._redeem_for_account, acc_id, bot)
                futures[future] = acc_id
            
            # 等待所有任务完成
            timeout = 60  # 60秒超时
            try:
                for future in as_completed(futures, timeout=timeout):
                    acc_id = futures[future]
                    try:
                        success = future.result()
                        if success:
                            success_count += 1
                        else:
                            fail_count += 1
                    except Exception as e:
                        fail_count += 1
                        bot = self.bots.get(acc_id)
                        if bot:
                            bot._log_error(f"索取异常: {e}")
            except TimeoutError:
                remaining = len(futures) - (success_count + fail_count)
                if remaining > 0:
                    fail_count += remaining
                    self._log_global(f"     ⚠ 警告: {remaining} 个账号索取超时（{timeout}秒）")
        
        self._log_global(f"     [并发索取完成] 成功: {success_count}, 失败: {fail_count}, 总计: {len(self.bots)}")
    
    def _redeem_for_account(self, acc_id: int, bot: TradingBot) -> bool:
        """为单个账号执行索取（在线程池中执行）"""
        try:
            bot.auto_redeem_positions()
            return True
        except Exception as e:
            bot._log_error(f"索取异常: {e}")
            return False
    
    def _place_order_for_account(self, acc_id: int, bot: TradingBot, order_info: Dict, side_label: str, market_id_str: str) -> bool:
        """为单个账号下单（在线程池中执行）"""
        try:
            result = bot.place_buy_order(
                order_info, 
                self.strategy_config, 
                auto_confirm=True, 
                skip_balance_check=True, 
                verbose=False
            )
            if result:
                bot._log_status(f"     ✓ 买入'{side_label}'成功！")
                # 线程安全地更新已下单标记
                with self._order_lock:
                    ordered_set = self.ordered_markets.get(market_id_str, set())
                    ordered_set.add(acc_id)
                    self.ordered_markets[market_id_str] = ordered_set
                return True
            else:
                bot._log_status(f"     ✗ 买入'{side_label}'失败")
                return False
        except Exception as e:
            bot._log_error(f"下单异常: {e}")
            return False
    
    def _log_global(self, message: str):
        """全局调度日志（不绑定具体账号）"""
        print(f"[调度] {message}")
    
    def get_running_accounts(self) -> List[int]:
        """获取正在运行的账号ID列表"""
        return list(self.bots.keys())
    
    def get_account_status(self, account_id: int) -> Dict:
        """获取账号运行状态"""
        is_running = account_id in self.bots and self.running and self.scanner_thread is not None and self.scanner_thread.is_alive()
        return {
            'account_id': account_id,
            'is_running': is_running,
            'bot_exists': account_id in self.bots
        }

    def get_scheduler_status(self) -> Dict:
        """获取调度线程状态"""
        return {
            'running': self.running and self.scanner_thread is not None and self.scanner_thread.is_alive(),
            'running_accounts': self.get_running_accounts()
        }
    
    def redeem_all_accounts(self) -> Dict:
        """手动触发所有运行账号的索取（并发执行）"""
        if not self.bots:
            return {'success': False, 'message': '没有运行中的账号'}
        
        try:
            self._log_global(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 手动触发索取（所有运行账号，并发执行）...")
            self._redeem_all_accounts_concurrent()
            return {'success': True, 'message': f'已为 {len(self.bots)} 个账号触发索取'}
        except Exception as e:
            return {'success': False, 'message': f'索取失败: {str(e)}'}
    
    def sell_all_accounts(self) -> Dict:
        """手动触发所有运行账号的出售（并发执行）"""
        if not self.bots:
            return {'success': False, 'message': '没有运行中的账号'}
        
        try:
            self._log_global(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 手动触发出售（所有运行账号，并发执行）...")
            return self._sell_all_accounts_concurrent()
        except Exception as e:
            return {'success': False, 'message': f'出售失败: {str(e)}'}
    
    def _sell_all_accounts_concurrent(self) -> Dict:
        """并发执行所有运行账号的出售"""
        if not self.bots:
            return {'success': False, 'sold_count': 0, 'failed_count': 0, 'message': '没有运行中的账号'}
        
        total_sold = 0
        total_failed = 0
        account_results = []
        
        # 使用线程池并发执行出售
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for acc_id, bot in list(self.bots.items()):
                future = executor.submit(self._sell_for_account, acc_id, bot)
                futures[future] = acc_id
            
            # 等待所有任务完成
            timeout = 60  # 60秒超时
            try:
                for future in as_completed(futures, timeout=timeout):
                    acc_id = futures[future]
                    try:
                        result = future.result()
                        if result:
                            sold = result.get('sold_count', 0)
                            failed = result.get('failed_count', 0)
                            total_sold += sold
                            total_failed += failed
                            account_results.append({
                                'account_id': acc_id,
                                'sold_count': sold,
                                'failed_count': failed
                            })
                    except Exception as e:
                        total_failed += 1
                        bot = self.bots.get(acc_id)
                        if bot:
                            bot._log_error(f"出售异常: {e}")
            except TimeoutError:
                remaining = len(futures) - len(account_results)
                if remaining > 0:
                    total_failed += remaining
                    self._log_global(f"     ⚠ 警告: {remaining} 个账号出售超时（{timeout}秒）")
        
        message = f"并发出售完成: 总成功 {total_sold}, 总失败 {total_failed}, 账号数 {len(self.bots)}"
        self._log_global(f"     [并发出售完成] {message}")
        
        return {
            'success': total_sold > 0,
            'sold_count': total_sold,
            'failed_count': total_failed,
            'account_count': len(self.bots),
            'account_results': account_results,
            'message': message
        }
    
    def _sell_for_account(self, acc_id: int, bot: TradingBot) -> Optional[Dict]:
        """为单个账号执行出售（在线程池中执行）"""
        try:
            return bot.sell_all_positions(verbose=True)
        except Exception as e:
            bot._log_error(f"出售异常: {e}")
            return {'success': False, 'sold_count': 0, 'failed_count': 0, 'message': f'出售异常: {str(e)}'}
    
    def manual_place_order(self, market_url: str, account_ids: List[int], side: str = 'YES') -> Dict:
        """手动下单（支持指定市场URL或使用默认15分钟预测）
        
        Args:
            market_url: 市场URL或市场ID（留空则使用默认15分钟预测）
            account_ids: 要下单的账号ID列表
            side: 下单方向，"YES"（绿色/UP）或"NO"（红色/DOWN）
            
        Returns:
            下单结果
        """
        if not account_ids:
            return {'success': False, 'message': '请选择至少一个账号'}
        
        if side not in ['YES', 'NO']:
            return {'success': False, 'message': '下单方向必须是YES或NO'}
        
        # 确保选中的账号都已启动
        missing_accounts = [acc_id for acc_id in account_ids if acc_id not in self.bots]
        if missing_accounts:
            return {'success': False, 'message': f'账号 {missing_accounts} 未启动，请先启动账号'}
        
        try:
            # 选择一个bot用于获取市场数据
            scan_bot = next(iter(self.bots.values()))
            
            # 获取市场信息
            if market_url:
                # 从URL或ID解析市场
                parse_info = self._parse_market_from_url(market_url)
                if not parse_info:
                    return {'success': False, 'message': f'无法解析市场URL或ID: {market_url}'}
                
                market_data = scan_bot.fetch_market_detail(parse_info)
                if not market_data:
                    return {'success': False, 'message': f'无法获取市场详情: {parse_info.get("value", market_url)}'}
                
                market = market_data
            else:
                # 使用默认15分钟预测市场
                markets = scan_bot.get_eth_15min_markets()
                if not markets:
                    return {'success': False, 'message': '未找到15分钟预测市场'}
                market = markets[0]  # 使用第一个市场
                market_data = scan_bot.fetch_market_detail(market.get("id"))
                if not market_data:
                    market_data = market
            
            market_id = market_data.get("id")
            market_id_str = str(market_id)
            market_question = market_data.get("question", "未知市场")
            
            # 获取价格和token
            yes_token_id, no_token_id = scan_bot.get_yes_no_token_ids(market_id, market_data)
            if not yes_token_id or not no_token_id:
                return {'success': False, 'message': '无法获取市场token IDs'}
            
            yes_price, no_price = scan_bot.get_yes_no_prices_via_clob_spreads(market_id, market_data)
            if yes_price is None or no_price is None:
                return {'success': False, 'message': '无法获取市场价格'}
            
            # 根据用户选择的方向下单
            if side == 'YES':
                # YES/UP (绿色)
                side_label = "YES/UP (绿色)"
                price_used = yes_price
                token_used = yes_token_id
                order_side = "UP"
            else:
                # NO/DOWN (红色)
                side_label = "NO/DOWN (红色)"
                price_used = no_price
                token_used = no_token_id
                order_side = "DOWN"
            
            self._log_global(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 手动下单: {market_question[:60]}...")
            self._log_global(f"     市场: {market_question}")
            self._log_global(f"     方向: {side_label}")
            self._log_global(f"     价格: {price_used:.4f} ({price_used*100:.2f}%)")
            self._log_global(f"     账号数: {len(account_ids)}")
            
            # 构建订单信息
            order_amount_usd = self.strategy_config['order_amount_usd']
            order_size = order_amount_usd / price_used
            order_info = {
                "market_id": market_id,
                "market_question": market_question,
                "token_id": token_used,
                "best_ask": price_used,
                "order_size": order_size,
                "order_amount_usd": order_amount_usd,
                "side": order_side
            }
            
            # 并发下单
            success_count = 0
            fail_count = 0
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                for acc_id in account_ids:
                    bot = self.bots.get(acc_id)
                    if not bot:
                        fail_count += 1
                        continue
                    future = executor.submit(
                        self._place_order_for_account,
                        acc_id, bot, order_info, side_label, market_id_str
                    )
                    futures[future] = acc_id
                
                timeout = 30
                try:
                    for future in as_completed(futures, timeout=timeout):
                        acc_id = futures[future]
                        try:
                            success = future.result()
                            if success:
                                success_count += 1
                            else:
                                fail_count += 1
                        except Exception as e:
                            fail_count += 1
                            bot = self.bots.get(acc_id)
                            if bot:
                                bot._log_error(f"下单异常: {e}")
                except TimeoutError:
                    remaining = len(futures) - (success_count + fail_count)
                    if remaining > 0:
                        fail_count += remaining
                        self._log_global(f"     ⚠ 警告: {remaining} 个账号下单超时（{timeout}秒）")
            
            message = f"手动下单完成 ({side_label}): 成功 {success_count}, 失败 {fail_count}, 总计 {len(account_ids)}"
            self._log_global(f"     [手动下单完成] {message}")
            
            return {
                'success': success_count > 0,
                'success_count': success_count,
                'fail_count': fail_count,
                'total_count': len(account_ids),
                'side': side_label,
                'message': message
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self._log_global(f"手动下单异常: {e}\n{error_detail}")
            return {'success': False, 'message': f'手动下单失败: {str(e)}'}
    
    def _parse_market_from_url(self, market_url: str) -> Optional[Dict]:
        """从URL或ID解析市场信息
        
        Args:
            market_url: 市场URL（如 https://polymarket.com/event/xxx）或市场ID/slug
            
        Returns:
            dict: {'type': 'slug'|'id', 'value': slug或id字符串} 或 None
        """
        if not market_url:
            return None
        
        import re
        
        # 如果是URL，提取slug或ID
        if 'polymarket.com' in market_url or 'gamma-api.polymarket.com' in market_url:
            # 匹配 /event/xxx（提取slug）
            match = re.search(r'/event/([^/?]+)', market_url)
            if match:
                slug = match.group(1)
                return {'type': 'slug', 'value': slug}
            
            # 匹配 /markets/xxx
            match = re.search(r'/markets/([^/?]+)', market_url)
            if match:
                value = match.group(1)
                # 判断是数字ID还是slug
                if value.isdigit():
                    return {'type': 'id', 'value': value}
                else:
                    return {'type': 'slug', 'value': value}
            
            # 匹配市场ID（纯数字）
            match = re.search(r'/(\d+)/?', market_url)
            if match:
                return {'type': 'id', 'value': match.group(1)}
        
        # 如果直接是ID或slug，判断类型
        value = market_url.strip()
        if value.isdigit():
            return {'type': 'id', 'value': value}
        else:
            return {'type': 'slug', 'value': value}

