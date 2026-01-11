#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Flask后端API"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
try:
    from .account_manager import AccountManager
    from .task_scheduler import TaskScheduler
    from .config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
except ImportError:
    from account_manager import AccountManager
    from task_scheduler import TaskScheduler
    from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 初始化管理器
account_manager = AccountManager()
task_scheduler = TaskScheduler(account_manager)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

# ========== 账号管理API ==========

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """获取所有账号（包含实时余额）"""
    # 为了避免频繁调用外部节点/API，这里只返回数据库中缓存的余额
    # 实时刷新余额请使用单账号接口 /api/accounts/<id>/balance
    accounts = account_manager.get_all_accounts()
    return jsonify({'success': True, 'data': accounts})

@app.route('/api/accounts', methods=['POST'])
def add_account():
    """添加账号"""
    data = request.json
    data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result = account_manager.add_account(data)
    return jsonify(result)

@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    """更新账号"""
    data = request.json
    result = account_manager.update_account(account_id, data)
    return jsonify(result)

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """删除账号"""
    result = account_manager.delete_account(account_id)
    return jsonify(result)

@app.route('/api/accounts/<int:account_id>/status', methods=['PUT'])
def update_account_status(account_id):
    """更新账号状态"""
    data = request.json
    status = data.get('status', 'active')
    result = account_manager.update_account_status(account_id, status)
    return jsonify(result)

@app.route('/api/accounts/<int:account_id>/balance', methods=['GET'])
def get_account_balance(account_id):
    """获取账号余额"""
    account = account_manager.get_account(account_id)
    if not account:
        return jsonify({'success': False, 'message': '账号不存在'})
    
    try:
        from trading_bot import TradingBot
        bot = TradingBot(account, proxy_ip=account.get('proxy_ip'))
        balance = bot.get_balance_usdc()
        account_manager.update_account_balance(account_id, balance)
        return jsonify({'success': True, 'balance': balance})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询余额失败: {str(e)}'})

# ========== 任务调度API ==========

@app.route('/api/tasks/start/<int:account_id>', methods=['POST'])
def start_task(account_id):
    """冷启动账号（只创建bot，不启动监控线程）"""
    result = task_scheduler.start_account(account_id)
    return jsonify(result)

@app.route('/api/tasks/start_auto_monitoring', methods=['POST'])
def start_auto_monitoring():
    """启动自动监控（为所有已启动的账号开始自动运行）"""
    result = task_scheduler.start_auto_monitoring()
    return jsonify(result)

@app.route('/api/tasks/stop/<int:account_id>', methods=['POST'])
def stop_task(account_id):
    """停止账号任务"""
    result = task_scheduler.stop_account(account_id)
    return jsonify(result)

@app.route('/api/tasks/running', methods=['GET'])
def get_running_tasks():
    """获取正在运行的任务"""
    running_accounts = task_scheduler.get_running_accounts()
    return jsonify({'success': True, 'data': running_accounts})

@app.route('/api/tasks/status/<int:account_id>', methods=['GET'])
def get_task_status(account_id):
    """获取任务状态"""
    status = task_scheduler.get_account_status(account_id)
    return jsonify({'success': True, 'data': status})

@app.route('/api/tasks/scheduler_status', methods=['GET'])
def get_scheduler_status():
    """获取调度线程总体状态"""
    status = task_scheduler.get_scheduler_status()
    return jsonify({'success': True, 'data': status})

@app.route('/api/strategy/config', methods=['GET'])
def get_strategy_config():
    """获取策略配置"""
    return jsonify({'success': True, 'data': task_scheduler.strategy_config})

@app.route('/api/strategy/config', methods=['PUT'])
def update_strategy_config():
    """更新策略配置"""
    data = request.json
    task_scheduler.set_strategy_config(data)
    return jsonify({'success': True, 'message': '配置更新成功'})

@app.route('/api/tasks/redeem_all', methods=['POST'])
def redeem_all_accounts():
    """一键索取所有运行账号的持仓"""
    result = task_scheduler.redeem_all_accounts()
    return jsonify(result)

@app.route('/api/tasks/sell_all', methods=['POST'])
def sell_all_accounts():
    """一键出售所有运行账号的持仓"""
    result = task_scheduler.sell_all_accounts()
    return jsonify(result)

@app.route('/api/tasks/manual_order', methods=['POST'])
def manual_place_order():
    """手动一键下单（支持指定市场URL或使用默认15分钟预测）"""
    data = request.json
    market_url = data.get('market_url', '').strip()
    account_ids = data.get('account_ids', [])
    side = data.get('side', '').upper()  # "YES" 或 "NO"
    
    if not account_ids:
        return jsonify({'success': False, 'message': '请选择至少一个账号'})
    
    if side not in ['YES', 'NO']:
        return jsonify({'success': False, 'message': '请选择下单方向（YES或NO）'})
    
    result = task_scheduler.manual_place_order(market_url, account_ids, side)
    return jsonify(result)

if __name__ == '__main__':
    print(f"启动服务器: http://{FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)

