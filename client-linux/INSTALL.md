# PMS 客户端快速安装指南

## 📦 部署包内容检查清单

部署前请确认以下文件存在：

- [x] `client/` 目录（客户端核心代码）
- [x] `pmq/` 目录（交易机器人依赖）
- [x] `pmq/trading_bot.py`（必需）
- [x] `pmq/config.py`（必需）
- [x] `requirements.txt`（Python 依赖）
- [x] `run_client.py`（启动脚本）
- [x] `README_DEPLOY.md`（详细文档）

## 🚀 快速部署（3步）

### 步骤 1: 上传文件

将 `client_deploy` 目录上传到服务器：
```bash
# 使用 scp (Linux/Mac)
scp -r client_deploy/ user@server:/opt/pms_client/

# 或使用 WinSCP、FileZilla 等工具
```

### 步骤 2: 安装依赖

```bash
cd /opt/pms_client/client_deploy

# 方法1: 使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 方法2: 直接安装（不推荐，可能污染系统环境）
pip3 install -r requirements.txt
```

### 步骤 3: 启动客户端

```bash
# 方法1: 使用提供的脚本（推荐）
chmod +x start.sh
./start.sh

# 方法2: 手动启动
python3 run_client.py

# 方法3: 后台运行
nohup python3 run_client.py > client.log 2>&1 &
```

## ⚙️ 配置

首次运行会提示输入：
- **客户端ID**: 例如 `client-1`、`client-2`（必须唯一）
- **服务端URL**: 例如 `http://192.168.1.100:8000`

或使用环境变量（推荐用于生产环境）：
```bash
export PMS_CLIENT_ID=client-1
export PMS_SERVER_URL=http://101.32.22.185:8000
export PMS_CLIENT_IP=your-client-public-ip  # 如果客户端在服务器上，需要配置
python3 run_client.py
```

**重要提示：**
- 服务端地址：`http://101.32.22.185:8000`
- 如果客户端在服务器上运行，需要配置 `PMS_CLIENT_IP` 为服务器的公网IP
- 详细配置说明请查看 `配置说明.md`

## 🔍 验证部署

1. 检查客户端是否启动：
   ```bash
   ps aux | grep run_client
   ```

2. 检查端口是否监听：
   ```bash
   netstat -tlnp | grep 9000
   # 或
   ss -tlnp | grep 9000
   ```

3. 检查服务端是否能看到客户端：
   - 访问服务端 Web 界面
   - 查看"客户端管理"面板
   - 应该能看到新注册的客户端

## 🛠️ 常见问题

### 问题1: 导入错误 `ModuleNotFoundError: No module named 'trading_bot'`

**解决**：
1. 确认 `pmq` 目录存在
2. 确认 `pmq/trading_bot.py` 存在
3. 检查 `command_executor.py` 的路径查找逻辑

### 问题2: 端口被占用

**解决**：
```bash
# 查找占用端口的进程
lsof -i :9000
# 或
netstat -tlnp | grep 9000

# 修改端口（编辑 client/app.py 中的 CLIENT_PORT）
```

### 问题3: 无法连接到服务端

**解决**：
1. 检查服务端是否运行
2. 检查防火墙是否开放端口
3. 检查 `PMS_SERVER_URL` 是否正确
4. 测试网络连通性：`ping your-server-ip`

### 问题4: 依赖安装失败

**解决**：
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像源（如果网络慢）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 📝 下一步

部署成功后：
1. 在服务端添加账号
2. 创建实例并分配账号到客户端
3. 测试下单功能

详细文档请查看 `README_DEPLOY.md`

