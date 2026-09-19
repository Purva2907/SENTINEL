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
        'Content-Type': 'application/json',
        ...options.headers
    };
    
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
            return await res.json();
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
