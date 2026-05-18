// ============================================
// GERENCIADOR DE ESTADO DA LICENÃ‡A
// ============================================

class LicenseStateManager {
    constructor() {
        this.listeners = [];
        this.setupStorageListener();
    }

    // Obter status da licenÃ§a com cache
    async get() {
        try {
            const result = await chrome.storage.local.get([
                CONFIG.STORAGE_KEYS.LICENSE_STATUS,
                CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP
            ]);
            
            const license = result[CONFIG.STORAGE_KEYS.LICENSE_STATUS];
            const timestamp = result[CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP];
            
            // Verificar se o cache ainda Ã© vÃ¡lido
            if (timestamp && license) {
                const age = Date.now() - timestamp;
                if (age < CONFIG.CACHE_DURATION) {
                    return { ...license, fromCache: true };
                }
            }
            
            return license || null;
        } catch (error) {
            console.error('[StateManager] Erro ao obter licenÃ§a:', error);
            return null;
        }
    }

    // Salvar status da licenÃ§a
    async set(license) {
        try {
            await chrome.storage.local.set({
                [CONFIG.STORAGE_KEYS.LICENSE_STATUS]: license,
                [CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP]: Date.now()
            });
            
            // Notificar listeners
            this.notifyListeners(license);
            
            return true;
        } catch (error) {
            console.error('[StateManager] Erro ao salvar licenÃ§a:', error);
            return false;
        }
    }

    // Limpar licenÃ§a
    async clear() {
        try {
            await chrome.storage.local.remove([
                CONFIG.STORAGE_KEYS.LICENSE_STATUS,
                CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP
            ]);
            
            this.notifyListeners(null);
            return true;
        } catch (error) {
            console.error('[StateManager] Erro ao limpar licenÃ§a:', error);
            return false;
        }
    }

    // Validar licenÃ§a no servidor
    async validate(email) {
        if (!email || !this.isValidEmail(email)) {
            throw new Error('Email invÃ¡lido');
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);

        try {
            const response = await fetch(CONFIG.WORKER_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const result = await response.json();
            
            // Salvar resultado
            await this.set(result);
            
            return result;
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('Tempo limite excedido. Verifique sua conexÃ£o.');
            }
            
            throw error;
        }
    }

    // Verificar se precisa revalidar
    async needsRevalidation() {
        const result = await chrome.storage.local.get([
            CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP
        ]);
        
        const timestamp = result[CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP];
        
        if (!timestamp) return true;
        
        const age = Date.now() - timestamp;
        return age >= CONFIG.CACHE_DURATION;
    }

    // Adicionar listener para mudanÃ§as
    addListener(callback) {
        this.listeners.push(callback);
        return () => this.removeListener(callback);
    }

    // Remover listener
    removeListener(callback) {
        this.listeners = this.listeners.filter(l => l !== callback);
    }

    // Notificar todos os listeners
    notifyListeners(license) {
        this.listeners.forEach(callback => {
            try {
                callback(license);
            } catch (error) {
                console.error('[StateManager] Erro no listener:', error);
            }
        });
    }

    // Configurar listener de storage para sincronizaÃ§Ã£o entre abas
    setupStorageListener() {
        chrome.storage.onChanged.addListener((changes, area) => {
            if (area === 'local' && changes[CONFIG.STORAGE_KEYS.LICENSE_STATUS]) {
                const newValue = changes[CONFIG.STORAGE_KEYS.LICENSE_STATUS].newValue;
                this.notifyListeners(newValue);
            }
        });
    }

    // Validar formato de email
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Obter informaÃ§Ãµes de debug
    async getDebugInfo() {
        const license = await this.get();
        const result = await chrome.storage.local.get([
            CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP
        ]);
        
        return {
            hasLicense: !!license,
            isValid: license?.valid || false,
            timestamp: result[CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP],
            age: result[CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP] 
                ? Date.now() - result[CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP]
                : null,
            needsRevalidation: await this.needsRevalidation()
        };
    }
}

// InstÃ¢ncia global
const licenseState = new LicenseStateManager();