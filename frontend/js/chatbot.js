// chatbot.js - Global SENTINEL AI Assistant

let chatHistory = [];

function initChatbot() {
    // Only inject if authenticated
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (!token) return;

    // Check if already injected
    if (document.getElementById('sentinelAiPanel')) return;

    const html = `
    <button class="sentinel-ai-btn" id="sentinelAiBtn" title="SENTINEL AI Assistant">
        <i class="fa-solid fa-robot"></i>
    </button>
    
    <div class="sentinel-ai-panel" id="sentinelAiPanel">
        <div class="ai-header">
            <div class="ai-header-left">
                <i class="fa-solid fa-shield-halved"></i> SENTINEL AI
                <span class="ai-status-indicator" title="Context-aware"></span>
            </div>
            <div class="ai-header-right">
                <i class="fa-solid fa-broom" id="clearChatBtn" title="Clear Conversation"></i>
                <i class="fa-solid fa-minus" id="minimizeChatBtn" title="Minimize"></i>
                <i class="fa-solid fa-xmark" id="closeChatBtn" title="Close"></i>
            </div>
        </div>
        
        <div class="ai-body" id="aiChatBody">
            <div class="ai-msg ai-msg-bot">I am SENTINEL AI, your forensic investigation assistant. How can I help you today?</div>
        </div>
        
        <div class="ai-suggestions" id="aiSuggestions">
            <button class="ai-suggestion-btn">Explain this risk score</button>
            <button class="ai-suggestion-btn">What evidence caused the risk?</button>
            <button class="ai-suggestion-btn">What should I manually verify?</button>
        </div>
        
        <div class="ai-input-area">
            <textarea id="aiChatInput" placeholder="Ask AI investigator..."></textarea>
            <button id="aiSendBtn"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
    </div>
    `;

    const container = document.createElement('div');
    container.innerHTML = html;
    document.body.appendChild(container);

    attachChatEvents();
}

function getForensicContext() {
    let context = null;
    let caseId = null;

    // From case-detail.html
    if (typeof currentCaseData !== 'undefined' && currentCaseData) {
        context = {
            risk_score: currentCaseData.risk_score,
            classification: currentCaseData.classification,
            document_type: currentCaseData.document_type,
            title: currentCaseData.title,
            ...currentCaseData.analysis
        };
        caseId = currentCaseData.case_id || currentCaseData.id;
    } 
    // From results.html
    else if (typeof analysisData !== 'undefined' && analysisData) {
        context = {
            risk_score: analysisData.risk_score,
            classification: analysisData.classification,
            document_type: analysisData.document_type,
            quality: analysisData.quality,
            ocr: analysisData.ocr,
            qr: analysisData.qr,
            evidence: analysisData.evidence,
            heatmap: !!analysisData.heatmap
        };
    }

    return { context, caseId };
}

function attachChatEvents() {
    const btn = document.getElementById('sentinelAiBtn');
    const panel = document.getElementById('sentinelAiPanel');
    const closeBtn = document.getElementById('closeChatBtn');
    const minimizeBtn = document.getElementById('minimizeChatBtn');
    const clearBtn = document.getElementById('clearChatBtn');
    const sendBtn = document.getElementById('aiSendBtn');
    const input = document.getElementById('aiChatInput');
    const body = document.getElementById('aiChatBody');
    const suggestions = document.getElementById('aiSuggestions');

    btn.addEventListener('click', () => {
        panel.style.display = 'flex';
        btn.style.display = 'none';
        updateSuggestionsVisibility();
        body.scrollTop = body.scrollHeight;
    });

    closeBtn.addEventListener('click', () => {
        panel.style.display = 'none';
        btn.style.display = 'flex';
    });

    minimizeBtn.addEventListener('click', () => {
        panel.style.display = 'none';
        btn.style.display = 'flex';
    });

    clearBtn.addEventListener('click', () => {
        chatHistory = [];
        body.innerHTML = '<div class="ai-msg ai-msg-bot">Conversation cleared. I am ready to assist you.</div>';
    });

    document.querySelectorAll('.ai-suggestion-btn').forEach(sbtn => {
        sbtn.addEventListener('click', () => {
            input.value = sbtn.innerText;
            sendMessage();
        });
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);
    
    function updateSuggestionsVisibility() {
        const { context } = getForensicContext();
        if (context) {
            suggestions.style.display = 'flex';
        } else {
            suggestions.style.display = 'none';
        }
    }

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Append user msg
        body.innerHTML += `<div class="ai-msg ai-msg-user">${escapeHTML(text)}</div>`;
        input.value = '';
        body.scrollTop = body.scrollHeight;

        // Append loading
        const loadingId = 'msg-' + Date.now();
        body.innerHTML += `<div class="ai-msg ai-msg-bot ai-loading-dots" id="${loadingId}"><i class="fa-solid fa-ellipsis fa-fade"></i></div>`;
        body.scrollTop = body.scrollHeight;

        const { context, caseId } = getForensicContext();
        
        // Add to history (limit to last 10 msgs)
        chatHistory.push({ role: "user", content: text });
        if(chatHistory.length > 20) chatHistory = chatHistory.slice(-20);

        try {
            const response = await fetchWithAuth(`${API_BASE}/chat`, {
                method: 'POST',
                body: JSON.stringify({
                    message: text,
                    history: chatHistory.slice(0, -1), // send previous history
                    context: context || {},
                    case_id: caseId
                })
            });

            const res = await response.json();
            
            if (response.ok) {
                const answer = res.response || "No response received.";
                document.getElementById(loadingId).outerHTML = `<div class="ai-msg ai-msg-bot">${escapeHTML(answer)}</div>`;
                chatHistory.push({ role: "assistant", content: answer });
            } else {
                document.getElementById(loadingId).outerHTML = `<div class="ai-msg ai-msg-bot" style="color:var(--danger)"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${res.detail || 'Could not connect to AI'}</div>`;
                chatHistory.pop(); // remove failed msg from history
            }
        } catch(e) {
            document.getElementById(loadingId).outerHTML = `<div class="ai-msg ai-msg-bot" style="color:var(--danger)"><i class="fa-solid fa-triangle-exclamation"></i> Network disconnected.</div>`;
            chatHistory.pop();
        }
        body.scrollTop = body.scrollHeight;
    }
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initChatbot);
