# CentOS 服务器部署指南（Conda环境）

## ⚠️ 安全提醒

**如果你在消息中公开了GitHub Token，请立即：**
1. 登录 GitHub → Settings → Developer settings → Personal access tokens
2. 找到已泄露的Token并撤销（Revoke）
3. 重新生成一个新的Token

**Token应该保密，不要在公共场合分享！**

## 📋 前置要求

- CentOS 7/8 服务器
- 具有 sudo 权限
- 网络可访问 GitHub 和 PyPI

## 🚀 部署步骤

### 步骤 1: 安装 Miniconda（如果未安装）

```bash
# 下载Miniconda安装脚本
cd /tmp
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# 安装Miniconda
bash Miniconda3-latest-Linux-x86_64.sh

# 按照提示安装（建议安装到 /opt/miniconda3）
# 安装完成后，重新加载shell配置
source ~/.bashrc

# 验证安装
conda --version
```

### 步骤 2: 从GitHub克隆代码

有两种方式克隆代码：

#### 方式1: 使用HTTPS + Token（推荐）

```bash
# 创建项目目录
cd /opt
sudo mkdir -p pms_client
sudo chown $USER:$USER pms_client
cd pms_client

# 使用Token克隆（替换 YOUR_TOKEN 为你的实际Token）
git clone https://YOUR_TOKEN@github.com/CNSAMYLOVE/pm.git

# 或使用环境变量（更安全）
export GITHUB_TOKEN="your_token_here"
git clone https://${GITHUB_TOKEN}@github.com/CNSAMYLOVE/pm.git

# 进入项目目录并切换到指定commit
cd pm
git checkout 947a3942804b3080b274d9375d3458fe2ca1bb9b
cd client-linux
```

#### 方式2: 使用SSH（更安全，推荐）

```bash
# 1. 生成SSH密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"
# 一路回车使用默认设置

# 2. 查看公钥
cat ~/.ssh/id_ed25519.pub

# 3. 将公钥添加到GitHub:
#    GitHub → Settings → SSH and GPG keys → New SSH key → 粘贴公钥

# 4. 测试SSH连接
ssh -T git@github.com

# 5. 使用SSH克隆
cd /opt
sudo mkdir -p pms_client
sudo chown $USER:$USER pms_client
cd pms_client
git clone git@github.com:CNSAMYLOVE/pm.git
cd pm
git checkout 947a3942804b3080b274d9375d3458fe2ca1bb9b
cd client-linux
```

### 步骤 3: 创建Conda环境并安装依赖

```bash
# 进入项目目录
cd /opt/pms_client/pm/client-linux

# 使用environment.yml创建conda环境
conda env create -f client/environment.yml

# 激活环境
conda activate pms-client

# 验证环境
python --version  # 应该是 Python 3.11
conda list  # 查看已安装的包
```

**如果环境创建失败，可以手动安装：**

```bash
# 创建基础环境
conda create -n pms-client python=3.11 -y
conda activate pms-client

# 安装conda包
conda install -c conda-forge requests python-dateutil -y

# 安装pip包
pip install -r client/requirements.txt
```

### 步骤 4: 配置客户端

首次运行会提示输入配置，或使用环境变量：

```bash
# 激活conda环境
conda activate pms-client

# 方式1: 首次运行时交互式配置（推荐首次使用）
python run_client.py
# 按提示输入：
# - 客户端ID（例如：client-1）
# - 服务端URL（默认：http://101.32.22.185:8000）
# - 客户端公网IP（如果客户端在服务器上，输入服务器公网IP）

# 方式2: 使用环境变量（推荐生产环境）
export PMS_CLIENT_ID=client-1
export PMS_SERVER_URL=http://101.32.22.185:8000
export PMS_CLIENT_IP=your-server-public-ip  # 如果客户端在服务器上
python run_client.py
```

**配置说明：**
- **客户端ID**: 唯一标识，例如 `client-1`、`client-2`
- **服务端URL**: `http://101.32.22.185:8000`
- **客户端公网IP**: 如果客户端在服务器上运行，需要输入服务器的公网IP

配置文件会自动保存到：`client/data/client/config.json`

### 步骤 5: 配置防火墙

```bash
# CentOS/RHEL 7/8 (firewalld)
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload

# 验证端口开放
sudo firewall-cmd --list-ports

# 或者如果使用iptables
sudo iptables -A INPUT -p tcp --dport 9000 -j ACCEPT
sudo service iptables save  # CentOS 6
```

### 步骤 6: 启动客户端

#### 方式1: 前台运行（测试用）

```bash
conda activate pms-client
python run_client.py
```

#### 方式2: 后台运行（使用nohup）

```bash
conda activate pms-client
cd /opt/pms_client/pm/client-linux
nohup python run_client.py > client.log 2>&1 &
echo $! > client.pid  # 保存进程ID

# 查看日志
tail -f client.log

# 停止服务
kill $(cat client.pid)
```

#### 方式3: 使用screen（推荐）

```bash
conda activate pms-client
cd /opt/pms_client/pm/client-linux

# 创建screen会话
screen -S pms-client

# 在screen中运行
python run_client.py

# 退出screen（保持运行）：按 Ctrl+A，然后按 D

# 重新连接screen
screen -r pms-client

# 查看所有screen会话
screen -ls
```

