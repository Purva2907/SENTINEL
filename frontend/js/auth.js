// Configurable API base origin
function getApiBase() {
    if (window.__SENTINEL_API_BASE__) return window.__SENTINEL_API_BASE__;
    try {
        const stored = localStorage.getItem('SENTINEL_API_BASE');
        if (stored) return stored;
    } catch (e) {}
    // If hosted on same port or reverse-proxied production host
    if (window.location.port === '8000' || (!window.location.port && window.location.protocol.startsWith('http'))) {
        return `${window.location.origin}/api`;
    }
    const host = window.location.hostname || 'localhost';
    return `http://${host}:8000/api`;
}

const API_BASE = getApiBase();
window.API_BASE = API_BASE;

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}
window.escapeHtml = escapeHtml;

function renderAvatarSafely(container, av, name = 'I') {
    if (!container) return;
    container.replaceChildren();
    if (!av) {
        container.style.background = 'linear-gradient(135deg, var(--orange, #e05a10), #e67e22)';
        container.textContent = (name || 'I').charAt(0).toUpperCase();
        return;
    }
    if (av.startsWith('data:image/')) {
        const img = document.createElement('img');
        img.src = av;
        img.alt = 'User Avatar';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        img.style.borderRadius = '50%';
        img.style.display = 'block';
        container.style.background = 'transparent';
        container.style.overflow = 'hidden';
        container.appendChild(img);
    } else if (av.startsWith('icon:')) {
        const parts = av.replace('icon:', '').split('|');
        const iconClass = (parts[0] || 'fa-user-shield').replace(/[^a-zA-Z0-9_-]/g, '');
        const bg = parts[1] || 'linear-gradient(135deg, var(--orange, #e05a10), #e67e22)';
        container.style.background = bg;
        container.style.overflow = 'hidden';
        if (iconClass === 'initials') {
            container.textContent = (name || 'I').charAt(0).toUpperCase();
        } else {
            const icon = document.createElement('i');
            icon.className = `fa-solid ${iconClass}`;
            container.appendChild(icon);
        }
    } else {
        container.textContent = (name || 'I').charAt(0).toUpperCase();
    }
}
window.renderAvatarSafely = renderAvatarSafely;

function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function removeToken() {
    localStorage.removeItem('token');
}

async function fetchWithAuth(url, options = {}) {
    const token = getToken();
    const headers = {
        ...options.headers
    };
    
    // If sending FormData, do not set Content-Type so browser generates multipart boundary
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    } else if (!headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        ...options,
        headers
    };
    
    const response = await fetch(url, config);
    if (response.status === 401) {
        // Token expired or invalid
        removeToken();
        window.location.href = 'login.html';
    }
    return response;
}

async function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = 'login.html';
        return null;
    }
    
    try {
        const res = await fetchWithAuth(`${API_BASE}/auth/me`);
        if (res.ok) {
            const user = await res.json();
            if (user.avatar) {
                localStorage.setItem('sentinel_avatar', user.avatar);
            }
            const topAv = document.getElementById('topAvatar');
            if (topAv) {
                const av = user.avatar || localStorage.getItem('sentinel_avatar');
                renderAvatarSafely(topAv, av, user.name);
            }
            return user;
        } else {
            removeToken();
            window.location.href = 'login.html';
            return null;
        }
    } catch (e) {
        console.error(e);
        return null;
    }
}

function logout() {
    removeToken();
    window.location.href = 'login.html';
}

function getErrorMessage(errorData) {
    if (!errorData) return "Unknown error occurred";
    if (typeof errorData === 'string') return errorData;
    
    if (typeof errorData === 'object') {
        if (errorData.detail) {
            if (typeof errorData.detail === 'string') return errorData.detail;
            if (Array.isArray(errorData.detail)) {
                return errorData.detail.map(err => {
                    return (err && err.msg) ? err.msg : JSON.stringify(err);
                }).join(', ');
            }
            return JSON.stringify(errorData.detail);
        }
        if (errorData.message) {
            return typeof errorData.message === 'string' ? errorData.message : JSON.stringify(errorData.message);
        }
        if (errorData.error) {
            return typeof errorData.error === 'string' ? errorData.error : JSON.stringify(errorData.error);
        }
        try {
            return JSON.stringify(errorData);
        } catch(e) {
            return "Unknown error occurred";
        }
    }
    return String(errorData);
}

function togglePasswordVisibility(inputId, button) {
    const input = document.getElementById(inputId);
    const icon = button.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
        button.setAttribute('aria-label', 'Hide password');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
        button.setAttribute('aria-label', 'Show password');
    }
}
