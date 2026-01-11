#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""客户端Flask应用"""
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

from command_executor import CommandExecutor

# 配置
CLIENT_HOST = "0.0.0.0"  # 监听所有网络接口，允许外部访问
CLIENT_PORT = 9000
CLIENT_DEBUG = False

app = Flask(__name__)
CORS(app)

# 导入配置管理器
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from config_manager import ConfigManager

config_manager = ConfigManager()

# 尝试从配置文件加载（如果存在），否则等待用户输入
_initial_client_id = config_manager.get_client_id() or os.environ.get('PMS_CLIENT_ID', '')
_initial_server_url = config_manager.get_server_url() or os.environ.get('PMS_SERVER_URL', 'http://101.32.22.185:8000')

# 如果配置文件中已有客户端ID，直接初始化；否则等待用户输入
if _initial_client_id:
    CLIENT_ID = _initial_client_id
    SERVER_URL = _initial_server_url
    executor = CommandExecutor(CLIENT_ID)
    print(f"[客户端] 从配置文件加载: ID={CLIENT_ID}, Server={SERVER_URL}")
else:
    CLIENT_ID = None
    SERVER_URL = None
    executor = None

def init_client_config():
    """初始化客户端配置（首次运行时提示用户输入）"""
    global CLIENT_ID, SERVER_URL, executor
    
    # 如果已经初始化，直接返回
    if CLIENT_ID and executor:
        return CLIENT_ID, SERVER_URL
    
    # 检查配置文件是否存在
    has_config = config_manager.has_config()
    
    # 获取客户端ID（优先从配置文件，其次环境变量，最后提示用户输入）
    CLIENT_ID = config_manager.get_client_id() or os.environ.get('PMS_CLIENT_ID', '')
    
    # 如果还没有客户端ID，提示用户输入（仅在首次运行时）
    if not CLIENT_ID:
        print("=" * 50)
        print("首次运行，需要设置客户端ID")
        print("=" * 50)
        print("提示: 只需要输入客户端ID即可，URL会自动检测")
        print("=" * 50)
        while True:
            client_id = input("请输入客户端ID（例如: client-1）: ").strip()
            if client_id:
                config_manager.set_client_id(client_id)
                CLIENT_ID = client_id
                print(f"✓ 客户端ID已保存: {CLIENT_ID}")
                break
            else:
                print("客户端ID不能为空，请重新输入")
    
    # 获取服务端URL（优先从配置文件，其次环境变量，最后使用固定默认值）
    SERVER_URL = config_manager.get_server_url() or os.environ.get('PMS_SERVER_URL', 'http://101.32.22.185:8000')
    
    # 如果配置文件中的服务端URL是旧的localhost，自动更新为固定IP
    saved_server_url = config_manager.get('server_url', '')
    if not saved_server_url or saved_server_url == 'http://localhost:8000':
        SERVER_URL = 'http://101.32.22.185:8000'
        config_manager.set_server_url(SERVER_URL)
        if not has_config:
            print("[客户端] 服务端URL已自动设置为: {}".format(SERVER_URL))
    
    # 自动获取并保存客户端公网IP到配置文件
    # 如果配置文件中没有，则自动获取并保存
    saved_client_ip = config_manager.get_client_ip()
    if not saved_client_ip:
        # 自动获取公网IP并保存
        try:
            import requests
            import socket
            public_ip_apis = [
                'https://api.ipify.org?format=text',
                'https://ifconfig.me/ip',
                'https://ipinfo.io/ip',
                'https://icanhazip.com'
            ]
            for api_url in public_ip_apis:
                try:
                    response = requests.get(api_url, timeout=3)
                    if response.status_code == 200:
                        public_ip = response.text.strip()
                        # 验证是否是有效的IP地址
                        try:
                            socket.inet_aton(public_ip)
                            config_manager.set_client_ip(public_ip)
                            print("[客户端] 自动获取并保存客户端公网IP: {}".format(public_ip))
                            break
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            print("[客户端] 无法自动获取公网IP: {}".format(str(e)))
    
    # 初始化命令执行器（如果还没有初始化）
    if not executor:
        executor = CommandExecutor(CLIENT_ID)
    
    return CLIENT_ID, SERVER_URL

