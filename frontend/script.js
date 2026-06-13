// TTS语音评测系统前端脚本

// 全局变量
let currentSessionId = null;
let websocket = null;
let selectedFiles = [];
let currentResults = null;

// 工具函数：检查session_id是否有效
function isValidSessionId(sessionId) {
    return sessionId && 
           sessionId !== 'null' && 
           sessionId !== 'undefined' &&
           typeof sessionId === 'string' &&
           sessionId.trim() !== '' &&
           sessionId.trim() !== 'null';
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 确保currentSessionId初始化为null
    currentSessionId = null;
    console.log('页面加载完成，currentSessionId初始化为:', currentSessionId);
    
    initializeApp();
});

function initializeApp() {
    // 设置事件监听器
    setupEventListeners();
    
    // 初始化WebSocket连接
    initWebSocket();
    
    // 加载系统信息
    loadSystemInfo();
    
    // 加载会话列表
    refreshSessions();
    
    // 加载历史记录
    refreshHistory();
}

// 设置事件监听器
function setupEventListeners() {
    // 导航栏点击
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tab = this.getAttribute('data-tab');
            switchTab(tab);
        });
    });
    
    // 评测方式切换
    document.querySelectorAll('.method-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            switchMethod(this.getAttribute('data-method'));
        });
    });
    
    // 文件上传
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    fileInput.addEventListener('change', handleFileSelect);
}

// 标签页切换
function switchTab(tabName) {
    // 更新导航栏
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // 切换内容
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // 特殊处理
    if (tabName === 'results') {
        // 清理现有图表
        destroyExistingCharts();
        refreshSessions();
    } else if (tabName === 'history') {
        refreshHistory();
    }
}

// 评测方式切换
function switchMethod(method) {
    // 更新标签
    document.querySelectorAll('.method-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-method="${method}"]`).classList.add('active');
    
    // 切换内容
    document.querySelectorAll('.method-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${method}-method`).classList.add('active');
}

// WebSocket连接
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log('初始化WebSocket连接:', wsUrl);
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function() {
        console.log('WebSocket连接已建立');
        showToast('WebSocket连接已建立', 'success');
        
        // 发送心跳
        setInterval(() => {
            if (websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({type: 'ping'}));
            }
        }, 30000);
    };
    
    websocket.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('收到原始WebSocket消息:', event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error('WebSocket消息解析错误:', e, '原始消息:', event.data);
        }
    };
    
    websocket.onclose = function(event) {
        console.log('WebSocket连接已关闭', event.code, event.reason);
        showToast('WebSocket连接已断开，正在重连...', 'warning');
        
        // 重连逻辑
        setTimeout(() => {
            console.log('尝试重新连接WebSocket...');
            initWebSocket();
        }, 5000);
    };
    
    websocket.onerror = function(error) {
        console.error('WebSocket错误:', error);
        showToast('WebSocket连接错误', 'error');
    };
}

// 处理WebSocket消息
function handleWebSocketMessage(data) {
    console.log('收到WebSocket消息:', data);
    console.log('当前session_id:', currentSessionId);
    
    if (data.type === 'progress') {
        // 检查收到的session_id有效性
        if (!isValidSessionId(data.session_id)) {
            console.log('忽略消息 - session_id无效:', data.session_id);
            return;
        }
        
        // 如果没有设置currentSessionId，或者session_id匹配，都处理进度更新
        if (!currentSessionId || data.session_id === currentSessionId) {
            console.log('处理进度更新:', data.data);
            updateProgress(data.data);
        } else {
            console.log('忽略消息 - session_id不匹配:', data.session_id, 'vs', currentSessionId);
        }
    } else if (data.type === 'pong') {
        // 心跳响应
        console.log('收到心跳响应');
    } else {
        console.log('忽略未知消息类型:', data.type);
    }
}

// 文件拖拽处理
function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    processSelectedFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    processSelectedFiles(files);
}

// 处理选择的文件
function processSelectedFiles(files) {
    selectedFiles = files.filter(file => {
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        return ['.wav', '.pcm', '.mp3', '.flac', '.txt'].includes(extension);
    });
    
    if (selectedFiles.length === 0) {
        showToast('请选择支持的文件格式', 'warning');
        return;
    }
    
    displaySelectedFiles();
}

