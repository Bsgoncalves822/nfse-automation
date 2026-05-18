// ============================================
// FUNÇÕES UTILITÁRIAS
// ============================================

const Utils = {
    // Debounce para evitar múltiplas chamadas
    debounce(func, wait = CONFIG.DEBOUNCE_DELAY) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Throttle para limitar frequência
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Verificar se está online
    isOnline() {
        return navigator.onLine;
    },

    // Sanitizar email
    sanitizeEmail(email) {
        if (!email) return '';
        return email.trim().toLowerCase();
    },

    // Validar email
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Formatar data
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        // Se já estiver em formato brasileiro, retornar como está
        if (typeof dateString === 'string' && /^\d{2}\/\d{2}\/\d{4}$/.test(dateString)) {
            return dateString;
        }
        
        try {
            const date = new Date(dateString);
            
            // Verificar se é uma data válida
            if (isNaN(date.getTime())) {
                return 'N/A';
            }
            
            return date.toLocaleDateString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        } catch (error) {
            console.error('[Utils] Erro ao formatar data:', error);
            return 'N/A';
        }
    },

    // Obter inicial do nome/email
    getInitial(text) {
        if (!text) return '?';
        return text.charAt(0).toUpperCase();
    },

    // Retry com backoff exponencial
    async retryWithBackoff(fn, maxRetries = CONFIG.MAX_RETRY_ATTEMPTS) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await fn();
            } catch (error) {
                if (i === maxRetries - 1) throw error;
                
                const delay = Math.min(1000 * Math.pow(2, i), 10000);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    },

    // Mostrar notificação do sistema (opcional)
    async showNotification(title, message, type = 'info') {
        if (!chrome.notifications) return;
        
        const iconUrls = {
            success: 'icons/icon-success-128.png',
            error: 'icons/icon-error-128.png',
            info: 'icons/icon-128.png'
        };

        try {
            await chrome.notifications.create({
                type: 'basic',
                iconUrl: iconUrls[type] || iconUrls.info,
                title: title,
                message: message
            });
        } catch (error) {
            console.error('[Utils] Erro ao mostrar notificação:', error);
        }
    },

    // Log com timestamp
    log(category, message, data = null) {
        const timestamp = new Date().toISOString();
        const prefix = `[${timestamp}] [${category}]`;
        
        if (data) {
            console.log(prefix, message, data);
        } else {
            console.log(prefix, message);
        }
    },

    // Copiar para clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            console.error('[Utils] Erro ao copiar:', error);
            
            // Fallback
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            
            const success = document.execCommand('copy');
            document.body.removeChild(textarea);
            
            return success;
        }
    },

    // Escapar HTML
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    },

    // Gerar ID único
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },

    // Criar elemento com atributos
    createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);
        
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'style' && typeof value === 'object') {
                Object.assign(element.style, value);
            } else if (key.startsWith('on') && typeof value === 'function') {
                element.addEventListener(key.substring(2).toLowerCase(), value);
            } else {
                element.setAttribute(key, value);
            }
        });
        
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                element.appendChild(child);
            }
        });
        
        return element;
    },

    // Animar elemento
    animate(element, keyframes, options) {
        if (!element || !element.animate) return null;
        return element.animate(keyframes, options);
    },

    // Fade in
    fadeIn(element, duration = 300) {
        if (!element) return;
        
        element.style.opacity = '0';
        element.style.display = 'block';
        
        this.animate(element, [
            { opacity: 0 },
            { opacity: 1 }
        ], {
            duration,
            easing: 'ease-in-out',
            fill: 'forwards'
        });
    },

    // Fade out
    fadeOut(element, duration = 300) {
        if (!element) return;
        
        const animation = this.animate(element, [
            { opacity: 1 },
            { opacity: 0 }
        ], {
            duration,
            easing: 'ease-in-out',
            fill: 'forwards'
        });
        
        if (animation) {
            animation.onfinish = () => {
                element.style.display = 'none';
            };
        }
    }
};

// Classe para gerenciar UI Messages
class UIMessage {
    constructor(containerId = 'message') {
        this.container = document.getElementById(containerId);
        this.timeout = null;
    }

    show(text, type = 'info', duration = CONFIG.AUTO_HIDE_MESSAGE) {
        if (!this.container) return;

        this.clear();

        this.container.textContent = text;
        this.container.className = `message ${type}`;
        this.container.style.display = 'block';
        
        Utils.fadeIn(this.container, 200);

        if (duration > 0) {
            this.timeout = setTimeout(() => this.hide(), duration);
        }
    }

    hide() {
        if (!this.container) return;
        
        Utils.fadeOut(this.container, 200);
        this.clear();
    }

    clear() {
        if (this.timeout) {
            clearTimeout(this.timeout);
            this.timeout = null;
        }
    }

    success(text, duration) {
        this.show(text, 'success', duration);
    }

    error(text, duration) {
        this.show(text, 'error', duration);
    }

    warning(text, duration) {
        this.show(text, 'warning', duration);
    }

    info(text, duration) {
        this.show(text, 'info', duration);
    }
}

// Classe para loading states
class LoadingManager {
    constructor() {
        this.activeLoaders = new Set();
    }

    start(loaderId = 'default') {
        this.activeLoaders.add(loaderId);
        this.updateUI();
    }

    stop(loaderId = 'default') {
        this.activeLoaders.delete(loaderId);
        this.updateUI();
    }

    isLoading(loaderId = null) {
        if (loaderId) {
            return this.activeLoaders.has(loaderId);
        }
        return this.activeLoaders.size > 0;
    }

    updateUI() {
        const isLoading = this.isLoading();
        
        // Atualizar cursor
        document.body.style.cursor = isLoading ? 'wait' : 'default';
        
        // Emitir evento customizado
        document.dispatchEvent(new CustomEvent('loadingChanged', {
            detail: { isLoading }
        }));
    }

    stopAll() {
        this.activeLoaders.clear();
        this.updateUI();
    }
}

// Instâncias globais
const loadingManager = new LoadingManager();