# 在模块加载时不自动初始化，由run.py调用

def get_client_url():
    """获取客户端URL（自动检测或手动配置）"""
    try:
        import socket
        
        # 方法1: 尝试从配置文件获取（优先级最高）
        config_client_ip = config_manager.get_client_ip()
        if config_client_ip:
            client_url = "http://{}:{}".format(config_client_ip, CLIENT_PORT)
            print("[客户端] 使用配置文件中的IP: {}".format(client_url))
            return client_url
        
        # 方法2: 尝试从环境变量获取
        env_ip = os.environ.get('PMS_CLIENT_IP')
        if env_ip:
            client_url = "http://{}:{}".format(env_ip, CLIENT_PORT)
            print("[客户端] 使用环境变量中的IP: {}".format(client_url))
            return client_url
        
        # 方法3: 尝试通过外部API获取公网IP（优先）
        public_ip = None
        try:
            import requests
            public_ip_apis = [
                'https://api.ipify.org?format=text',
                'https://ifconfig.me/ip',
                'https://ipinfo.io/ip',
                'https://icanhazip.com'
            ]
            for api_url in public_ip_apis:
                try:
                    response = requests.get(api_url, timeout=3)
                    if response.status_code == 200:
                        public_ip = response.text.strip()
                        # 验证是否是有效的IP地址
                        try:
                            socket.inet_aton(public_ip)
                            print("[客户端] 通过API获取到公网IP: {}".format(public_ip))
                            break
                        except:
                            public_ip = None
                except:
                    continue
        except Exception as e:
            print("[客户端] 无法通过API获取公网IP: {}".format(str(e)))
        
        # 方法4: 尝试连接外部服务获取本机IP（内网IP，作为备选）
        local_ip = None
        if not public_ip:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    # 连接到一个远程地址（不会实际发送数据）
                    s.connect(('8.8.8.8', 80))
                    local_ip = s.getsockname()[0]
                except Exception as e:
                    print("[客户端] 无法通过连接外部服务获取IP: {}".format(str(e)))
                finally:
                    s.close()
            except Exception as e:
                print("[客户端] 创建socket失败: {}".format(str(e)))
            
            # 方法5: 尝试通过主机名获取
            if not local_ip or local_ip == '127.0.0.1':
                try:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    if local_ip == '127.0.0.1':
                        local_ip = None
                except Exception as e:
                    print("[客户端] 无法通过主机名获取IP: {}".format(str(e)))
        
        # 优先使用公网IP，如果没有则使用内网IP
        client_ip = public_ip or local_ip
        
        # 如果获取到公网IP，自动保存到配置文件
        if public_ip:
            saved_ip = config_manager.get_client_ip()
            if saved_ip != public_ip:
                config_manager.set_client_ip(public_ip)
                print("[客户端] 公网IP已自动保存到配置文件: {}".format(public_ip))
        
        # 如果还是没获取到，使用默认值
        if not client_ip:
            client_ip = '127.0.0.1'
            print("[客户端] 警告: 无法自动检测IP，使用默认值 {}".format(client_ip))
            print("[客户端] 提示: 可以通过以下方式手动设置客户端IP:")
            print("[客户端]   1. 环境变量: export PMS_CLIENT_IP=your-ip")
            print("[客户端]   2. 配置文件: 修改 client/data/client/config.json 中的 client_ip")
        elif not public_ip:
            print("[客户端] 警告: 只能获取到内网IP: {}".format(client_ip))
            print("[客户端] ⚠ 注意: 如果服务端无法访问此URL，请在配置文件中设置正确的客户端公网IP")
        
        client_url = "http://{}:{}".format(client_ip, CLIENT_PORT)
        print("[客户端] 检测到的客户端URL: {}".format(client_url))
        return client_url
    except Exception as e:
        print("[客户端] 获取客户端URL异常: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        client_url = "http://127.0.0.1:{}".format(CLIENT_PORT)
        print("[客户端] 使用默认URL: {}".format(client_url))
        return client_url

# 客户端启动时自动注册到服务端
def auto_register_to_server():
    """客户端首次运行时自动注册到服务端"""
    try:
        import requests
        
        if not CLIENT_ID:
            print(f"[客户端] 警告: 客户端ID未设置，跳过自动注册")
            return False
        
        client_url = get_client_url()
        print(f"[客户端] 准备注册到服务端，客户端URL: {client_url}")
        
        # 如果配置了SERVER_URL，使用配置的URL
        if SERVER_URL:
            register_url = f"{SERVER_URL}/api/clients/auto_register"
            payload = {
                'client_id': CLIENT_ID,
                'client_url': client_url
            }
            print(f"[客户端] 向服务端注册: {register_url}")
            try:
                response = requests.post(register_url, json=payload, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"[客户端] ✓ 已自动注册到服务端: {SERVER_URL}")
                        print(f"[客户端]   客户端ID: {CLIENT_ID}")
                        print(f"[客户端]   客户端URL: {client_url}")
                        if result.get('is_new'):
                            print(f"[客户端]   这是首次注册")
                        else:
                            print(f"[客户端]   客户端已存在，已更新URL")
                        return True
                    else:
                        print(f"[客户端] ✗ 注册失败: {result.get('message', '未知错误')}")
                        return False
                else:
                    print(f"[客户端] ✗ 注册失败: HTTP {response.status_code}")
                    try:
                        error_text = response.text[:200]
                        print(f"[客户端]   错误详情: {error_text}")
                    except:
                        pass
                    return False
            except requests.exceptions.ConnectionError as e:
                print(f"[客户端] ✗ 无法连接到服务端: {SERVER_URL}")
                print(f"[客户端]   错误: {e}")
                print(f"[客户端]   请确保服务端正在运行")
                return False
            except requests.exceptions.Timeout as e:
                print(f"[客户端] ✗ 连接服务端超时: {SERVER_URL}")
                print(f"[客户端]   请检查网络连接")
                return False
            except Exception as e:
                print(f"[客户端] ✗ 自动注册失败: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print(f"[客户端] 警告: 服务端URL未设置，跳过自动注册")
            return False
    except Exception as e:
        print(f"[客户端] 自动注册异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_heartbeat_thread():
    """启动心跳线程（定期向服务端发送心跳）"""
    import threading
    import time
    import requests
    
    def heartbeat_loop():
        while True:
            try:
                # 确保CLIENT_ID和SERVER_URL已初始化
                current_client_id = CLIENT_ID
                current_server_url = SERVER_URL
                
                if current_client_id and current_server_url:
                    client_url = get_client_url()
                    heartbeat_url = f"{current_server_url}/api/clients/heartbeat"
                    payload = {
                        'client_id': current_client_id,
                        'client_url': client_url
                    }
                    try:
                        response = requests.post(heartbeat_url, json=payload, timeout=5)
                        if response.status_code == 200:
                            result = response.json()
                            if not result.get('success'):
                                print(f"[客户端] 心跳失败: {result.get('message')}")
                    except Exception as e:
                        # 静默失败，不打印错误（避免日志过多）
                        pass
            except:
                pass
            
            # 每30秒发送一次心跳
            time.sleep(30)
    
    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    return heartbeat_thread

@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'success': True,
        'client_id': CLIENT_ID or '未初始化',
        'status': 'online',
        'accounts_count': len(executor.accounts) if executor else 0
    })

@app.route('/api/command', methods=['POST'])
def execute_command():
    """执行命令
    
    Body:
        {
            "command": "place_order" | "sell" | "redeem" | "get_balance" | "load_account" | "unload_account",
            "params": {...}
        }
    """
    global CLIENT_ID, SERVER_URL, executor
    
    try:
        print(f"[客户端] 收到命令请求: {request.json}")
        
        # 如果executor未初始化，尝试初始化
        if not executor:
            try:
                # 尝试从配置加载
                if not CLIENT_ID:
                    CLIENT_ID = config_manager.get_client_id() or os.environ.get('PMS_CLIENT_ID', '')
                if CLIENT_ID:
                    executor = CommandExecutor(CLIENT_ID)
                    print(f"[客户端] Executor初始化成功: ID={CLIENT_ID}")
                else:
                    error_msg = '客户端未初始化，请先设置客户端ID'
                    print(f"[客户端] {error_msg}")
                    return jsonify({'success': False, 'message': error_msg})
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"[客户端] Executor初始化失败: {error_detail}")
                return jsonify({'success': False, 'message': f'客户端初始化失败: {str(e)}'})
        
        data = request.json
        if not data:
            error_msg = '缺少请求数据'
            print(f"[客户端] {error_msg}")
            return jsonify({'success': False, 'message': error_msg})
        
        command = data.get('command')
        params = data.get('params', {})
        
        print(f"[客户端] 执行命令: {command}, 参数: {params}")
        
        try:
            if command == 'place_order':
                result = executor.execute_place_order(params)
            elif command == 'sell':
                result = executor.execute_sell(params)
            elif command == 'redeem':
                result = executor.execute_redeem(params)
            elif command == 'get_balance':
                result = executor.execute_get_balance(params)
            elif command == 'load_account':
                account_data = params.get('account_data')
                if account_data:
                    try:
                        success = executor.load_account(account_data)
                        if success:
                            result = {'success': True, 'message': f'账号加载成功: ID={account_data.get("id")}'}
                        else:
                            result = {'success': False, 'message': f'账号加载失败: ID={account_data.get("id")}'}
                    except Exception as e:
                        import traceback
                        error_detail = traceback.format_exc()
                        print(f"[客户端] 加载账号异常: {error_detail}")
                        result = {'success': False, 'message': f'账号加载异常: {str(e)}'}
                else:
                    result = {'success': False, 'message': '缺少账号数据'}
            elif command == 'unload_account':
                account_id = params.get('account_id')
                if account_id:
                    success = executor.unload_account(account_id)
                    result = {'success': success, 'message': '账号卸载成功' if success else '账号卸载失败'}
                else:
                    result = {'success': False, 'message': '缺少账号ID'}
            else:
                result = {'success': False, 'message': f'未知命令: {command}'}
        
            return jsonify(result)
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[客户端] 执行命令异常: {error_detail}")
            return jsonify({'success': False, 'message': f'执行命令失败: {str(e)}'})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[客户端] 处理请求异常: {error_detail}")
        return jsonify({'success': False, 'message': f'处理请求失败: {str(e)}'})

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """获取已加载的账号列表"""
    if not executor:
        return jsonify({'success': False, 'message': '客户端未初始化'})
    return jsonify({
        'success': True,
        'account_ids': executor.get_account_ids()
    })

if __name__ == '__main__':
    # 初始化配置（首次运行会提示用户输入）
    CLIENT_ID, SERVER_URL = init_client_config()
    
    print("=" * 50)
    print(f"PMS 客户端启动: {CLIENT_ID}")
    print("=" * 50)
    print(f"监听地址: http://{CLIENT_HOST}:{CLIENT_PORT}")
    print(f"服务端URL: {SERVER_URL}")
    print("=" * 50)
    
    # 启动时自动注册
    auto_register_to_server()
    
    # 启动心跳线程（定期向服务端发送心跳，保持在线状态）
    start_heartbeat_thread()
    print("[客户端] 心跳线程已启动（每30秒发送一次）")
    
    print("=" * 50)
    app.run(host=CLIENT_HOST, port=CLIENT_PORT, debug=CLIENT_DEBUG)