#### 方式4: 使用systemd服务（推荐生产环境）

创建服务文件：

```bash
sudo nano /etc/systemd/system/pms-client.service
```

添加以下内容（根据实际路径修改）：

```ini
[Unit]
Description=PMS Client Service
After=network.target

[Service]
Type=simple
User=your_username
Group=your_group
WorkingDirectory=/opt/pms_client/pm/client-linux

# Conda环境路径（根据实际安装路径修改）
Environment="PATH=/opt/miniconda3/envs/pms-client/bin:/usr/local/bin:/usr/bin:/bin"

# 客户端配置（可选，也可以在config.json中配置）
Environment="PMS_CLIENT_ID=client-1"
Environment="PMS_SERVER_URL=http://101.32.22.185:8000"
Environment="PMS_CLIENT_IP=your-server-public-ip"

# 启动命令
ExecStart=/opt/miniconda3/envs/pms-client/bin/python /opt/pms_client/pm/client-linux/run_client.py

# 重启策略
Restart=always
RestartSec=10

# 日志
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable pms-client

# 启动服务
sudo systemctl start pms-client

# 查看状态
sudo systemctl status pms-client

# 查看日志
sudo journalctl -u pms-client -f

# 停止服务
sudo systemctl stop pms-client

# 重启服务
sudo systemctl restart pms-client
```

## 🔍 验证部署

### 1. 检查进程

```bash
# 查看Python进程
ps aux | grep run_client

# 查看端口监听
netstat -tlnp | grep 9000
# 或
ss -tlnp | grep 9000
```

### 2. 检查健康状态

```bash
# 测试健康检查接口
curl http://localhost:9000/api/health

# 应该返回JSON响应，包含client_id和status
```

### 3. 检查服务端连接

1. 访问服务端Web界面：`http://101.32.22.185:8000`
2. 查看"客户端管理"面板
3. 应该能看到新注册的客户端

## 🛠️ 故障排查

### 问题1: Conda环境创建失败

```bash
# 清理conda缓存
conda clean --all

# 使用国内镜像源（如果网络慢）
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --set show_channel_urls yes

# 重新创建环境
conda env create -f client/environment.yml
```

### 问题2: 依赖安装失败

```bash
conda activate pms-client

# 升级pip
pip install --upgrade pip

# 使用国内镜像源
pip install -r client/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题3: 无法连接到服务端

```bash
# 测试网络连通性
ping 101.32.22.185

# 测试端口连通性
telnet 101.32.22.185 8000
# 或
nc -zv 101.32.22.185 8000

# 检查防火墙
sudo firewall-cmd --list-all
```

### 问题4: 端口被占用

```bash
# 查找占用端口的进程
sudo lsof -i :9000
# 或
sudo netstat -tlnp | grep 9000

# 修改端口（编辑 client/app.py 中的 CLIENT_PORT）
```

### 问题5: 查看详细日志

```bash
# 如果使用systemd
sudo journalctl -u pms-client -n 100 -f

# 如果使用nohup
tail -f /opt/pms_client/pm/client-linux/client.log

# 如果使用screen
screen -r pms-client
# 然后查看输出
```

## 📝 更新客户端

```bash
# 1. 停止服务
sudo systemctl stop pms-client
# 或
kill $(cat client.pid)

# 2. 备份数据
cd /opt/pms_client/pm/client-linux
cp -r client/data client/data.backup.$(date +%Y%m%d_%H%M%S)

# 3. 更新代码
cd /opt/pms_client/pm
git pull
git checkout 947a3942804b3080b274d9375d3458fe2ca1bb9b
cd client-linux

# 4. 更新依赖（如果需要）
conda activate pms-client
conda env update -f client/environment.yml --prune

# 5. 重启服务
sudo systemctl start pms-client
# 或
conda activate pms-client
nohup python run_client.py > client.log 2>&1 &
```

## 📁 目录结构

```
/opt/pms_client/pm/client-linux/
├── client/                    # 客户端核心文件
│   ├── app.py                # Flask应用
│   ├── command_executor.py   # 命令执行器
│   ├── config_manager.py     # 配置管理
│   ├── account_manager.py    # 账号管理
│   ├── data/                 # 数据目录
│   │   └── client/
│   │       ├── config.json   # 客户端配置
│   │       └── accounts.json # 账号数据
│   └── environment.yml       # Conda环境文件
├── pmq/                      # 交易机器人依赖
├── run_client.py             # 启动脚本
└── requirements.txt          # Python依赖
```

## ⚙️ 配置文件位置

- 客户端配置：`client/data/client/config.json`
- 账号数据：`client/data/client/accounts.json`

配置文件示例：

```json
{
  "client_id": "client-1",
  "server_url": "http://101.32.22.185:8000",
  "client_ip": "your-server-public-ip"
}
```

## 🔐 安全建议

1. **Token安全**：不要将GitHub Token提交到代码仓库
2. **防火墙**：只开放必要的端口（9000）
3. **权限控制**：使用非root用户运行服务
4. **日志管理**：定期清理日志文件
5. **备份**：定期备份 `client/data` 目录

## 📞 获取帮助

- 查看详细配置说明：`配置说明.md`
- 查看快速配置：`快速配置.md`
- 查看安装指南：`INSTALL.md`
