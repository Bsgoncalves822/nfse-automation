// ============================================
// CONFIGURAÃ‡Ã•ES CENTRALIZADAS DA EXTENSÃƒO
// ============================================

const CONFIG = {
    // URLs
    WORKER_URL: 'https://hotmart-validator.eliabellira.workers.dev',
    SALES_PAGE_URL: chrome.runtime.getURL('sales.html'),
    HOTMART_CHECKOUT_URL: 'https://pay.hotmart.com/J104394050D',
    
    // Timing (em milissegundos)
    CACHE_DURATION: 6 * 60 * 60 * 1000, // 6 horas
    REVALIDATE_INTERVAL: 360, // 6 horas em minutos
    AUTO_HIDE_MESSAGE: 5000, // 5 segundos
    RELOAD_DELAY: 1000, // 1 segundo
    
    // Limites
    MAX_RETRY_ATTEMPTS: 3,
    REQUEST_TIMEOUT: 30000, // 30 segundos
    DEBOUNCE_DELAY: 300, // 300ms
    
    // Storage Keys
    STORAGE_KEYS: {
        LICENSE_STATUS: 'licenseStatus',
        LAST_VALIDATION: 'lastValidation',
        VALIDATION_TIMESTAMP: 'validationTimestamp'
    },
    
    // Estados de UI
    UI_STATES: {
        VALID: 'valid',
        INVALID: 'invalid',
        LOADING: 'loading',
        ERROR: 'error'
    }
};

// Tornar disponÃ­vel globalmente
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}