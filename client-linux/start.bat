@echo off
REM PMS 客户端启动脚本 (Windows)
echo ========================================
echo PMS 客户端启动脚本
echo ========================================

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

REM 检查依赖是否安装
if not exist "venv\" (
    echo [提示] 未检测到虚拟环境，正在创建...
    python -m venv venv
    echo [提示] 正在安装依赖...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM 启动客户端
echo [提示] 启动客户端...
python run_client.py

pause

