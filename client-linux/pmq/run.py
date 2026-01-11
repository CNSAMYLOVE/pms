#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""启动脚本"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG

if __name__ == '__main__':
    print("=" * 50)
    print("Polymarket 多账号群控系统")
    print("=" * 50)
    print(f"服务器地址: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"访问地址: http://localhost:{FLASK_PORT}")
    print("=" * 50)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)









