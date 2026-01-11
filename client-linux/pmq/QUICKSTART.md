# 快速启动指南

## 1. 安装依赖

```bash
cd pmq
pip install -r requirements.txt
```

## 2. 启动系统

```bash
python run.py
```

或者：

```bash
python app.py
```

## 3. 访问界面

打开浏览器访问：`http://localhost:5000`

## 4. 添加账号

1. 点击"添加账号"按钮
2. 填写账号信息：
   - **账号名称**：自定义名称（如：账号1）
   - **私钥**：0x开头的私钥
   - **代理钱包地址**：可选，如果使用代理钱包
   - **Builder API Key**：从Polymarket获取
   - **Builder API Secret**：从Polymarket获取
   - **Builder API Passphrase**：从Polymarket获取
   - **代理IP**：格式 `http://ip:port` 或 `http://user:pass@ip:port`
   - **备注**：可选

3. 点击"添加"按钮

## 5. 配置策略

在"任务数据面板"中配置：
- **订单执行金额**：每次下单金额（默认$2）
- **价格阈值**：达到多少百分比时买入（默认85%）
- **检查时间窗口**：市场结束前多少分钟检查（默认2分钟）
- **监控间隔**：扫描间隔（默认3秒）

点击"更新策略配置"保存

## 6. 启动任务

在账号列表中，点击对应账号的"启动"按钮

## 7. 查看状态

在"运行状态"面板查看正在运行的账号

## 代理IP配置示例

### 示例1：HTTP代理
```
http://192.168.1.100:8080
```

### 示例2：HTTPS代理
```
https://192.168.1.100:8080
```

### 示例3：带认证的代理
```
http://username:password@192.168.1.100:8080
```

### 示例4：SOCKS5代理（需要Proxifier）
```
socks5://192.168.1.100:1080
```

## 常见问题

### Q: Web3 RPC如何走代理？
A: 推荐使用Proxifier软件，或者为每个账号配置不同的RPC节点。详见 `PROXY_IMPLEMENTATION.md`

### Q: 如何测试代理是否可用？
A: 可以使用以下Python代码测试：
```python
import requests
proxy = "http://ip:port"
proxies = {'http': proxy, 'https': proxy}
response = requests.get('https://httpbin.org/ip', proxies=proxies)
print(response.json())
```

### Q: 多个账号可以同时运行吗？
A: 可以，每个账号在独立的线程中运行，互不干扰。

### Q: 如何停止账号？
A: 在账号列表中点击"停止"按钮。

### Q: 数据存储在哪里？
A: 数据存储在 `data/` 目录下：
- `accounts.json`：账号数据
- `tasks.json`：任务数据（如果有）

## 下一步

- 查看 `README.md` 了解详细功能
- 查看 `PROXY_IMPLEMENTATION.md` 了解代理实现细节
- 根据需要修改 `config.py` 中的配置









