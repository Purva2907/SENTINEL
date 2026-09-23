// chatbot.js - Global SENTINEL AI Assistant (Interactive ChatGPT-Style)

let chatHistory = [];
let userDocketCases = [];
let activeCaseOverride = null;

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

        <div class="ai-docket-bar" id="aiDocketBar">
            <i class="fa-solid fa-folder-open"></i>
            <span class="ai-docket-label">Case Focus:</span>
            <select id="aiCaseSelect" title="Select Investigation Case Context">
                <option value="">Active Document / General</option>
            </select>
        </div>
        
        <div class="ai-body" id="aiChatBody">
            <div class="ai-msg ai-msg-bot">
                <div class="ai-msg-content">
                    <p>Hello! I am <strong>SENTINEL AI</strong>, your digital forensic investigation copilot.</p>
                    <p style="margin-top:6px;">I can converse like ChatGPT and assist across your entire docket:</p>
                    <ul>
                        <li><strong>Multi-Case Cross Referencing</strong>: Ask about any of your cases by name or ID (or compare two cases)!</li>
                        <li><strong>Forensic Explainability</strong>: Drill down into 52 risk score, ELA heatmaps, typography, and QR codes.</li>
                        <li><strong>Demographic Extraction</strong>: Query registered name, DOB, address, Aadhaar/PAN, or virtual ID.</li>
                        <li><strong>Executive Summaries</strong>: Ask <em>"Give me summary"</em> anytime for a full dossier.</li>
                    </ul>
                    <p style="margin-top:8px;">What would you like to investigate?</p>
                </div>
            </div>
        </div>
        
        <div class="ai-suggestions" id="aiSuggestions">
            <button class="ai-suggestion-btn" data-prompt="List my cases">📋 List My Cases</button>
            <button class="ai-suggestion-btn" data-prompt="Explain this risk score">🔍 Explain Score</button>
            <button class="ai-suggestion-btn" data-prompt="Compare this case with my other cases">⚖️ Compare Cases</button>
            <button class="ai-suggestion-btn" data-prompt="Who is the registered holder?">👤 Extract Info</button>
            <button class="ai-suggestion-btn" data-prompt="Give me summary of this case">📊 Case Summary</button>
        </div>
        
        <div class="ai-input-area">
            <textarea id="aiChatInput" placeholder="Ask AI investigator (e.g. 'Compare with passport case')..."></textarea>
            <button id="aiSendBtn" title="Send Message"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
    </div>
    `;

    const container = document.createElement('div');
    container.innerHTML = html;
    document.body.appendChild(container);

    attachChatEvents();
    loadDocketCases();
}

async function loadDocketCases() {
    try {
        const select = document.getElementById('aiCaseSelect');
        if (!select) return;

        const res = await fetchWithAuth(`${API_BASE}/cases`);
        if (!res.ok) return;

        const data = await res.json();
        userDocketCases = Array.isArray(data) ? data : (data.cases || []);

        // Rebuild options
        select.innerHTML = '<option value="">Active Document / General</option>';
        userDocketCases.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id || c.case_id;
            opt.textContent = `${c.title || 'Untitled'} (${c.case_id || 'Case'}) - Risk: ${c.risk_score || 0}`;
            select.appendChild(opt);
        });

        // If on case-detail page, sync preselection
        const { caseId } = getForensicContext();
        if (caseId) {
            select.value = caseId;
            activeCaseOverride = caseId;
        }
    } catch(e) {
        // Silent background fallback
    }
}

function getForensicContext() {
    let context = null;
    let caseId = activeCaseOverride;

    // From case-detail.html
    if (typeof currentCaseData !== 'undefined' && currentCaseData) {
        context = {
            risk_score: currentCaseData.risk_score,
            classification: currentCaseData.classification,
            document_type: currentCaseData.document_type,
            title: currentCaseData.title,
            ...currentCaseData.analysis
        };
        if (!caseId) caseId = currentCaseData.id || currentCaseData.case_id;
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
    const caseSelect = document.getElementById('aiCaseSelect');

    btn.addEventListener('click', () => {
        panel.style.display = 'flex';
        btn.style.display = 'none';
        body.scrollTop = body.scrollHeight;
        loadDocketCases();
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
                <div class="ai-msg-content">
                    <p>Conversation cleared. Ready for your forensic inquiries or case cross-examinations.</p>
                    <p style="margin-top:6px;">What would you like to investigate?</p>
                </div>
            </div>
        `;
    });

    if (caseSelect) {
        caseSelect.addEventListener('change', (e) => {
            activeCaseOverride = e.target.value || null;
            const selectedText = e.target.options[e.target.selectedIndex].text;
            body.innerHTML += `
                <div class="ai-msg ai-system-note">
                    <i class="fa-solid fa-arrows-rotate"></i> Context focus updated: <strong>${escapeHTML(selectedText)}</strong>
                </div>
            `;
            body.scrollTop = body.scrollHeight;
        });
    }

    document.querySelectorAll('.ai-suggestion-btn').forEach(sbtn => {
        sbtn.addEventListener('click', () => {
            const prompt = sbtn.getAttribute('data-prompt') || sbtn.innerText;
            input.value = prompt;
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

    async function sendMessage(customText) {
        const text = (typeof customText === 'string' ? customText : input.value).trim();
        if (!text) return;

        // Append user msg
        body.innerHTML += `<div class="ai-msg ai-msg-user">${escapeHTML(text)}</div>`;
        input.value = '';
        body.scrollTop = body.scrollHeight;

        // Append loading
        const loadingId = 'msg-' + Date.now();
        body.innerHTML += `<div class="ai-msg ai-msg-bot ai-loading-dots" id="${loadingId}"><i class="fa-solid fa-circle-notch fa-spin"></i> Analyzing...</div>`;
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
                    history: chatHistory.slice(0, -1),
                    context: context || {},
                    case_id: activeCaseOverride || caseId
                })
            });

            const res = await response.json();
            
            if (response.ok) {
                const answer = res.response || "No response received.";
                const loadingElem = document.getElementById(loadingId);
                if (loadingElem) {
                    loadingElem.outerHTML = renderBotMessage(answer);
                }
                chatHistory.push({ role: "assistant", content: answer });
                setupCopyButtons();
            } else {
                const loadingElem = document.getElementById(loadingId);
                if (loadingElem) {
                    loadingElem.outerHTML = `<div class="ai-msg ai-msg-bot" style="color:var(--danger)"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${escapeHTML(res.detail || 'Could not connect to AI')}</div>`;
                }
                chatHistory.pop();
            }
        } catch(e) {
            const loadingElem = document.getElementById(loadingId);
            if (loadingElem) {
                loadingElem.outerHTML = `<div class="ai-msg ai-msg-bot" style="color:var(--danger)"><i class="fa-solid fa-triangle-exclamation"></i> Network disconnected.</div>`;
            }
            chatHistory.pop();
        }
        body.scrollTop = body.scrollHeight;
    }

    // Expose global sender for interactive chips
    window.askSentinelAi = function(query) {
        const p = document.getElementById('sentinelAiPanel');
        const b = document.getElementById('sentinelAiBtn');
        if (p) p.style.display = 'flex';
        if (b) b.style.display = 'none';
        sendMessage(query);
    };
}

