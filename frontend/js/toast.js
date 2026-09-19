class ToastManager {
    constructor() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
        
        // Ensure CSS is loaded
        if (!document.querySelector('link[href="css/toast.css"]')) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'css/toast.css';
            document.head.appendChild(link);
        }
    }

    show(type, title, message, duration = 4000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let iconClass = '';
        switch(type) {
            case 'success': iconClass = 'fa-solid fa-circle-check'; break;
            case 'error': iconClass = 'fa-solid fa-circle-exclamation'; break;
            case 'warning': iconClass = 'fa-solid fa-triangle-exclamation'; break;
            case 'info': iconClass = 'fa-solid fa-circle-info'; break;
            case 'loading': iconClass = 'fa-solid fa-spinner'; break;
        }

        toast.innerHTML = `
            <div class="toast-icon">
                <i class="${iconClass}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                ${message ? `<div class="toast-message">${message}</div>` : ''}
            </div>
            ${type !== 'loading' ? `
            <button class="toast-close">
                <i class="fa-solid fa-xmark"></i>
            </button>` : ''}
        `;

        this.container.appendChild(toast);
        
        // Trigger reflow for animation
        toast.offsetHeight;
        toast.classList.add('show');

        const removeToast = () => {
            toast.classList.remove('show');
            toast.addEventListener('transitionend', () => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            });
        };

        if (type !== 'loading') {
            const closeBtn = toast.querySelector('.toast-close');
            closeBtn.addEventListener('click', removeToast);
            
            if (duration > 0) {
                setTimeout(removeToast, duration);
            }
        }
        
        return {
            dismiss: removeToast
        };
    }

    success(title, message = '', duration = 4000) { return this.show('success', title, message, duration); }
    error(title, message = '', duration = 5000) { return this.show('error', title, message, duration); }
    warning(title, message = '', duration = 4000) { return this.show('warning', title, message, duration); }
    info(title, message = '', duration = 4000) { return this.show('info', title, message, duration); }
    loading(title, message = '') { return this.show('loading', title, message, 0); }
}

const Toast = new ToastManager();
window.Toast = Toast;
