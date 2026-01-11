// 主JavaScript文件
let selectedAccounts = new Set();

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadAccounts();
    loadRunningStatus();
    updateRunningAccounts();
    updateSchedulerStatus();
    setInterval(loadAccounts, 5000); // 每5秒刷新账号列表
    setInterval(loadRunningStatus, 3000); // 每3秒刷新运行状态
    setInterval(updateRunningAccounts, 3000); // 每3秒更新运行账号集合
    setInterval(updateSchedulerStatus, 3000); // 每3秒刷新调度线程状态
});

// 加载账号列表
async function loadAccounts() {
    try {
        const response = await fetch('/api/accounts');
        const result = await response.json();
        if (result.success) {
            renderAccountsTable(result.data);
        }
    } catch (error) {
        console.error('加载账号失败:', error);
    }
}

// 渲染账号表格
function renderAccountsTable(accounts) {
    const tbody = document.getElementById('accountsTableBody');
    tbody.innerHTML = '';
    
    accounts.forEach(account => {
        const tr = document.createElement('tr');
        const isSelected = selectedAccounts.has(account.id);
        const isRunning = checkAccountRunning(account.id);
        const balanceText = (account.balance_usdc !== undefined && account.balance_usdc !== null)
            ? account.balance_usdc
            : '未知';
        
        tr.innerHTML = `
            <td><input type="checkbox" ${isSelected ? 'checked' : ''} 
                onchange="toggleAccountSelection(${account.id}, this.checked)"></td>
            <td>${account.id}</td>
            <td>${account.name}</td>
            <td>${account.proxy_wallet_address || '未设置'}</td>
            <td>${account.proxy_ip || '无代理'}</td>
            <td>
                <span id="balance-${account.id}">${balanceText}</span>
                <button class="btn btn-sm btn-secondary" style="margin-left:6px" onclick="refreshBalance(${account.id})">刷新</button>
            </td>
            <td><span class="status-badge status-${account.status}">${getStatusText(account.status)}</span></td>
            <td>
                <button class="btn btn-sm ${isRunning ? 'btn-danger' : 'btn-success'}" 
                    onclick="${isRunning ? 'stopAccount' : 'startAccount'}(${account.id})">
                    ${isRunning ? '停止' : '启动'}
                </button>
                <button class="btn btn-sm btn-secondary" onclick="editAccount(${account.id})">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteAccount(${account.id})">删除</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    updateSelectedCount();
}

// 手动刷新单个账号余额
async function refreshBalance(accountId) {
    const balanceSpan = document.getElementById(`balance-${accountId}`);
    if (balanceSpan) balanceSpan.textContent = '刷新中...';
    try {
        const response = await fetch(`/api/accounts/${accountId}/balance`);
        const result = await response.json();
        if (result.success) {
            const balance = result.balance !== undefined ? result.balance : '未知';
            if (balanceSpan) balanceSpan.textContent = balance;
            // 重新加载列表以更新缓存
            loadAccounts();
        } else {
            if (balanceSpan) balanceSpan.textContent = '失败';
            alert('刷新余额失败: ' + result.message);
        }
    } catch (error) {
        if (balanceSpan) balanceSpan.textContent = '失败';
        console.error('刷新余额失败:', error);
        alert('刷新余额失败: ' + error.message);
    }
}

// 切换账号选择
function toggleAccountSelection(accountId, checked) {
    if (checked) {
        selectedAccounts.add(accountId);
    } else {
        selectedAccounts.delete(accountId);
    }
    updateSelectedCount();
}

// 更新选中数量
function updateSelectedCount() {
    document.getElementById('selectedAccountsCount').textContent = selectedAccounts.size;
}

// 启动选中账号（实例）
async function startSelectedAccounts() {
    if (selectedAccounts.size === 0) {
        alert('请先在账户列表中勾选要启动的账号');
        return;
    }
    // 先冷启动所有选中的账号（不弹窗确认）
    const promises = [];
    for (const accountId of selectedAccounts) {
        promises.push(startAccountSilent(accountId));
    }
    await Promise.all(promises);
    
    // 然后启动自动监控
    try {
        const response = await fetch('/api/tasks/start_auto_monitoring', {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            alert(`已启动 ${selectedAccounts.size} 个账号的自动监控`);
        } else {
            alert('启动自动监控失败: ' + result.message);
        }
    } catch (error) {
        console.error('启动自动监控失败:', error);
        alert('启动自动监控失败: ' + error.message);
    }
    
    loadAccounts();
    loadRunningStatus();
}

// 停止选中账号
async function stopSelectedAccounts() {
    if (selectedAccounts.size === 0) {
        alert('请先在账户列表中勾选要停止的账号');
        return;
    }
    // 并发停止所有选中的账号（不弹窗确认）
    const promises = [];
    for (const accountId of selectedAccounts) {
        promises.push(stopAccountSilent(accountId));
    }
    await Promise.all(promises);
    loadAccounts();
    loadRunningStatus();
}

// 静默启动账号（不弹窗）
async function startAccountSilent(accountId) {
    try {
        const response = await fetch(`/api/tasks/start/${accountId}`, {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            runningAccountIds.add(accountId);
        }
    } catch (error) {
        console.error(`启动账号 ${accountId} 失败:`, error);
    }
}

// 静默停止账号（不弹窗）
async function stopAccountSilent(accountId) {
    try {
        const response = await fetch(`/api/tasks/stop/${accountId}`, {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            runningAccountIds.delete(accountId);
        }
    } catch (error) {
        console.error(`停止账号 ${accountId} 失败:`, error);
    }
}

// 获取状态文本
function getStatusText(status) {
    const statusMap = {
        'active': '活跃',
        'paused': '暂停',
        'error': '错误'
    };
    return statusMap[status] || status;
}

// 存储运行中的账号ID
let runningAccountIds = new Set();

// 检查账号是否运行中
function checkAccountRunning(accountId) {
    return runningAccountIds.has(accountId);
}

// 更新运行中的账号ID集合
async function updateRunningAccounts() {
    try {
        const response = await fetch('/api/tasks/running');
        const result = await response.json();
        if (result.success) {
            runningAccountIds = new Set(result.data || []);
        }
    } catch (error) {
        console.error('更新运行账号列表失败:', error);
    }
}

// 启动账号（单个账号，保留弹窗提示）
async function startAccount(accountId) {
    try {
        const response = await fetch(`/api/tasks/start/${accountId}`, {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            alert('账号启动成功');
            runningAccountIds.add(accountId);
            loadAccounts();
            loadRunningStatus();
        } else {
            alert('启动失败: ' + result.message);
        }
    } catch (error) {
        console.error('启动账号失败:', error);
        alert('启动失败: ' + error.message);
    }
}

// 停止账号（单个账号，保留弹窗提示）
async function stopAccount(accountId) {
    try {
        const response = await fetch(`/api/tasks/stop/${accountId}`, {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            alert('账号停止成功');
            runningAccountIds.delete(accountId);
            loadAccounts();
            loadRunningStatus();
        } else {
            alert('停止失败: ' + result.message);
        }
    } catch (error) {
        console.error('停止账号失败:', error);
        alert('停止失败: ' + error.message);
    }
}

// 一键索取所有运行账号
async function redeemAllAccounts() {
    try {
        const response = await fetch('/api/tasks/redeem_all', {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            alert('已触发所有运行账号的索取，请查看日志');
        } else {
            alert('索取失败: ' + result.message);
        }
    } catch (error) {
        console.error('一键索取失败:', error);
        alert('索取失败: ' + error.message);
    }
}

// 一键出售所有运行账号的持仓
async function sellAllAccounts() {
    if (!confirm('确定要出售所有运行账号的持仓吗？这将立即卖出所有持仓，不等结算。')) {
        return;
    }
    
    try {
        const response = await fetch('/api/tasks/sell_all', {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            const message = result.message || `已触发出售，成功: ${result.sold_count || 0}, 失败: ${result.failed_count || 0}`;
            alert(message + '\n请查看日志了解详细信息');
        } else {
            alert('出售失败: ' + result.message);
        }
    } catch (error) {
        console.error('一键出售失败:', error);
        alert('出售失败: ' + error.message);
    }
}

// 手动一键下单
async function manualPlaceOrder() {
    const marketUrl = document.getElementById('marketUrl').value.trim();
    const statusDiv = document.getElementById('manualOrderStatus');
    const sideRadio = document.querySelector('input[name="orderSide"]:checked');
    
    if (!selectedAccounts.size) {
        statusDiv.innerHTML = '<span style="color: red;">请先选择要下单的账号</span>';
        return;
    }
    
    if (!sideRadio) {
        statusDiv.innerHTML = '<span style="color: red;">请选择下单方向（YES/NO）</span>';
        return;
    }
    
    const side = sideRadio.value; // "YES" 或 "NO"
    const sideLabel = side === 'YES' ? 'YES/UP (绿色)' : 'NO/DOWN (红色)';
    
    if (!confirm(`确定要为 ${selectedAccounts.size} 个选中的账号手动下单 ${sideLabel} 吗？`)) {
        return;
    }
    
    statusDiv.innerHTML = '<span style="color: blue;">正在下单，请稍候...</span>';
    
    try {
        const response = await fetch('/api/tasks/manual_order', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                market_url: marketUrl,
                account_ids: Array.from(selectedAccounts),
                side: side  // "YES" 或 "NO"
            })
        });
        
        const result = await response.json();
        if (result.success) {
            const message = result.message || `手动下单完成，成功: ${result.success_count || 0}, 失败: ${result.fail_count || 0}`;
            statusDiv.innerHTML = `<span style="color: green;">${message}</span>`;
            setTimeout(() => {
                statusDiv.innerHTML = '';
            }, 5000);
        } else {
            statusDiv.innerHTML = `<span style="color: red;">下单失败: ${result.message}</span>`;
        }
    } catch (error) {
        console.error('手动下单失败:', error);
        statusDiv.innerHTML = `<span style="color: red;">下单失败: ${error.message}</span>`;
    }
}

// 清空市场URL输入框
function clearMarketUrl() {
    document.getElementById('marketUrl').value = '';
    document.getElementById('manualOrderStatus').innerHTML = '';
}

// 删除账号
async function deleteAccount(accountId) {
    if (!confirm('确定要删除这个账号吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/accounts/${accountId}`, {method: 'DELETE'});
        const result = await response.json();
        if (result.success) {
            alert('删除成功');
            selectedAccounts.delete(accountId);
            loadAccounts();
        } else {
            alert('删除失败: ' + result.message);
        }
    } catch (error) {
        console.error('删除账号失败:', error);
        alert('删除失败: ' + error.message);
    }
}

