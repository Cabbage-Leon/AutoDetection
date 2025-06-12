document.addEventListener('DOMContentLoaded', function() {
    const startButton = document.getElementById('startDetection');
    const stopButton = document.getElementById('stopDetection');
    const statusText = document.getElementById('statusText');
    const serverUrlInput = document.getElementById('serverUrl');

    // 从存储中加载设置
    chrome.storage.local.get(['serverUrl'], function(result) {
        if (result.serverUrl) {
            serverUrlInput.value = result.serverUrl;
        }
    });

    // 保存设置
    serverUrlInput.addEventListener('change', function() {
        chrome.storage.local.set({ serverUrl: serverUrlInput.value });
    });

    // 开始检测
    startButton.addEventListener('click', function() {
        chrome.storage.local.get(['serverUrl'], function(result) {
            const serverUrl = result.serverUrl || 'http://localhost:5000';
            
            // 发送消息给background script
            chrome.runtime.sendMessage({
                action: 'startDetection',
                serverUrl: serverUrl
            }, function(response) {
                if (response.success) {
                    statusText.textContent = '检测中...';
                    startButton.disabled = true;
                    stopButton.disabled = false;
                } else {
                    statusText.textContent = '启动失败: ' + response.error;
                }
            });
        });
    });

    // 停止检测
    stopButton.addEventListener('click', function() {
        chrome.runtime.sendMessage({
            action: 'stopDetection'
        }, function(response) {
            if (response.success) {
                statusText.textContent = '已停止';
                startButton.disabled = false;
                stopButton.disabled = true;
            }
        });
    });

    // 初始化按钮状态
    chrome.runtime.sendMessage({ action: 'getStatus' }, function(response) {
        if (response.isRunning) {
            statusText.textContent = '检测中...';
            startButton.disabled = true;
            stopButton.disabled = false;
        } else {
            statusText.textContent = '未开始';
            startButton.disabled = false;
            stopButton.disabled = true;
        }
    });
}); 