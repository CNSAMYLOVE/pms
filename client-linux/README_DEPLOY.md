# PMS 客户端部署指南

## 目录结构

```
client_deploy/
├── client/          # 客户端核心文件
├── pmq/            # 交易机器人依赖（trading_bot.py）
├── requirements.txt # Python依赖
├── run_client.py   # 客户端启动脚本
└── README_DEPLOY.md # 本文件
```

## 部署步骤

### 1. 上传文件到服务器

将整个 `client_deploy` 目录上传到服务器，例如：
```bash
# 使用 scp 上传
scp -r client_deploy user@server:/path/to/pms_client/

# 或使用 rsync
rsync -avz client_deploy/ user@server:/path/to/pms_client/
```

### 2. 安装 Python 依赖

```bash
cd /path/to/pms_client/client_deploy
pip install -r requirements.txt
```

或使用虚拟环境（推荐）：
```bash
cd /path/to/pms_client/client_deploy
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. 配置客户端

首次运行时会提示输入配置，或使用环境变量：

```bash
# 设置环境变量（Linux/Mac）
export PMS_CLIENT_ID=client-1
export PMS_SERVER_URL=http://your-server-ip:8000

# Windows CMD
set PMS_CLIENT_ID=client-1
set PMS_SERVER_URL=http://your-server-ip:8000

# Windows PowerShell
$env:PMS_CLIENT_ID="client-1"
$env:PMS_SERVER_URL="http://your-server-ip:8000"
```

### 4. 启动客户端

```bash
# 直接运行
python run_client.py

# 或使用 nohup 后台运行（Linux/Mac）
nohup python run_client.py > client.log 2>&1 &

# 或使用 screen
screen -S pms_client
python run_client.py
# 按 Ctrl+A 然后 D 退出 screen

# 或使用 systemd 服务（见下方）
```

## 使用 systemd 管理服务（Linux）

创建服务文件 `/etc/systemd/system/pms-client.service`：

```ini
[Unit]
Description=PMS Client Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/pms_client/client_deploy
Environment="PMS_CLIENT_ID=client-1"
Environment="PMS_SERVER_URL=http://your-server-ip:8000"
ExecStart=/usr/bin/python3 /path/to/pms_client/client_deploy/run_client.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用和启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable pms-client
sudo systemctl start pms-client
sudo systemctl status pms-client
```

查看日志：
```bash
sudo journalctl -u pms-client -f
```

## 配置说明

### 客户端ID (PMS_CLIENT_ID)

每个客户端必须有唯一的ID，例如：
- client-1
- client-2
- client-prod-01

### 服务端URL (PMS_SERVER_URL)

服务端的访问地址，例如：
- http://101.32.22.185:8000 （当前使用的服务端）
- http://192.168.1.100:8000 （内网地址）
- https://your-domain.com:8000 （域名）

**重要：** 如果使用远程服务端，确保URL正确且网络可达。

### 客户端端口

默认监听端口：9000

可以通过修改 `client/app.py` 中的 `CLIENT_PORT` 来更改。

### 客户端公网IP (PMS_CLIENT_IP)

**重要：** 如果客户端在服务器上运行，且服务端需要通过公网访问客户端，需要配置客户端公网IP。

配置方式：
- 环境变量：`export PMS_CLIENT_IP=your-public-ip`
- 配置文件：在 `client/data/client/config.json` 中添加 `"client_ip": "your-public-ip"`
- 首次运行时会提示输入

**注意：** 如果自动检测的IP是内网IP（如 192.168.x.x、10.x.x.x），服务端无法访问，必须手动配置公网IP。

## 数据存储

客户端数据存储在：
```
client_deploy/client/data/
├── client/
│   ├── config.json      # 客户端配置（自动创建）
│   └── accounts.json    # 账号数据（从服务端同步）
```

## 防火墙设置

确保客户端端口（默认9000）可以被服务端访问：

```bash
# Linux (ufw)
sudo ufw allow 9000/tcp

# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 9000 -j ACCEPT

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

## 故障排查

### 1. 无法连接到服务端

检查：
- 服务端是否运行
- 防火墙是否开放端口
- PMS_SERVER_URL 是否正确
- 网络是否可达

### 2. 导入错误

确保：
- 已安装所有依赖：`pip install -r requirements.txt`
- pmq 目录存在且包含 trading_bot.py
- Python 版本 >= 3.7

### 3. 端口被占用

检查端口占用：
```bash
# Linux/Mac
lsof -i :9000
# 或
netstat -tlnp | grep 9000

# Windows
netstat -ano | findstr :9000
```

### 4. 查看日志

客户端会在控制台输出日志，如果使用 systemd，查看：
```bash
sudo journalctl -u pms-client -f
```

## 更新客户端

1. 停止服务
2. 备份数据目录
3. 替换代码文件
4. 重启服务

```bash
sudo systemctl stop pms-client
cp -r client/data client/data.backup
# 替换新文件
sudo systemctl start pms-client
```

## 注意事项

1. **安全性**：确保客户端端口不对外暴露，或使用防火墙限制访问
2. **备份**：定期备份 `client/data` 目录
3. **监控**：建议使用进程监控工具（如 systemd、supervisor）确保服务持续运行
4. **日志**：建议将日志输出到文件，方便排查问题

