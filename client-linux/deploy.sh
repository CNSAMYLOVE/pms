#!/bin/bash
# PMS 客户端一键部署脚本（CentOS + Conda）
# 使用方法: bash deploy.sh [安装目录] [客户端ID]

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
GITHUB_REPO="https://github.com/CNSAMYLOVE/pms.git"
GIT_COMMIT="947a3942804b3080b274d9375d3458fe2ca1bb9b"
INSTALL_DIR="${1:-/opt/pms_client}"
CLIENT_ID="${2:-client-1}"
SERVER_URL="http://101.32.22.185:8000"
CONDA_ENV_NAME="pms-client"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PMS 客户端一键部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then 
   echo -e "${YELLOW}[警告] 不建议使用root用户运行，建议使用普通用户${NC}"
   read -p "是否继续？(y/n) " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
   fi
fi

# 步骤1: 检查并安装Miniconda
echo -e "${GREEN}[步骤1/7] 检查Miniconda安装...${NC}"
if ! command -v conda &> /dev/null; then
    echo -e "${YELLOW}未检测到Conda，开始安装Miniconda...${NC}"
    
    # 检测系统架构
    ARCH=$(uname -m)
    if [ "$ARCH" != "x86_64" ]; then
        echo -e "${RED}不支持的架构: $ARCH${NC}"
        exit 1
    fi
    
    # 检测GLIBC版本
    GLIBC_VERSION=$(ldd --version 2>&1 | head -n1 | grep -oE '[0-9]+\.[0-9]+' | head -n1)
    echo -e "${GREEN}检测到GLIBC版本: ${GLIBC_VERSION}${NC}"
    
    # 根据GLIBC版本选择Miniconda版本
    if [ -n "$GLIBC_VERSION" ]; then
        # 使用bc或者awk来比较版本（如果没有bc，使用awk）
        GLIBC_MAJOR=$(echo $GLIBC_VERSION | cut -d. -f1)
        GLIBC_MINOR=$(echo $GLIBC_VERSION | cut -d. -f2)
        
        if [ "$GLIBC_MAJOR" -lt 2 ] || ([ "$GLIBC_MAJOR" -eq 2 ] && [ "$GLIBC_MINOR" -lt 28 ]); then
            echo -e "${YELLOW}检测到GLIBC版本较低（${GLIBC_VERSION}），使用兼容的Miniconda版本...${NC}"
            # 使用兼容GLIBC 2.17的旧版本Miniconda (py39_4.9.2)
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py39_4.9.2-Linux-x86_64.sh"
        else
            echo -e "${GREEN}GLIBC版本满足要求，使用最新版本Miniconda...${NC}"
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        fi
    else
        # 如果无法检测GLIBC版本，默认使用旧版本（更安全）
        echo -e "${YELLOW}无法检测GLIBC版本，使用兼容版本Miniconda...${NC}"
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py39_4.9.2-Linux-x86_64.sh"
    fi
    
    # 下载并安装
    cd /tmp
    echo -e "${GREEN}下载Miniconda: $MINICONDA_URL${NC}"
    wget -q $MINICONDA_URL -O miniconda.sh || {
        echo -e "${RED}下载失败，尝试备用URL...${NC}"
        # 备用：使用py38版本（更老的兼容版本）
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py38_4.9.2-Linux-x86_64.sh"
        wget -q $MINICONDA_URL -O miniconda.sh || {
            echo -e "${RED}Miniconda下载失败，请检查网络连接${NC}"
            exit 1
        }
    }
    
    echo -e "${GREEN}安装Miniconda...${NC}"
    bash miniconda.sh -b -p $HOME/miniconda3 || {
        echo -e "${RED}Miniconda安装失败${NC}"
        rm -f miniconda.sh
        exit 1
    }
    rm miniconda.sh
    
    # 初始化conda
    $HOME/miniconda3/bin/conda init bash 2>/dev/null || true
    source $HOME/miniconda3/etc/profile.d/conda.sh
    
    echo -e "${GREEN}Miniconda安装完成！${NC}"
    echo -e "${YELLOW}请重新运行此脚本，或执行: source ~/.bashrc${NC}"
    exit 0
else
    echo -e "${GREEN}Conda已安装: $(conda --version)${NC}"
    # 初始化conda（如果脚本中未初始化）
    if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source $HOME/miniconda3/etc/profile.d/conda.sh
    elif [ -f "$HOME/.conda/etc/profile.d/conda.sh" ]; then
        source $HOME/.conda/etc/profile.d/conda.sh
    fi
fi
echo ""

# 步骤2: 创建安装目录
echo -e "${GREEN}[步骤2/7] 创建安装目录...${NC}"
sudo mkdir -p "$INSTALL_DIR"
sudo chown -R $USER:$USER "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo -e "${GREEN}安装目录: $INSTALL_DIR${NC}"
echo ""

# 步骤3: 克隆或更新代码
echo -e "${GREEN}[步骤3/7] 克隆/更新代码...${NC}"
if [ -d "pm" ]; then
    echo -e "${YELLOW}检测到现有代码，更新中...${NC}"
    cd pm
    git fetch origin
    git checkout $GIT_COMMIT
    cd ..
else
    echo -e "${GREEN}克隆代码仓库...${NC}"
    git clone $GITHUB_REPO pm
    cd pm
    git checkout $GIT_COMMIT
    cd ..
fi
echo -e "${GREEN}代码就绪${NC}"
echo ""

# 步骤4: 创建Conda环境
echo -e "${GREEN}[步骤4/7] 创建Conda环境...${NC}"
PROJECT_DIR="$INSTALL_DIR/pm/client-linux"

