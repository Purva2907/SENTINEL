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
            <div class="ai-msg ai-msg-bot">
                <p>Hello! I am <strong>SENTINEL AI</strong>, your digital forensic investigation assistant.</p>
                <p style="margin-top:6px;">I can assist you with:</p>
                <ul>
                    <li><strong>Forensic Scoring</strong>: Explain why a document received a specific risk score.</li>
                    <li><strong>Signal Explanations</strong>: Break down ELA heatmaps, typography disparities, and layout shifts.</li>
                    <li><strong>Data Extraction</strong>: Retrieve registered names, DOB, address, Aadhaar/PAN numbers, and QR status.</li>
                    <li><strong>Investigative Guidance</strong>: Recommend physical checks and verification protocols.</li>
                </ul>
                <p style="margin-top:8px;">What would you like to investigate?</p>
            </div>
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
        caseId = currentCaseData.id || currentCaseData.case_id;
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
    // From active session storage across dashboard / profile / cases
    else {
        try {
            const cached = sessionStorage.getItem('analysisResult');
            if (cached) {
                const parsed = JSON.parse(cached);
                context = {
                    risk_score: parsed.risk_score,
                    classification: parsed.classification,
                    document_type: parsed.document_type,
                    quality: parsed.quality,
                    ocr: parsed.ocr,
                    qr: parsed.qr,
                    evidence: parsed.evidence,
                    heatmap: !!parsed.heatmap
                };
            }
        } catch(e) {}
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
        body.innerHTML = `
            <div class="ai-msg ai-msg-bot">
                <p>Conversation cleared. Ready for your forensic inquiries.</p>
                <p style="margin-top:6px;">What would you like to investigate?</p>
            </div>
        `;
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
        
        // Add to history (limit to last 20 msgs)
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
                document.getElementById(loadingId).outerHTML = `<div class="ai-msg ai-msg-bot">${formatAiResponse(answer)}</div>`;
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

function formatAiResponse(text) {
    if (!text) return '';

    // First safely escape raw HTML characters
    let safe = escapeHTML(text);

    // If bullets (• or * or -) appear inline without preceding newline, break them onto new lines
    safe = safe.replace(/([^\n])\s*[•]\s*/g, '$1\n• ');
    safe = safe.replace(/([^\n])\s*([0-9]+\.\s+)/g, '$1\n$2');

    // If concluding questions appear right after bullet item, break to new line
    safe = safe.replace(/([.!?])\s+(What would you like|How can I|Please let me know|Let me know|Where would you)/gi, '$1\n\n$2');

    // Convert bold: **text** -> <strong>text</strong>
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Convert inline code: `code` -> <code>$1</code>
    safe = safe.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Parse into structured paragraphs and bullet list items
    const rawLines = safe.split('\n');
    let html = '';
    let inList = false;

    for (let i = 0; i < rawLines.length; i++) {
        const line = rawLines[i].trim();

        // Check if line is a bullet item (•, -, *, or numbered like 1.)
        const isBullet = line.startsWith('•') || line.startsWith('- ') || line.startsWith('* ');
        const isNumbered = /^\d+\.\s+/.test(line);

        if (isBullet || isNumbered) {
            if (!inList) {
                html += '<ul style="margin:6px 0 8px 0; padding-left:18px;">';
                inList = true;
            }
            const itemContent = isBullet 
                ? line.replace(/^[•*-]\s*/, '') 
                : line.replace(/^\d+\.\s*/, '');
            html += `<li style="margin-bottom:6px; line-height:1.5;">${itemContent}</li>`;
        } else {
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            if (line === '') {
                html += '<div style="height:6px;"></div>';
            } else {
                html += `<p style="margin:0 0 6px 0; line-height:1.55;">${line}</p>`;
            }
        }
    }

    if (inList) {
        html += '</ul>';
    }

    return html;
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initChatbot);
