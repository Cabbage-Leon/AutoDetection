let isRunning = false;
let currentTabId = null;

// 检查URL是否是允许的网页
function isAllowedUrl(url) {
    return url.startsWith('http://') || url.startsWith('https://');
}

// 监听来自popup的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
        case 'startDetection':
            startDetection(request.serverUrl, sendResponse);
            return true; // 保持消息通道开放

        case 'stopDetection':
            stopDetection(sendResponse);
            return true;

        case 'getStatus':
            sendResponse({ isRunning });
            return false;

        case 'captureVisibleTab':
            captureVisibleTab(sender.tab.id, sendResponse);
            return true;
    }
});

// 开始检测
async function startDetection(serverUrl, sendResponse) {
    try {
        // 获取当前标签页
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // 检查是否是允许的URL
        if (!isAllowedUrl(tab.url)) {
            sendResponse({ 
                success: false, 
                error: '此页面不支持检测功能。请尝试在普通网页上使用。' 
            });
            return;
        }

        currentTabId = tab.id;

        // 注入content script
        await chrome.scripting.executeScript({
            target: { tabId: currentTabId },
            files: ['src/js/content.js']
        });

        // 发送消息给content script
        chrome.tabs.sendMessage(currentTabId, {
            action: 'startDetection',
            serverUrl: serverUrl
        }, (response) => {
            if (chrome.runtime.lastError) {
                sendResponse({ success: false, error: chrome.runtime.lastError.message });
            } else {
                isRunning = true;
                sendResponse({ success: true });
            }
        });
    } catch (error) {
        sendResponse({ success: false, error: error.message });
    }
}

// 停止检测
function stopDetection(sendResponse) {
    if (currentTabId) {
        chrome.tabs.sendMessage(currentTabId, {
            action: 'stopDetection'
        }, (response) => {
            if (chrome.runtime.lastError) {
                sendResponse({ success: false, error: chrome.runtime.lastError.message });
            } else {
                isRunning = false;
                currentTabId = null;
                sendResponse({ success: true });
            }
        });
    } else {
        isRunning = false;
        sendResponse({ success: true });
    }
}

// 捕获可见标签页的截图
async function captureVisibleTab(tabId, sendResponse) {
    try {
        if (!tabId) {
            throw new Error('无效的标签页ID');
        }

        const dataUrl = await chrome.tabs.captureVisibleTab(null, {
            format: 'png'
        });

        if (!dataUrl) {
            throw new Error('截图失败');
        }

        sendResponse({ success: true, dataUrl });
    } catch (error) {
        console.error('截图错误:', error);
        sendResponse({ success: false, error: error.message });
    }
} 