// 显示选择的文件
function displaySelectedFiles() {
    const fileList = document.getElementById('file-list');
    const selectedFilesDiv = document.getElementById('selected-files');
    
    selectedFilesDiv.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        const isAudio = ['.wav', '.pcm', '.mp3', '.flac'].includes(extension);
        const fileType = isAudio ? 'audio' : 'text';
        
        fileItem.innerHTML = `
            <div class="file-info">
                <span class="file-type ${fileType}">${extension.substring(1).toUpperCase()}</span>
                <span class="file-name">${file.name}</span>
                <span class="file-size">(${formatFileSize(file.size)})</span>
            </div>
            <button class="btn btn-danger btn-small" onclick="removeFile(${index})">
                <i class="fas fa-trash"></i>
            </button>
        `;
        
        selectedFilesDiv.appendChild(fileItem);
    });
    
    fileList.style.display = selectedFiles.length > 0 ? 'block' : 'none';
}

// 移除文件
function removeFile(index) {
    selectedFiles.splice(index, 1);
    displaySelectedFiles();
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 浏览目录
async function browseDirectory() {
    try {
        // 打开目录浏览器模态框
        showDirectoryBrowser();
    } catch (error) {
        console.error('Directory browse error:', error);
        showToast('目录浏览失败: ' + error.message, 'error');
    }
}

// 显示目录浏览器
async function showDirectoryBrowser(currentPath = null) {
    try {
        // 获取目录内容
        const response = await fetch(`/api/browse-directory${currentPath ? '?path=' + encodeURIComponent(currentPath) : ''}`);
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || '获取目录内容失败');
        }
        
        // 创建模态框
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content directory-browser">
                <div class="modal-header">
                    <h3><i class="fas fa-folder-open"></i> 选择目录</h3>
                    <button class="close-btn" onclick="closeModal(this)">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="current-path">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${result.data.current_path}</span>
                    </div>
                    <div class="directory-list">
                        ${result.data.items.map(item => `
                            <div class="directory-item ${item.type}" data-path="${item.path}" data-type="${item.type}">
                                <i class="fas ${getItemIcon(item)}"></i>
                                <span class="item-name">${item.name}</span>
                                ${item.size !== null ? `<span class="item-size">${formatFileSize(item.size)}</span>` : ''}
                                <div class="item-actions">
                                    ${item.type === 'directory' || item.type === 'parent' ? 
                                        `<button class="btn btn-sm" onclick="navigateToDirectory('${item.path}')">
                                            <i class="fas fa-arrow-right"></i>
                                        </button>` : ''
                                    }
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeModal(this)">取消</button>
                    <button class="btn btn-primary" onclick="selectCurrentDirectory('${result.data.current_path}')">
                        选择此目录
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.style.display = 'block';
        
    } catch (error) {
        console.error('Show directory browser error:', error);
        showToast('显示目录浏览器失败: ' + error.message, 'error');
    }
}

// 获取文件/目录图标
function getItemIcon(item) {
    if (item.type === 'parent') return 'fa-level-up-alt';
    if (item.type === 'directory') return 'fa-folder';
    
    const ext = item.extension?.toLowerCase();
    switch (ext) {
        case '.wav':
        case '.mp3':
        case '.flac':
        case '.m4a':
        case '.aac':
        case '.ogg':
            return 'fa-file-audio';
        case '.txt':
            return 'fa-file-alt';
        default:
            return 'fa-file';
    }
}

// 导航到目录
async function navigateToDirectory(path) {
    // 关闭当前模态框
    const currentModal = document.querySelector('.modal');
    if (currentModal) {
        currentModal.remove();
    }
    
    // 显示新的目录内容
    await showDirectoryBrowser(path);
}

// 选择当前目录
function selectCurrentDirectory(path) {
    document.getElementById('directory-path').value = path;
    
    // 关闭模态框
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.remove();
    }
    
    showToast('目录已选择: ' + path, 'success');
}

// 关闭模态框
function closeModal(button) {
    const modal = button.closest('.modal');
    if (modal) {
        modal.remove();
    }
}

// 开始评测
async function startEvaluation() {
    const activeMethod = document.querySelector('.method-tab.active')?.getAttribute('data-method');
    const taskName = document.getElementById('task-name').value.trim();
    
    console.log('开始评测:', { activeMethod, taskName });
    
    if (!activeMethod) {
        showToast('请选择评测方法', 'error');
        return;
    }
    
    try {
        showLoading(true);
        
        if (activeMethod === 'upload') {
            if (selectedFiles.length === 0) {
                throw new Error('请选择要上传的文件');
            }
            
            console.log('使用上传方法，文件数:', selectedFiles.length);
            
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            if (taskName) {
                formData.append('task_name', taskName);
            }
            
            console.log('发送上传请求...');
            const response = await fetch('/api/upload-directory', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            console.log('上传响应:', result);
            
            if (result.success) {
                currentSessionId = result.session_id;
                console.log('设置currentSessionId:', currentSessionId);
                showProgressSection();
                console.log('进度区域已显示');
                showToast(result.message, 'success');
                
                // 立即开始监听进度更新
                console.log('开始监听进度更新，session_id:', currentSessionId);
            } else {
                throw new Error(result.message || '上传失败');
            }
            
        } else if (activeMethod === 'local') {
            const directoryPath = document.getElementById('directory-path').value.trim();
            
            console.log('使用本地目录方法，路径:', directoryPath);
            
            if (!directoryPath) {
                throw new Error('请输入目录路径');
            }
            
            const formData = new FormData();
            formData.append('directory_path', directoryPath);
            
            if (taskName) {
                formData.append('task_name', taskName);
            }
            
            console.log('发送评测请求...');
            const response = await fetch('/api/start-evaluation', {
                method: 'POST',
                body: formData
            });
            
            console.log('响应状态:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('评测响应:', result);
            
            if (result.success) {
                currentSessionId = result.session_id;
                console.log('设置currentSessionId:', currentSessionId);
                showProgressSection();
                console.log('进度区域已显示');
                showToast(result.message, 'success');
            } else {
                throw new Error(result.message || '启动评测失败');
            }
        }
        
    } catch (error) {
        console.error('评测启动错误:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 显示进度区域
function showProgressSection() {
    console.log('显示进度区域');
    
    const evaluationSection = document.querySelector('.evaluation-section');
    const progressSection = document.getElementById('progress-section');
    
    if (evaluationSection) {
        evaluationSection.style.display = 'none';
        console.log('隐藏评测区域');
    } else {
        console.error('评测区域元素未找到');
    }
    
    if (progressSection) {
        progressSection.style.display = 'block';
        console.log('显示进度区域');
        
        // 初始化进度条状态
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const currentStage = document.getElementById('current-stage');
        const processedFiles = document.getElementById('processed-files');
        const estimatedTime = document.getElementById('estimated-time');
        
        if (progressFill) progressFill.style.width = '0%';
        if (progressText) progressText.textContent = '0%';
        if (currentStage) currentStage.textContent = '准备中...';
        if (processedFiles) processedFiles.textContent = '0 / 0';
        if (estimatedTime) estimatedTime.textContent = '计算中...';
        
        console.log('进度条已初始化');
    } else {
        console.error('进度区域元素未找到');
    }
}

// 更新进度
function updateProgress(progressData) {
    console.log('更新进度:', progressData);
    
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const currentStage = document.getElementById('current-stage');
    const processedFiles = document.getElementById('processed-files');
    const estimatedTime = document.getElementById('estimated-time');
    
    if (!progressFill || !progressText) {
        console.error('进度条元素未找到');
        return;
    }
    
    const percentage = Math.round(progressData.progress_percentage || 0);
    
    // 更新进度条
    progressFill.style.width = `${percentage}%`;
    progressText.textContent = `${percentage}%`;
    
    // 更新其他信息
    if (currentStage) {
        currentStage.textContent = progressData.current_stage || '处理中...';
    }
    
    if (processedFiles) {
        processedFiles.textContent = `${progressData.current_step || 0} / ${progressData.total_steps || 0}`;
    }
    
    if (estimatedTime && progressData.estimated_time_remaining) {
        const minutes = Math.ceil(progressData.estimated_time_remaining / 60);
        estimatedTime.textContent = `约 ${minutes} 分钟`;
    } else if (estimatedTime) {
        estimatedTime.textContent = '计算中...';
    }
    
    console.log(`进度已更新: ${percentage}%`);
    
    // 检查是否完成 - 只有在有有效session_id时才检查
    if (percentage >= 100 && isValidSessionId(currentSessionId)) {
        console.log('任务已完成，等待2秒后检查状态，session_id:', currentSessionId);
        setTimeout(() => {
            checkTaskCompletion();
        }, 2000);
    } else if (percentage >= 100) {
        console.log('任务完成但session_id无效，跳过状态检查，currentSessionId:', currentSessionId);
    }
}

// 检查任务完成状态
async function checkTaskCompletion() {
    // 使用工具函数检查session_id有效性
    if (!isValidSessionId(currentSessionId)) {
        console.warn('无效的session_id，跳过任务状态检查:', currentSessionId);
        return;
    }
    
    try {
        console.log('检查任务状态，session_id:', currentSessionId);
        const response = await fetch(`/api/task-status/${currentSessionId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.data.status === 'completed') {
            // 隐藏进度条
            document.getElementById('progress-section').style.display = 'none';
            document.getElementById('view-results-btn').style.display = 'inline-flex';
            showToast('评测任务已完成！', 'success');
            
            // 重置表单
            resetEvaluationForm();
        } else if (result.data.status === 'failed') {
            // 隐藏进度条
            document.getElementById('progress-section').style.display = 'none';
            showToast('评测任务失败：' + (result.data.error || '未知错误'), 'error');
            
            // 重置表单
            resetEvaluationForm();
        }
    } catch (error) {
        console.error('检查任务状态失败:', error, '当前session_id:', currentSessionId);
        // 隐藏进度条
        const progressSection = document.getElementById('progress-section');
        if (progressSection) {
            progressSection.style.display = 'none';
        }
        showToast('测评任务状态检测失败', 'error');
        
        // 重置无效的session_id
        currentSessionId = null;
    }
}

// 重置评测表单
function resetEvaluationForm() {
    console.log('重置评测表单');
    
    const evaluationSection = document.querySelector('.evaluation-section');
    if (evaluationSection) {
        evaluationSection.style.display = 'block';
    }
    
    const progressSection = document.getElementById('progress-section');
    if (progressSection) {
        progressSection.style.display = 'none';
    }
    
    currentSessionId = null;
    console.log('已重置currentSessionId');
}

// 取消任务
async function cancelTask() {
    if (!isValidSessionId(currentSessionId)) {
        console.warn('无法取消任务，session_id无效:', currentSessionId);
        showToast('无法取消任务：会话ID无效', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/cancel-task/${currentSessionId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('任务已取消', 'info');
            resetForm();
        } else {
            throw new Error(result.message || '取消任务失败');
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 查看结果
function viewResults() {
    if (isValidSessionId(currentSessionId)) {
        switchTab('results');
        document.getElementById('session-select').value = currentSessionId;
        loadSessionResults();
    } else {
        console.warn('无法查看结果，session_id无效:', currentSessionId);
        showToast('无法查看结果：会话ID无效', 'warning');
    }
}

// 重置表单
function resetForm() {
    selectedFiles = [];
    currentSessionId = null;
    
    document.getElementById('file-input').value = '';
    document.getElementById('directory-path').value = '';
    document.getElementById('task-name').value = '';
    document.getElementById('file-list').style.display = 'none';
    document.getElementById('selected-files').innerHTML = '';
    
    document.querySelector('.evaluation-section').style.display = 'block';
    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('view-results-btn').style.display = 'none';
}

// 加载系统信息
async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system-info');
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            document.getElementById('asr-status').textContent = 
                data.funasr_available ? '正常' : '未安装';
            document.getElementById('active-tasks').textContent = data.active_sessions;
            document.getElementById('total-sessions').textContent = data.total_sessions;
        }
    } catch (error) {
        console.error('加载系统信息失败:', error);
    }
}

// 刷新会话列表
async function refreshSessions() {
    try {
        const response = await fetch('/api/sessions');
        const result = await response.json();
        
        if (result.success) {
            const sessionSelect = document.getElementById('session-select');
            const currentValue = sessionSelect.value;
            
            sessionSelect.innerHTML = '<option value="">请选择会话...</option>';
            
            result.data.forEach(session => {
                const option = document.createElement('option');
                option.value = session.session_id;
                option.textContent = `${session.task_name || session.session_id} - ${new Date(session.created_time).toLocaleString()}`;
                sessionSelect.appendChild(option);
            });
            
            // 恢复选择
            if (currentValue) {
                sessionSelect.value = currentValue;
            }
        }
    } catch (error) {
        console.error('刷新会话列表失败:', error);
    }
}

// 加载会话结果
async function loadSessionResults() {
    const sessionId = document.getElementById('session-select').value;
    
    // 清理现有图表
    destroyExistingCharts();
    
    if (!sessionId) {
        currentSessionId = null;  // 清空当前会话ID
        document.getElementById('results-display').style.display = 'none';
        document.getElementById('empty-results').style.display = 'block';
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch(`/api/task-results/${sessionId}`);
        const result = await response.json();
        
        if (result.success && result.data.results) {
            currentSessionId = sessionId;  // 设置当前会话ID用于音频播放
            currentResults = result.data.results;
            displayResults(result.data);
            document.getElementById('results-display').style.display = 'block';
            document.getElementById('empty-results').style.display = 'none';
        } else {
            throw new Error('结果数据不完整');
        }
        
    } catch (error) {
        showToast('加载结果失败: ' + error.message, 'error');
        document.getElementById('results-display').style.display = 'none';
        document.getElementById('empty-results').style.display = 'block';
    } finally {
        showLoading(false);
    }
}

// 显示结果
function displayResults(data) {
    // 显示汇总统计
    displaySummaryStats(data.statistics);
    
    // 显示图表
    displayCharts(data.results);
    
    // 显示详细结果表格
    displayDetailedResults(data.results);
}

// 显示汇总统计
function displaySummaryStats(statistics) {
    const statsGrid = document.getElementById('stats-grid');
    
    if (!statistics) {
        statsGrid.innerHTML = '<p>暂无统计数据</p>';
        return;
    }
    
    const stats = [
        { label: '总样本数', value: statistics.total_samples, format: 'number' },
        { label: '有效样本数', value: statistics.valid_samples, format: 'number' },
        { label: '平均CER', value: statistics.avg_cer, format: 'percentage' },
        { label: '平均WER', value: statistics.avg_wer, format: 'percentage' },
        { label: '平均相似度', value: statistics.avg_similarity, format: 'percentage' },
        { label: '完全匹配率', value: statistics.exact_match_rate, format: 'percentage' }
    ];
    
    statsGrid.innerHTML = stats.map(stat => `
        <div class="stat-card">
            <div class="stat-value">${formatStatValue(stat.value, stat.format)}</div>
            <div class="stat-label">${stat.label}</div>
        </div>
    `).join('');
}

// 格式化统计值
function formatStatValue(value, format) {
    if (value === undefined || value === null) return 'N/A';
    
    switch (format) {
        case 'percentage':
            return (value * 100).toFixed(2) + '%';
        case 'number':
            return value.toLocaleString();
        default:
            return value.toFixed(2);
    }
}

// 显示图表
function displayCharts(results) {
    // 清理现有图表
    destroyExistingCharts();
    
    // CER分布图
    displayCERChart(results);
    
    // WER分布图
    displayWERChart(results);
}

// 销毁现有图表
function destroyExistingCharts() {
    // 销毁CER图表
    if (window.cerChart) {
        window.cerChart.destroy();
        window.cerChart = null;
    }
    
    // 销毁WER图表
    if (window.werChart) {
        window.werChart.destroy();
        window.werChart = null;
    }
    
    // 清理canvas元素
    const cerCanvas = document.getElementById('cer-chart');
    const werCanvas = document.getElementById('wer-chart');
    
    if (cerCanvas) {
        cerCanvas.width = cerCanvas.width; // 重置canvas
    }
    if (werCanvas) {
        werCanvas.width = werCanvas.width; // 重置canvas
    }
}

// 显示CER图表
function displayCERChart(results) {
    const canvas = document.getElementById('cer-chart');
    const ctx = canvas.getContext('2d');
    
    // 计算CER分布
    const cerValues = results.filter(r => r.success && isFinite(r.cer)).map(r => r.cer);
    const cerDistribution = calculateDistribution(cerValues, 10);
    
    window.cerChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: cerDistribution.labels,
            datasets: [{
                label: 'CER分布',
                data: cerDistribution.values,
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'CER错误率分布'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// 显示WER图表
function displayWERChart(results) {
    const canvas = document.getElementById('wer-chart');
    const ctx = canvas.getContext('2d');
    
    // 计算WER分布
    const werValues = results.filter(r => r.success && isFinite(r.wer)).map(r => r.wer);
    const werDistribution = calculateDistribution(werValues, 10);
    
    window.werChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: werDistribution.labels,
            datasets: [{
                label: 'WER分布',
                data: werDistribution.values,
                backgroundColor: 'rgba(118, 75, 162, 0.6)',
                borderColor: 'rgba(118, 75, 162, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'WER错误率分布'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// 计算分布
function calculateDistribution(values, bins) {
    if (values.length === 0) {
        return { labels: [], values: [] };
    }
    
    const min = Math.min(...values);
    const max = Math.max(...values);
    const step = (max - min) / bins;
    
    const labels = [];
    const counts = new Array(bins).fill(0);
    
    for (let i = 0; i < bins; i++) {
        const start = min + i * step;
        const end = min + (i + 1) * step;
        labels.push(`${(start * 100).toFixed(1)}-${(end * 100).toFixed(1)}%`);
    }
    
    values.forEach(value => {
        const binIndex = Math.min(Math.floor((value - min) / step), bins - 1);
        counts[binIndex]++;
    });
    
    return { labels, values: counts };
}

// 显示详细结果表格
function displayDetailedResults(results) {
    const tbody = document.getElementById('results-tbody');
    
    tbody.innerHTML = results.map((result, index) => `
        <tr>
            <td>${index + 1}</td>
            <td title="${result.audio_file}">${getFileName(result.audio_file)}</td>
            <td class="text-cell" title="${result.original_text}">
                ${truncateText(result.original_text, 50)}
            </td>
            <td class="text-cell" title="${result.recognized_text}">
                ${truncateText(result.recognized_text, 50)}
            </td>
            <td>${result.success ? (result.cer * 100).toFixed(2) + '%' : 'N/A'}</td>
            <td>${result.success ? (result.wer * 100).toFixed(2) + '%' : 'N/A'}</td>
            <td>${result.success ? (result.similarity * 100).toFixed(2) + '%' : 'N/A'}</td>
            <td>
                <span class="status-badge ${getStatusClass(result)}">
                    ${getStatusText(result)}
                </span>
            </td>
            <td>
                ${result.success ? `
                    <button class="btn btn-small btn-secondary" onclick="showDiffModal(${index})">
                        <i class="fas fa-eye"></i> 对比
                    </button>
                ` : `
                    <span title="${result.error}">
                        <i class="fas fa-exclamation-triangle" style="color: #dc3545;"></i>
                    </span>
                `}
            </td>
        </tr>
    `).join('');
}

// 获取文件名
function getFileName(filepath) {
    return filepath.split(/[\\/]/).pop();
}

// 截断文本
function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// 获取状态类名
function getStatusClass(result) {
    if (!result.success) return 'status-failed';
    if (result.exact_match) return 'status-exact';
    return 'status-success';
}

// 获取状态文本
function getStatusText(result) {
    if (!result.success) return '失败';
    if (result.exact_match) return '完全匹配';
    return '成功';
}

// 显示差异对比模态框
function showDiffModal(index) {
    if (!currentResults || !currentResults[index]) return;
    
    const result = currentResults[index];
    
    document.getElementById('original-text').textContent = result.original_text;
    document.getElementById('recognized-text').textContent = result.recognized_text;
    
    // 设置音频播放器
    setupAudioPlayer(result);
    
    // 显示差异详情
    const diffDetailsDiv = document.getElementById('diff-details-content');
    
    if (result.diff_details && result.diff_details.length > 0) {
        diffDetailsDiv.innerHTML = result.diff_details.map(diff => `
            <div class="diff-operation diff-${diff.operation}">
                <strong>${getOperationName(diff.operation)}:</strong>
                "${diff.reference_text}" → "${diff.hypothesis_text}"
            </div>
        `).join('');
    } else {
        diffDetailsDiv.innerHTML = '<p>暂无详细差异信息</p>';
    }
    
    document.getElementById('diff-modal').style.display = 'block';
}

// 设置音频播放器
function setupAudioPlayer(result) {
    console.log('setupAudioPlayer called with result:', result);
    console.log('currentSessionId:', currentSessionId);
    
    const audioPlayer = document.getElementById('audio-player');
    const audioFilename = document.getElementById('audio-filename');
    const audioDuration = document.getElementById('audio-duration');
    
    if (result.audio_file && currentSessionId) {
        // 构建音频文件URL
        const audioUrl = `/api/sessions/${currentSessionId}/audio/${encodeURIComponent(result.audio_file)}`;
        console.log('构建的音频URL:', audioUrl);
        
        audioPlayer.src = audioUrl;
        audioFilename.textContent = result.audio_file;
        
        // 监听音频元数据加载完成事件，获取时长
        audioPlayer.addEventListener('loadedmetadata', function() {
            const duration = formatDuration(audioPlayer.duration);
            audioDuration.textContent = duration;
        });
        
        // 监听音频加载错误
        audioPlayer.addEventListener('error', function() {
            console.error('音频加载错误:', audioPlayer.error);
            audioFilename.textContent = `${result.audio_file} (加载失败)`;
            audioDuration.textContent = '--:--';
            showToast('音频文件加载失败', 'error');
        });
        
        // 显示音频控件
        audioPlayer.style.display = 'block';
    } else {
        console.log('无音频文件或无当前会话ID - audio_file:', result.audio_file, 'currentSessionId:', currentSessionId);
        // 隐藏音频控件
        audioPlayer.style.display = 'none';
        audioFilename.textContent = '无音频文件';
        audioDuration.textContent = '--:--';
    }
}

// 格式化音频时长
function formatDuration(seconds) {
    if (isNaN(seconds) || !isFinite(seconds)) {
        return '--:--';
    }
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// 获取操作名称
function getOperationName(operation) {
    const names = {
        'equal': '匹配',
        'insert': '插入',
        'delete': '删除',
        'replace': '替换'
    };
    return names[operation] || operation;
}

// 关闭差异对比模态框
function closeDiffModal() {
    // 停止音频播放
    const audioPlayer = document.getElementById('audio-player');
    if (audioPlayer && !audioPlayer.paused) {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
    }
    
    document.getElementById('diff-modal').style.display = 'none';
}

// 过滤结果
function filterResults() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const filterValue = document.getElementById('filter-select').value;
    
    const rows = document.querySelectorAll('#results-tbody tr');
    
    rows.forEach(row => {
        const cells = row.cells;
        const fileName = cells[1].textContent.toLowerCase();
        const originalText = cells[2].textContent.toLowerCase();
        const recognizedText = cells[3].textContent.toLowerCase();
        const statusBadge = cells[7].querySelector('.status-badge');
        
        // 搜索过滤
        const matchesSearch = !searchTerm || 
            fileName.includes(searchTerm) || 
            originalText.includes(searchTerm) || 
            recognizedText.includes(searchTerm);
        
        // 状态过滤
        let matchesFilter = true;
        if (filterValue) {
            const statusClass = statusBadge.className;
            matchesFilter = statusClass.includes(`status-${filterValue}`);
        }
        
        row.style.display = matchesSearch && matchesFilter ? '' : 'none';
    });
}

// 导出结果
async function exportResults() {
    const sessionId = document.getElementById('session-select').value;
    
    if (!sessionId) {
        showToast('请先选择会话', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/download-results/${sessionId}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `evaluation_results_${sessionId}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('结果已导出', 'success');
        } else {
            throw new Error('导出失败');
        }
    } catch (error) {
        showToast('导出失败: ' + error.message, 'error');
    }
}

// 刷新历史记录
async function refreshHistory() {
    try {
        const response = await fetch('/api/sessions');
        const result = await response.json();
        
        if (result.success) {
            displayHistory(result.data);
        }
    } catch (error) {
        console.error('刷新历史记录失败:', error);
    }
}

// 显示历史记录
function displayHistory(sessions) {
    const historyList = document.getElementById('history-list');
    const emptyHistory = document.getElementById('empty-history');
    
    if (sessions.length === 0) {
        historyList.style.display = 'none';
        emptyHistory.style.display = 'block';
        return;
    }
    
    historyList.style.display = 'block';
    emptyHistory.style.display = 'none';
    
    historyList.innerHTML = sessions.map(session => `
        <div class="history-item">
            <div class="history-header">
                <div class="history-title">${session.task_name || session.session_id}</div>
                <div class="history-date">${new Date(session.created_time).toLocaleString()}</div>
            </div>
            <div class="history-details">
                <div class="history-detail">
                    <span>状态:</span>
                    <span class="status-badge ${getSessionStatusClass(session.status)}">
                        ${getSessionStatusText(session.status)}
                    </span>
                </div>
                <div class="history-detail">
                    <span>文件数:</span>
                    <span>${session.total_files || 'N/A'}</span>
                </div>
                <div class="history-detail">
                    <span>处理时间:</span>
                    <span>${formatProcessingTime(session.total_processing_time)}</span>
                </div>
            </div>
            <div class="history-actions">
                ${session.has_results ? `
                    <button class="btn btn-small btn-secondary" onclick="viewSessionResults('${session.session_id}')">
                        <i class="fas fa-eye"></i> 查看
                    </button>
                ` : ''}
                <button class="btn btn-small btn-danger" onclick="deleteSession('${session.session_id}')">
                    <i class="fas fa-trash"></i> 删除
                </button>
            </div>
        </div>
    `).join('');
}

// 获取会话状态类名
function getSessionStatusClass(status) {
    switch (status) {
        case 'completed': return 'status-success';
        case 'failed': return 'status-failed';
        case 'running': return 'status-exact';
        default: return 'status-success';
    }
}

// 获取会话状态文本
function getSessionStatusText(status) {
    const statusTexts = {
        'completed': '已完成',
        'failed': '失败',
        'running': '运行中',
        'cancelled': '已取消'
    };
    return statusTexts[status] || status;
}

// 格式化处理时间
function formatProcessingTime(seconds) {
    if (!seconds) return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

// 查看会话结果
function viewSessionResults(sessionId) {
    switchTab('results');
    document.getElementById('session-select').value = sessionId;
    loadSessionResults();
}

// 删除会话
async function deleteSession(sessionId) {
    if (!confirm('确定要删除这个会话吗？此操作不可撤销。')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('会话已删除', 'success');
            refreshHistory();
            refreshSessions();
        } else {
            throw new Error(result.message || '删除失败');
        }
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// 清空历史
async function clearHistory() {
    if (!confirm('确定要清空所有历史记录吗？此操作不可撤销。')) {
        return;
    }
    
    try {
        const response = await fetch('/api/sessions');
        const result = await response.json();
        
        if (result.success) {
            const deletePromises = result.data.map(session => 
                fetch(`/api/sessions/${session.session_id}`, { method: 'DELETE' })
            );
            
            await Promise.all(deletePromises);
            
            showToast('历史记录已清空', 'success');
            refreshHistory();
            refreshSessions();
        }
    } catch (error) {
        showToast('清空失败: ' + error.message, 'error');
    }
}

// 显示加载指示器
function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}

// 显示提示消息
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    toast.innerHTML = `
        <div>${message}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // 自动移除
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

// 点击模态框外部关闭
document.addEventListener('click', function(event) {
    const modal = document.getElementById('diff-modal');
    if (event.target === modal) {
        closeDiffModal();
    }
});

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，正在初始化...');
    
    // 检查关键元素是否存在
    const startBtn = document.getElementById('start-evaluation-btn');
    if (startBtn) {
        console.log('开始评测按钮找到');
        // 确保按钮没有被禁用
        startBtn.disabled = false;
    } else {
        console.error('开始评测按钮未找到');
    }
    
    // 检查方法选项卡
    const methodTabs = document.querySelectorAll('.method-tab');
    console.log('找到方法选项卡数量:', methodTabs.length);
    
    // 确保有活动的方法选项卡
    const activeTab = document.querySelector('.method-tab.active');
    if (!activeTab && methodTabs.length > 0) {
        console.log('没有活动选项卡，设置第一个为活动');
        methodTabs[0].classList.add('active');
        const method = methodTabs[0].getAttribute('data-method');
        if (method) {
            switchUploadMethod(method);
        }
    }
    
    console.log('页面初始化完成');
});