function renderBotMessage(text) {
    const formatted = formatAiResponse(text);
    return `
        <div class="ai-msg ai-msg-bot">
            <div class="ai-msg-actions">
                <button class="ai-copy-btn" title="Copy response"><i class="fa-regular fa-copy"></i></button>
            </div>
            <div class="ai-msg-content">${formatted}</div>
        </div>
    `;
}

function setupCopyButtons() {
    document.querySelectorAll('.ai-copy-btn').forEach(btn => {
        if (btn.dataset.bound) return;
        btn.dataset.bound = "true";
        btn.addEventListener('click', (e) => {
            const container = btn.closest('.ai-msg-bot');
            const content = container ? container.querySelector('.ai-msg-content') : null;
            if (content) {
                navigator.clipboard.writeText(content.innerText || content.textContent);
                btn.innerHTML = '<i class="fa-solid fa-check" style="color:var(--success)"></i>';
                setTimeout(() => {
                    btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
                }, 2000);
            }
        });
    });
}

function escapeHTML(str) {
    return String(str).replace(/[&<>'"]/g, 
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

    // Parse Markdown tables if present (| header | header |)
    safe = parseMarkdownTables(safe);

    // Convert Markdown headers: ### Heading -> <h4>Heading</h4>
    safe = safe.replace(/^###\s+(.*$)/gim, '<h4 class="ai-heading-3">$1</h4>');
    safe = safe.replace(/^##\s+(.*$)/gim, '<h3 class="ai-heading-2">$1</h3>');

    // Convert bold: **text** -> <strong>text</strong>
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Convert inline italics: *text* -> <em>$1</em>
    safe = safe.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');

    // Convert inline code: `code` -> <code>$1</code>
    safe = safe.replace(/`([^`]+)`/g, (match, p1) => {
        // If it's a Case ID like SC-2026-XXXX, make it a clickable chip!
        if (/^SC-\d{4}-[A-Z0-9]+$/i.test(p1.trim())) {
            return `<span class="ai-case-chip" onclick="askSentinelAi('What about case ${p1.trim()}?')"><i class="fa-solid fa-folder-closed"></i> ${p1.trim()}</span>`;
        }
        return `<code>${p1}</code>`;
    });

    // Parse into structured paragraphs and bullet list items
    const rawLines = safe.split('\n');
    let html = '';
    let inList = false;

    for (let i = 0; i < rawLines.length; i++) {
        const line = rawLines[i].trim();

        if (line.startsWith('<table') || line.startsWith('</table') || line.startsWith('<h3') || line.startsWith('<h4')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += line;
            continue;
        }

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

function parseMarkdownTables(text) {
    const tableRegex = /(?:\|[^\n]+\|\r?\n)((?:\|[^\n]+\|\r?\n?)+)/g;
    return text.replace(tableRegex, (match) => {
        const lines = match.trim().split('\n');
        if (lines.length < 2) return match;

        let tableHtml = '<div class="ai-table-wrap"><table class="ai-table">';
        
        // Header
        const headerCols = lines[0].split('|').map(s => s.trim()).filter((s, idx, arr) => idx > 0 && idx < arr.length - 1);
        tableHtml += '<thead><tr>' + headerCols.map(c => `<th>${c}</th>`).join('') + '</tr></thead>';

        // Body rows (skip separator at index 1 if contains ---)
        tableHtml += '<tbody>';
        const startRow = lines[1].includes('---') ? 2 : 1;
        for (let r = startRow; r < lines.length; r++) {
            const cols = lines[r].split('|').map(s => s.trim()).filter((s, idx, arr) => idx > 0 && idx < arr.length - 1);
            if (cols.length) {
                tableHtml += '<tr>' + cols.map(c => `<td>${c}</td>`).join('') + '</tr>';
            }
        }
        tableHtml += '</tbody></table></div>';
        return tableHtml;
    });
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initChatbot);
