# PMS 客户端部署包

## 📦 部署包说明

这是一个完整的 PMS 客户端部署包，包含运行客户端所需的所有文件。

## 📁 目录结构

```
client_deploy/
├── client/                    # 客户端核心文件
│   ├── __init__.py
│   ├── account_manager.py     # 账号管理
│   ├── app.py                 # Flask 应用
│   ├── command_executor.py    # 命令执行器（已优化路径查找）
│   ├── config_manager.py      # 配置管理
│   └── run.py                 # 原始启动脚本
│
├── pmq/                       # 交易机器人依赖（必需）
│   ├── trading_bot.py         # 核心交易模块（必需）
│   ├── config.py              # 交易配置（必需）
│   └── ...                    # 其他文件
│
├── requirements.txt           # Python 依赖包
├── run_client.py              # 推荐使用的启动脚本
├── start.bat                  # Windows 快速启动脚本
├── start.sh                   # Linux/Mac 快速启动脚本
│
└── 文档/
    ├── README_DEPLOY.md       # 详细部署说明
    ├── INSTALL.md             # 快速安装指南
    └── 打包说明.md             # 打包说明
```

## 🚀 快速开始

### Windows

1. 解压部署包
2. 双击运行 `start.bat`（会自动安装依赖）
3. 首次运行会提示输入客户端ID和服务端URL

### Linux/Mac

```bash
# 1. 解压部署包
unzip client_deploy.zip
cd client_deploy

# 2. 给脚本执行权限
chmod +x start.sh

# 3. 运行（会自动安装依赖）
./start.sh
```

### 手动启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量（可选）
export PMS_CLIENT_ID=client-1
export PMS_SERVER_URL=http://your-server:8000

# 3. 启动
python run_client.py
```

## ⚙️ 配置

### 必需配置

- **客户端ID** (`PMS_CLIENT_ID`): 唯一标识，例如 `client-1`
- **服务端URL** (`PMS_SERVER_URL`): 服务端地址，例如 `http://101.32.22.185:8000`

### 可选配置

- **客户端公网IP** (`PMS_CLIENT_IP`): 如果客户端在服务器上，需要配置公网IP以便服务端访问

### 配置方式

1. **首次运行时输入**（推荐，最简单）
   ```bash
   python run_client.py
   # 会提示输入：
   # - 客户端ID
   # - 服务端URL（默认会询问，输入：http://101.32.22.185:8000）
   # - 客户端公网IP（如果需要）
   ```

2. **环境变量**（推荐用于生产环境）
   ```bash
   export PMS_CLIENT_ID=client-1
   export PMS_SERVER_URL=http://101.32.22.185:8000
   export PMS_CLIENT_IP=your-client-public-ip  # 如果客户端在服务器上
   ```

3. **配置文件**（首次运行后自动生成）
   - 位置：`client/data/client/config.json`
   - 格式：
     ```json
     {
       "client_id": "client-1",
       "server_url": "http://101.32.22.185:8000",
       "client_ip": "optional-public-ip"
     }
     ```

### 端口配置

默认监听端口：**9000**

可以通过修改 `client/app.py` 中的 `CLIENT_PORT` 来更改。

## 📋 文件清单

### 核心文件（必需）

- ✅ `client/command_executor.py` - 已优化路径查找逻辑
- ✅ `pmq/trading_bot.py` - 交易机器人核心
- ✅ `pmq/config.py` - 交易配置
- ✅ `requirements.txt` - Python 依赖

### 启动脚本

- `run_client.py` - 主启动脚本（推荐）
- `start.bat` - Windows 快速启动
- `start.sh` - Linux/Mac 快速启动

## 🔧 技术说明

### 路径查找优化

`command_executor.py` 已更新为自动查找 `pmq` 目录，支持以下目录结构：

```
client_deploy/
├── client/
└── pmq/          ✅ 支持
```

```
pms1/
├── client/
└── pmq/          ✅ 支持
```

### 依赖关系

客户端依赖：
- Flask (Web 框架)
- pmq.trading_bot (交易机器人)
- Web3 (区块链交互)
- py-clob-client (CLOB API)

所有依赖已在 `requirements.txt` 中列出。

## 📝 部署检查清单

部署前请确认：

- [ ] Python 3.7+ 已安装
- [ ] `client/` 目录存在
- [ ] `pmq/trading_bot.py` 存在
- [ ] `pmq/config.py` 存在
- [ ] `requirements.txt` 存在
- [ ] 网络可以访问服务端（`http://101.32.22.185:8000`）
- [ ] 防火墙已开放端口 9000
- [ ] 配置了客户端ID和服务端URL
- [ ] 如果客户端在服务器上，配置了客户端公网IP

## ⚠️ 重要提示（服务端地址：101.32.22.185）

**服务端URL：** `http://101.32.22.185:8000`

首次运行时会提示输入，请确保输入正确的服务端地址。

如果客户端在服务器上运行：
- 需要配置客户端公网IP（`PMS_CLIENT_IP`）
- 确保防火墙开放端口9000
- 确保服务端可以访问客户端的公网IP:9000

详细配置说明请查看 `配置说明.md`

## 🛠️ 故障排查

详细故障排查请查看 `README_DEPLOY.md` 或 `INSTALL.md`

## 📞 获取帮助

- 详细部署说明：查看 `README_DEPLOY.md`
- 快速安装指南：查看 `INSTALL.md`
- 打包说明：查看 `打包说明.md`

