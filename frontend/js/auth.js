const API_BASE = 'http://localhost:8000/api';

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
                if (av && (av.startsWith('data:image/') || av.startsWith('http'))) {
                    topAv.innerHTML = `<img src="${av}" style="width:100%; height:100%; object-fit:cover; border-radius:50%; display:block;">`;
                    topAv.style.background = 'transparent';
                    topAv.style.overflow = 'hidden';
                } else if (av && av.startsWith('icon:')) {
                    const parts = av.replace('icon:', '').split('|');
                    const iconClass = parts[0] || 'fa-user-shield';
                    const bg = parts[1] || 'linear-gradient(135deg, var(--orange), #e67e22)';
                    topAv.style.background = bg;
                    topAv.style.overflow = 'hidden';
                    if (iconClass === 'initials') {
                        const name = user.name || 'I';
                        topAv.innerText = name.charAt(0).toUpperCase();
                    } else {
                        topAv.innerHTML = `<i class="fa-solid ${iconClass}"></i>`;
                    }
                }
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
