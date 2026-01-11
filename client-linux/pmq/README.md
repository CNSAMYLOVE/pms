# Polymarket 多账号群控系统

## 功能特点

1. **多账号管理**
   - 支持添加多个账号
   - 每个账号独立的私钥、代理钱包、Builder API凭证
   - 账号状态管理（活跃/暂停/错误）

2. **独立代理IP**
   - 每个账号可以配置不同的代理IP
   - 支持HTTP/HTTPS代理
   - 支持带认证的代理（user:pass@ip:port）

3. **任务调度**
   - 每个账号独立运行监控任务
   - 支持启动/停止单个账号
   - 实时状态监控

4. **Web UI界面**
   - 账号数据面板
   - 任务配置面板
   - 运行状态监控

## 安装步骤

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行程序：
```bash
python app.py
```

3. 打开浏览器访问：
```
http://localhost:5000
```

## 使用说明

### 添加账号

1. 点击"添加账号"按钮
2. 填写账号信息：
   - 账号名称
   - 私钥（0x开头）
   - 代理钱包地址（可选）
   - Builder API凭证（Key、Secret、Passphrase）
   - 代理IP（格式：http://ip:port 或 http://user:pass@ip:port）
   - 备注信息

### 配置代理IP

每个账号可以配置独立的代理IP：

- **HTTP代理**: `http://192.168.1.100:8080`
- **HTTPS代理**: `https://192.168.1.100:8080`
- **带认证的代理**: `http://username:password@192.168.1.100:8080`

### 启动任务

1. 选择要启动的账号（勾选复选框）
2. 配置策略参数（订单金额、价格阈值等）
3. 点击账号行的"启动"按钮
4. 查看运行状态面板

### 策略配置

- **订单执行金额**: 每次下单的USDC金额（默认$2）
- **价格阈值**: UP/DOWN价格达到多少百分比时买入（默认85%）
- **检查时间窗口**: 市场结束前多少分钟开始检查（默认2分钟）
- **监控间隔**: 扫描市场的间隔时间（默认3秒）

## 代理IP实现说明

### 技术实现

1. **HTTP请求代理**
   - 使用 `requests` 库的 `proxies` 参数
   - 每个账号的 `TradingBot` 实例独立配置代理
   - 所有HTTP请求（API调用）都通过代理

2. **Web3 RPC代理**
   - Web3的HTTPProvider本身不支持代理
   - 解决方案：
     - 方案1：使用支持代理的RPC节点（如Infura、Alchemy）
     - 方案2：通过代理中间件转发RPC请求
     - 方案3：使用本地代理软件（如Proxifier）强制所有流量走代理

3. **推荐方案**

   如果使用独立代理，推荐使用**方案3**（Proxifier）：
   - 安装Proxifier软件
   - 配置规则：Python进程 -> 指定代理
   - 这样所有网络请求（包括Web3 RPC）都会走代理

   或者使用**方案1**：
   - 为每个账号配置不同的RPC节点
   - 通过代理访问RPC节点

## 项目结构

```
pmq/
├── app.py                 # Flask后端API
├── account_manager.py     # 账号管理模块
├── task_scheduler.py      # 任务调度器
├── trading_bot.py         # 交易机器人（支持代理）
├── config.py              # 配置文件
├── requirements.txt       # 依赖包
├── README.md             # 说明文档
├── data/                 # 数据存储目录
│   ├── accounts.json    # 账号数据
│   └── tasks.json       # 任务数据
├── templates/           # HTML模板
│   └── index.html
└── static/              # 静态文件
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## 注意事项

1. **私钥安全**: 私钥存储在本地JSON文件中，请妥善保管
2. **代理稳定性**: 确保代理IP稳定可用
3. **API限制**: 注意Polymarket API的请求频率限制
4. **余额检查**: 确保每个账号有足够的USDC余额

## 开发计划

- [ ] 完善价格获取逻辑
- [ ] 添加持仓数据面板
- [ ] 添加订单历史记录
- [ ] 添加统计报表
- [ ] 支持批量操作