// 显示添加账号模态框
function showAddAccountModal() {
    document.getElementById('addAccountModal').style.display = 'block';
    document.getElementById('addAccountForm').reset();
}

// 关闭模态框
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// 添加账号表单提交
document.getElementById('addAccountForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const accountData = {
        name: document.getElementById('accountName').value,
        private_key: document.getElementById('privateKey').value,
        proxy_wallet_address: document.getElementById('proxyWallet').value,
        builder_api_key: document.getElementById('builderApiKey').value,
        builder_api_secret: document.getElementById('builderApiSecret').value,
        builder_api_passphrase: document.getElementById('builderApiPassphrase').value,
        proxy_ip: document.getElementById('proxyIp').value,
        notes: document.getElementById('accountNotes').value
    };
    
    try {
        const response = await fetch('/api/accounts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(accountData)
        });
        const result = await response.json();
        if (result.success) {
            alert('账号添加成功');
            closeModal('addAccountModal');
            loadAccounts();
        } else {
            alert('添加失败: ' + result.message);
        }
    } catch (error) {
        console.error('添加账号失败:', error);
        alert('添加失败: ' + error.message);
    }
});

// 更新策略配置
async function updateStrategyConfig() {
    const config = {
        order_amount_usd: parseFloat(document.getElementById('orderAmount').value),
        price_percentage_threshold: parseFloat(document.getElementById('priceThreshold').value) / 100,
        check_time_window_minutes: parseInt(document.getElementById('timeWindow').value),
        monitor_interval: parseInt(document.getElementById('monitorInterval').value)
    };
    
    try {
        const response = await fetch('/api/strategy/config', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        const result = await response.json();
        if (result.success) {
            alert('策略配置更新成功');
        } else {
            alert('更新失败: ' + result.message);
        }
    } catch (error) {
        console.error('更新策略配置失败:', error);
        alert('更新失败: ' + error.message);
    }
}

// 加载运行状态
async function loadRunningStatus() {
    try {
        const response = await fetch('/api/tasks/running');
        const result = await response.json();
        if (result.success) {
            const statusDiv = document.getElementById('runningStatus');
            const runningIds = result.data || [];
            
            // 更新运行账号集合
            runningAccountIds = new Set(runningIds);
            
            // 获取所有账号信息
            const accountsResponse = await fetch('/api/accounts');
            const accountsResult = await accountsResponse.json();
            const allAccounts = accountsResult.success ? accountsResult.data : [];
            
            if (runningIds.length > 0 || allAccounts.length > 0) {
                let html = '<div class="running-accounts-list">';
                
                // 显示正在运行的账号
                if (runningIds.length > 0) {
                    runningIds.forEach(accountId => {
                        const account = allAccounts.find(acc => acc.id === accountId);
                        const accountName = account ? (account.name || '未命名') : `账号${accountId}`;
                        const accountAddress = account ? (account.proxy_wallet_address || (account.private_key ? '0x' + account.private_key.slice(-8) : '未设置')) : '未知';
                        
                        html += `
                            <div class="running-account-item">
                                <div class="account-info">
                                    <strong>账号 ${accountId}: ${accountName}</strong>
                                    <span class="account-address">${accountAddress}</span>
                                </div>
                                <div class="account-actions">
                                    <button class="btn btn-sm btn-danger" onclick="stopAccount(${accountId})">停止</button>
                                </div>
                            </div>
                        `;
                    });
                }
                
                // 显示未运行的账号（可选，如果用户想要快速启动）
                // 这里只显示前5个未运行的账号，避免列表过长
                const stoppedAccounts = allAccounts
                    .filter(acc => !runningIds.includes(acc.id))
                    .slice(0, 5);
                
                if (stoppedAccounts.length > 0 && runningIds.length === 0) {
                    // 如果没有运行中的账号，显示一些未运行的账号供快速启动
                    stoppedAccounts.forEach(account => {
                        html += `
                            <div class="running-account-item" style="border-left-color: #6c757d; opacity: 0.8;">
                                <div class="account-info">
                                    <strong>账号 ${account.id}: ${account.name || '未命名'}</strong>
                                    <span class="account-address">${account.proxy_wallet_address || (account.private_key ? '0x' + account.private_key.slice(-8) : '未设置')}</span>
                                </div>
                                <div class="account-actions">
                                    <button class="btn btn-sm btn-success" onclick="startAccount(${account.id})">启动</button>
                                </div>
                            </div>
                        `;
                    });
                }
                
                html += '</div>';
                statusDiv.innerHTML = html;
            } else {
                statusDiv.innerHTML = '<p>当前没有账号，请先添加账号</p>';
            }
        }
    } catch (error) {
        console.error('加载运行状态失败:', error);
    }
}

// 更新调度线程状态显示
async function updateSchedulerStatus() {
    try {
        const response = await fetch('/api/tasks/scheduler_status');
        const result = await response.json();
        if (!result.success) return;

        const data = result.data || {};
        const running = !!data.running;
        const runningAccounts = data.running_accounts || [];

        const el = document.getElementById('schedulerStatus');
        if (!el) return;

        const statusText = running ? '运行中' : '已停止';
        const statusClass = running ? 'status-running' : 'status-stopped';
        const accountsText = runningAccounts.length > 0
            ? `当前运行账号: ${runningAccounts.join(', ')}`
            : '当前无运行账号';

        el.innerHTML = `
            <div class="scheduler-status-row">
                <span class="scheduler-label">调度线程状态:</span>
                <span class="scheduler-value ${statusClass}">[调度] ${statusText}</span>
                <span class="scheduler-accounts">${accountsText}</span>
            </div>
        `;
    } catch (error) {
        console.error('更新调度线程状态失败:', error);
    }
}

// 编辑账号
async function editAccount(accountId) {
    try {
        // 获取账号信息
        const response = await fetch(`/api/accounts`);
        const result = await response.json();
        if (!result.success) {
            alert('获取账号信息失败');
            return;
        }
        
        const account = result.data.find(acc => acc.id === accountId);
        if (!account) {
            alert('账号不存在');
            return;
        }
        
        // 填充表单
        document.getElementById('editAccountId').value = account.id;
        document.getElementById('editAccountName').value = account.name || '';
        document.getElementById('editPrivateKey').value = account.private_key || '';
        document.getElementById('editProxyWallet').value = account.proxy_wallet_address || '';
        document.getElementById('editBuilderApiKey').value = account.builder_api_key || '';
        document.getElementById('editBuilderApiSecret').value = account.builder_api_secret || '';
        document.getElementById('editBuilderApiPassphrase').value = account.builder_api_passphrase || '';
        document.getElementById('editProxyIp').value = account.proxy_ip || '';
        document.getElementById('editAccountNotes').value = account.notes || '';
        
        // 显示模态框
        document.getElementById('editAccountModal').style.display = 'block';
    } catch (error) {
        console.error('加载账号信息失败:', error);
        alert('加载账号信息失败: ' + error.message);
    }
}

// 编辑账号表单提交
document.getElementById('editAccountForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const accountId = parseInt(document.getElementById('editAccountId').value);
    const accountData = {
        name: document.getElementById('editAccountName').value,
        private_key: document.getElementById('editPrivateKey').value,
        proxy_wallet_address: document.getElementById('editProxyWallet').value,
        builder_api_key: document.getElementById('editBuilderApiKey').value,
        builder_api_secret: document.getElementById('editBuilderApiSecret').value,
        builder_api_passphrase: document.getElementById('editBuilderApiPassphrase').value,
        proxy_ip: document.getElementById('editProxyIp').value,
        notes: document.getElementById('editAccountNotes').value
    };
    
    try {
        const response = await fetch(`/api/accounts/${accountId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(accountData)
        });
        const result = await response.json();
        if (result.success) {
            alert('账号更新成功');
            closeModal('editAccountModal');
            loadAccounts();
        } else {
            alert('更新失败: ' + result.message);
        }
    } catch (error) {
        console.error('更新账号失败:', error);
        alert('更新失败: ' + error.message);
    }
});

