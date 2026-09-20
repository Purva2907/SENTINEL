// theme.js - Global SENTINEL Theme Manager

window.ThemeManager = {
    STORAGE_KEY: 'sentinel_theme',
    
    init() {
        const savedTheme = localStorage.getItem(this.STORAGE_KEY) || 'dark';
        this.applyTheme(savedTheme);
        
        // Handle legacy toggle if it still exists somewhere
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                this.setTheme(newTheme);
            });
            this.updateIcon(themeToggle, savedTheme);
        }
    },
    
    setTheme(theme) {
        // Map clean-light to light, forensic-dark to dark if accidentally passed
        if (theme === 'clean-light') theme = 'light';
        if (theme === 'forensic-dark') theme = 'dark';

        localStorage.setItem(this.STORAGE_KEY, theme);
        this.applyTheme(theme);
        
        // Dispatch global event for charts, chatbot, etc.
        window.dispatchEvent(
            new CustomEvent("sentinel-theme-change", {
                detail: { theme }
            })
        );
    },
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            this.updateIcon(themeToggle, theme);
        }
    },
    
    updateIcon(toggleEl, theme) {
        const icon = toggleEl.querySelector('i');
        if (icon) {
            if (theme === 'light') {
                icon.className = 'fa-solid fa-sun';
            } else {
                icon.className = 'fa-solid fa-moon';
            }
        }
    }
};

// Initialize after DOM load for any components that need it, 
// though the actual CSS variable should be set earlier by the inline head script.
document.addEventListener('DOMContentLoaded', () => {
    window.ThemeManager.init();
});
