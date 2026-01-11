#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PMS 客户端启动脚本（部署版本）
用于在服务器上启动客户端
"""
import sys
import os

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
client_dir = os.path.join(current_dir, 'client')

# 添加客户端目录到路径（command_executor.py会自己处理pmq路径）
sys.path.insert(0, client_dir)
sys.path.insert(0, current_dir)

# 导入并运行客户端
if __name__ == '__main__':
    # 切换到客户端目录
    os.chdir(client_dir)
    
    # 确保client_dir在sys.path最前面（防止pmq/app.py被优先导入）
    if client_dir in sys.path:
        sys.path.remove(client_dir)
    sys.path.insert(0, client_dir)
    
    # 导入客户端应用
    from app import app, CLIENT_HOST, CLIENT_PORT, CLIENT_DEBUG, init_client_config, auto_register_to_server
    from app import start_heartbeat_thread
    
    # 初始化配置（首次运行会提示用户输入）
    CLIENT_ID, SERVER_URL = init_client_config()
    
    print("=" * 50)
    print(f"PMS 客户端启动: {CLIENT_ID}")
    print("=" * 50)
    print(f"监听地址: http://{CLIENT_HOST}:{CLIENT_PORT}")
    print(f"服务端URL: {SERVER_URL}")
    print(f"工作目录: {current_dir}")
    print("=" * 50)
    
    # 启动时自动注册
    try:
        auto_register_to_server()
    except Exception as e:
        print(f"[警告] 自动注册失败: {e}")
        print("[提示] 客户端仍会继续运行，但需要在服务端手动注册")
    
    # 启动心跳线程（定期向服务端发送心跳，保持在线状态）
    try:
        start_heartbeat_thread()
        print("[客户端] 心跳线程已启动（每30秒发送一次）")
    except Exception as e:
        print(f"[警告] 心跳线程启动失败: {e}")
    
    print("=" * 50)
    print("[客户端] 开始监听请求...")
    print("=" * 50)
    
    # 运行 Flask 应用
    app.run(host=CLIENT_HOST, port=CLIENT_PORT, debug=CLIENT_DEBUG)

