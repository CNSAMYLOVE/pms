# 代理IP实现方案

## 问题说明

在一台电脑上运行多个账号，每个账号使用不同的代理IP，需要解决以下问题：

1. **HTTP请求代理**：API调用（Gamma API、CLOB API、Data API）
2. **Web3 RPC代理**：区块链RPC节点连接（Polygon RPC）

## 实现方案

### 方案1：使用 requests 库的 proxies 参数（已实现）

**优点**：
- 简单直接
- 每个账号独立配置
- 支持HTTP/HTTPS代理

**缺点**：
- 只适用于HTTP请求
- Web3的HTTPProvider不支持代理

**实现代码**：
```python
# 在 trading_bot.py 中
if self.proxy_ip:
    self.proxies = {
        'http': self.proxy_ip,
        'https': self.proxy_ip
    }

# 使用代理发起请求
def _make_request(self, method, url, **kwargs):
    if self.proxies:
        kwargs['proxies'] = self.proxies
    return requests.get(url, **kwargs)
```

### 方案2：使用代理中间件（推荐）

**实现思路**：
1. 为每个账号创建独立的Session
2. 使用 `requests.Session` 配置代理
3. 所有HTTP请求都通过Session

**代码示例**：
```python
import requests

class TradingBot:
    def __init__(self, account_data, proxy_ip=None):
        self.session = requests.Session()
        if proxy_ip:
            self.session.proxies = {
                'http': proxy_ip,
                'https': proxy_ip
            }
    
    def _make_request(self, method, url, **kwargs):
        if method.upper() == 'GET':
            return self.session.get(url, **kwargs)
        # ...
```

### 方案3：使用 Proxifier 软件（最简单）

**步骤**：
1. 下载安装 Proxifier（Windows/Mac）
2. 配置代理服务器列表
3. 创建规则：Python进程 -> 指定代理
4. 为不同账号配置不同的代理规则

**优点**：
- 无需修改代码
- 所有网络流量（包括Web3 RPC）都走代理
- 支持SOCKS5代理

**缺点**：
- 需要额外软件
- 商业软件（有免费试用）

### 方案4：使用代理池（高级）

**实现思路**：
1. 创建代理池管理器
2. 为每个账号分配代理
3. 自动检测代理可用性
4. 代理失效时自动切换

**代码结构**：
```python
class ProxyPool:
    def __init__(self):
        self.proxies = []
        self.assigned = {}  # account_id -> proxy
    
    def assign_proxy(self, account_id):
        # 分配代理逻辑
        pass
    
    def check_proxy(self, proxy):
        # 检测代理可用性
        pass
```

## Web3 RPC 代理问题

### 问题
Web3的 `HTTPProvider` 不支持直接配置代理。

### 解决方案

#### 方案A：使用支持代理的RPC节点
```python
# 通过代理访问RPC节点
# 需要配置代理中间件或使用Proxifier
w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
```

#### 方案B：使用本地代理转发
```python
# 创建本地HTTP代理服务器
# 转发请求到真实RPC节点
# 这样可以通过代理访问
```

#### 方案C：使用不同的RPC节点
```python
# 为每个账号配置不同的RPC节点
# 通过代理访问不同的节点
rpc_nodes = {
    'account1': 'https://rpc-node1.com',
    'account2': 'https://rpc-node2.com',
}
```

## 推荐实现方案

### 对于HTTP请求（API调用）
✅ **已实现**：使用 `requests` 的 `proxies` 参数

### 对于Web3 RPC
推荐使用 **Proxifier** 或配置不同的RPC节点：

1. **使用Proxifier**（最简单）
   - 安装Proxifier
   - 配置规则：`python.exe` -> 代理1
   - 为不同账号启动不同的Python进程（使用不同端口）

2. **使用不同RPC节点**
   ```python
   # 在 config.py 中配置
   RPC_NODES = {
       'account1': 'https://polygon-rpc.com',
       'account2': 'https://rpc.ankr.com/polygon',
       'account3': 'https://polygon.llamarpc.com',
   }
   ```

## 测试代理

```python
# 测试代理是否可用
import requests

proxy = "http://ip:port"
proxies = {'http': proxy, 'https': proxy}

try:
    response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
    print(f"代理IP: {response.json()}")
except Exception as e:
    print(f"代理不可用: {e}")
```

## 注意事项

1. **代理格式**：
   - HTTP: `http://ip:port`
   - HTTPS: `https://ip:port`
   - 带认证: `http://user:pass@ip:port`

2. **代理稳定性**：
   - 定期检测代理可用性
   - 代理失效时自动切换或暂停账号

3. **并发限制**：
   - 注意代理的并发连接数限制
   - 避免过多账号同时使用同一代理

4. **IP轮换**：
   - 考虑实现IP轮换机制
   - 避免频繁请求导致IP被封









