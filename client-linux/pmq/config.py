#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""配置文件"""
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据存储目录
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 数据文件路径
ACCOUNTS_FILE = os.path.join(DATA_DIR, 'accounts.json')
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')
POSITIONS_FILE = os.path.join(DATA_DIR, 'positions.json')

# Polymarket API配置
CLOB_HOST = "https://clob.polymarket.com"
GAMMA_API_HOST = "https://gamma-api.polymarket.com"
DATA_API_HOST = "https://data-api.polymarket.com"
CHAIN_ID = 137  # Polygon mainnet

# 合约地址
USDC_ADDRESS_POLYGON = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
GNOSIS_SAFE_FACTORY = "0xaacfeea03eb1561c4e67d661e40682bd20e3541b"
POLYMARKET_PROXY_FACTORY = "0xaB45c5A4B0c941a2F231C04C3f49182e1A254052"

# 默认策略参数
DEFAULT_ORDER_AMOUNT_USD = 2.0
DEFAULT_PRICE_PERCENTAGE_THRESHOLD = 0.85
DEFAULT_CHECK_TIME_WINDOW_MINUTES = 2
DEFAULT_MONITOR_INTERVAL = 3

# Flask配置
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
# 生产运行必须为 False，避免 Flask 调试自动重启导致调度线程和实例被杀掉
FLASK_DEBUG = False


