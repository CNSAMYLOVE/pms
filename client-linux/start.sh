#!/bin/bash
# PMS 客户端启动脚本 (Linux/Mac)

echo "========================================"
echo "PMS 客户端启动脚本"
echo "========================================"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.7+"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "[提示] 未检测到虚拟环境，正在创建..."
    python3 -m venv venv
    echo "[提示] 正在安装依赖..."
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 启动客户端
echo "[提示] 启动客户端..."
python3 run_client.py

