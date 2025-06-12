// 使用window对象来存储全局状态
if (!window.autoDetection) {
    window.autoDetection = {
        isRunning: false,
        serverUrl: '',
        interval: null,
        retryCount: 0,
        maxRetries: 3,
        retryDelay: 2000,  // 2秒
        lastError: null
    };
}

// 监听来自background script的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (sender.id !== chrome.runtime.id) {
        return; // 忽略来自其他扩展的消息
    }

    switch (request.action) {
        case 'startDetection':
            window.autoDetection.serverUrl = request.serverUrl;
            startDetection(sendResponse);
            return true;

        case 'stopDetection':
            stopDetection(sendResponse);
            return true;
    }
});

// 开始检测
function startDetection(sendResponse) {
    if (window.autoDetection.isRunning) {
        sendResponse({ success: false, error: '检测已经在运行中' });
        return;
    }

    window.autoDetection.isRunning = true;
    window.autoDetection.retryCount = 0;
    window.autoDetection.lastError = null;
    
    // 创建截图区域
    const overlay = document.createElement('div');
    overlay.id = 'detection-overlay';
    document.body.appendChild(overlay);

    // 开始定期截图和检测
    window.autoDetection.interval = setInterval(async () => {
        if (!window.autoDetection.isRunning) {
            clearInterval(window.autoDetection.interval);
            return;
        }

        try {
            // 获取页面截图
            const screenshot = await captureVisibleTab();
            if (!screenshot) {
                throw new Error('截图失败');
            }
            
            // 发送到服务器进行检测
            const response = await fetch(`${window.autoDetection.serverUrl}/api/detect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: screenshot
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`检测请求失败: ${response.status} ${response.statusText} - ${errorData.error || ''}`);
            }

            const result = await response.json();
            
            // 重置重试计数和错误状态
            window.autoDetection.retryCount = 0;
            window.autoDetection.lastError = null;
            
            // 显示检测结果
            displayResults(result);
        } catch (error) {
            console.error('检测过程出错:', error);
            window.autoDetection.lastError = error.message;
            
            // 处理连接错误
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                window.autoDetection.retryCount++;
                
                if (window.autoDetection.retryCount >= window.autoDetection.maxRetries) {
                    console.error('达到最大重试次数，停止检测');
                    stopDetection();
                    return;
                }
                
                console.log(`将在 ${window.autoDetection.retryDelay/1000} 秒后重试... (${window.autoDetection.retryCount}/${window.autoDetection.maxRetries})`);
                await new Promise(resolve => setTimeout(resolve, window.autoDetection.retryDelay));
            }
        }
    }, 1000); // 每秒检测一次

    sendResponse({ success: true });
}

// 停止检测
function stopDetection(sendResponse) {
    window.autoDetection.isRunning = false;
    
    if (window.autoDetection.interval) {
        clearInterval(window.autoDetection.interval);
        window.autoDetection.interval = null;
    }
    
    // 移除覆盖层
    const overlay = document.getElementById('detection-overlay');
    if (overlay) {
        overlay.remove();
    }

    if (sendResponse) {
        sendResponse({ 
            success: true,
            lastError: window.autoDetection.lastError
        });
    }
}

// 捕获可见标签页的截图
async function captureVisibleTab() {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ 
            action: 'captureVisibleTab'
        }, (response) => {
            if (chrome.runtime.lastError) {
                reject(chrome.runtime.lastError);
            } else if (response && response.success) {
                resolve(response.dataUrl);
            } else {
                reject(new Error('截图失败'));
            }
        });
    });
}

// 显示检测结果
function displayResults(results) {
    const overlay = document.getElementById('detection-overlay');
    if (!overlay) return;

    // 清除之前的结果
    overlay.innerHTML = '';

    // 显示新的检测结果
    results.detections.forEach(result => {
        const box = document.createElement('div');
        box.className = 'detection-box';
        
        // 设置检测框的位置和大小
        box.style.left = `${result.x}px`;
        box.style.top = `${result.y}px`;
        box.style.width = `${result.width}px`;
        box.style.height = `${result.height}px`;

        // 添加标签
        const label = document.createElement('div');
        label.className = 'detection-label';
        label.textContent = `${result.class} (${Math.round(result.confidence * 100)}%)`;
        box.appendChild(label);

        overlay.appendChild(box);
    });

    // 更新预览图片
    const preview = document.getElementById('preview');
    if (preview && results.image) {
        // 确保 image 是字符串类型
        const imageData = typeof results.image === 'string' ? results.image : 
                         (results.image.data || results.image.toString());
        preview.src = 'data:image/jpeg;base64,' + imageData;
        preview.style.display = 'block';
    }
} 