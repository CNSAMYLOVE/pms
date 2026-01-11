#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""客户端启动脚本"""
import sys
import os

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入app模块
from app import app, CLIENT_HOST, CLIENT_PORT, CLIENT_DEBUG, init_client_config, auto_register_to_server

if __name__ == '__main__':
    # 导入心跳函数
    from app import start_heartbeat_thread
    
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