if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
    echo -e "${YELLOW}环境 $CONDA_ENV_NAME 已存在，跳过创建${NC}"
    echo -e "${YELLOW}如需重新创建，请先执行: conda env remove -n $CONDA_ENV_NAME${NC}"
else
    echo -e "${GREEN}正在创建Conda环境: $CONDA_ENV_NAME${NC}"
    conda env create -f "$PROJECT_DIR/client/environment.yml"
    echo -e "${GREEN}环境创建完成${NC}"
fi
echo ""

# 步骤5: 激活环境并安装依赖
echo -e "${GREEN}[步骤5/7] 激活环境并安装依赖...${NC}"
conda activate $CONDA_ENV_NAME

# 验证Python版本
echo -e "${GREEN}验证Python版本...${NC}"
python --version

# 确保所有依赖都安装（environment.yml应该已经安装了，这里作为补充）
echo -e "${GREEN}安装/更新pip依赖包...${NC}"
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${GREEN}使用根目录 requirements.txt 安装依赖...${NC}"
    pip install -r "$PROJECT_DIR/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
elif [ -f "$PROJECT_DIR/client/requirements.txt" ]; then
    echo -e "${GREEN}使用 client/requirements.txt 安装依赖...${NC}"
    pip install -r "$PROJECT_DIR/client/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
else
    echo -e "${YELLOW}未找到requirements.txt，跳过pip安装（依赖已通过environment.yml安装）${NC}"
fi

# 验证关键包
echo -e "${GREEN}验证关键依赖包...${NC}"
python -c "import flask; import web3; import requests; print('✓ 核心依赖包已安装')" || {
    echo -e "${RED}依赖包验证失败${NC}"
    exit 1
}
echo ""

# 步骤6: 配置防火墙
echo -e "${GREEN}[步骤6/7] 配置防火墙...${NC}"
if command -v firewall-cmd &> /dev/null; then
    if sudo firewall-cmd --list-ports | grep -q "9000/tcp"; then
        echo -e "${YELLOW}端口9000已开放${NC}"
    else
        echo -e "${GREEN}开放端口9000...${NC}"
        sudo firewall-cmd --permanent --add-port=9000/tcp
        sudo firewall-cmd --reload
        echo -e "${GREEN}端口9000已开放${NC}"
    fi
else
    echo -e "${YELLOW}未检测到firewalld，请手动开放端口9000${NC}"
fi
echo ""

# 步骤7: 生成启动脚本
echo -e "${GREEN}[步骤7/7] 生成启动脚本...${NC}"
cat > "$INSTALL_DIR/start_client.sh" << EOF
#!/bin/bash
# PMS客户端启动脚本

cd "$PROJECT_DIR"
source \$(conda info --base)/etc/profile.d/conda.sh
conda activate $CONDA_ENV_NAME
python run_client.py
EOF

chmod +x "$INSTALL_DIR/start_client.sh"

# 生成后台启动脚本
cat > "$INSTALL_DIR/start_client_background.sh" << EOF
#!/bin/bash
# PMS客户端后台启动脚本

cd "$PROJECT_DIR"
source \$(conda info --base)/etc/profile.d/conda.sh
conda activate $CONDA_ENV_NAME
nohup python run_client.py > client.log 2>&1 &
echo \$! > client.pid
echo "客户端已启动，PID: \$(cat client.pid)"
echo "查看日志: tail -f $PROJECT_DIR/client.log"
EOF

chmod +x "$INSTALL_DIR/start_client_background.sh"

# 生成停止脚本
cat > "$INSTALL_DIR/stop_client.sh" << EOF
#!/bin/bash
# PMS客户端停止脚本

if [ -f "$PROJECT_DIR/client.pid" ]; then
    PID=\$(cat "$PROJECT_DIR/client.pid")
    if ps -p \$PID > /dev/null 2>&1; then
        kill \$PID
        echo "客户端已停止 (PID: \$PID)"
        rm "$PROJECT_DIR/client.pid"
    else
        echo "客户端进程不存在"
        rm "$PROJECT_DIR/client.pid"
    fi
else
    echo "未找到PID文件，尝试通过进程名停止..."
    pkill -f "run_client.py" && echo "客户端已停止" || echo "未找到运行中的客户端"
fi
EOF

chmod +x "$INSTALL_DIR/stop_client.sh"

echo -e "${GREEN}启动脚本已生成:${NC}"
echo -e "  - 前台启动: $INSTALL_DIR/start_client.sh"
echo -e "  - 后台启动: $INSTALL_DIR/start_client_background.sh"
echo -e "  - 停止服务: $INSTALL_DIR/stop_client.sh"
echo ""

# 完成提示
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}下一步操作:${NC}"
echo -e "1. 启动客户端:"
echo -e "   ${GREEN}cd $INSTALL_DIR${NC}"
echo -e "   ${GREEN}./start_client.sh${NC}"
echo ""
echo -e "2. 或后台启动:"
echo -e "   ${GREEN}./start_client_background.sh${NC}"
echo ""
echo -e "3. 首次运行会提示输入配置:"
echo -e "   - 客户端ID: ${GREEN}$CLIENT_ID${NC} (或自定义)"
echo -e "   - 服务端URL: ${GREEN}$SERVER_URL${NC}"
echo -e "   - 客户端公网IP: (如果客户端在服务器上，输入服务器公网IP)"
echo ""
echo -e "4. 查看日志:"
echo -e "   ${GREEN}tail -f $PROJECT_DIR/client.log${NC}"
echo ""
echo -e "${YELLOW}配置文件位置:${NC}"
echo -e "   $PROJECT_DIR/client/data/client/config.json"
echo ""
