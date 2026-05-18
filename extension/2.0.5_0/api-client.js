// ============================================
// MÓDULO DE API - COMUNICAÇÃO COM SERVIDOR
// ============================================

class APIClient {
    constructor(baseUrl = CONFIG.WORKER_URL) {
        this.baseUrl = baseUrl;
        this.requestQueue = [];
        this.processing = false;
    }

    // Fazer requisição com retry automático
    async request(endpoint = '', data = {}, options = {}) {
        const {
            method = 'POST',
            timeout = CONFIG.REQUEST_TIMEOUT,
            retries = CONFIG.MAX_RETRY_ATTEMPTS
        } = options;

        // Verificar conexão
        if (!Utils.isOnline()) {
            throw new Error('Sem conexão com a internet. Verifique sua rede.');
        }

        return Utils.retryWithBackoff(async () => {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);

            try {
                const url = endpoint ? `${this.baseUrl}${endpoint}` : this.baseUrl;
                
                const response = await fetch(url, {
                    method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Extension-Version': chrome.runtime.getManifest().version
                    },
                    body: JSON.stringify(data),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                // Verificar rate limit
                if (response.status === 429) {
                    const retryAfter = response.headers.get('Retry-After');
                    throw new Error(`Muitas requisições. Tente novamente em ${retryAfter || 60} segundos.`);
                }

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.message || `Erro HTTP: ${response.status}`);
                }

                const result = await response.json();
                
                Utils.log('API', `Requisição bem-sucedida: ${method} ${endpoint}`, result);
                
                return result;

            } catch (error) {
                clearTimeout(timeoutId);

                if (error.name === 'AbortError') {
                    throw new Error('Tempo limite excedido. Verifique sua conexão.');
                }

                Utils.log('API', `Falha na requisição: ${method} ${endpoint}`, error);
                throw error;
            }
        }, retries);
    }

    // Validar email
    async validateEmail(email) {
        return this.request('', { email }, {
            timeout: 15000 // 15 segundos para validação
        });
    }

    // Adicionar membro à equipe
    async addTeamMember(subscriberCode, memberEmail, requestorEmail) {
        return this.request('', {
            action: 'add_member',
            subscriberCode,
            memberEmail,
            requestorEmail
        });
    }

    // Remover membro da equipe
    async removeTeamMember(subscriberCode, memberEmail, requestorEmail) {
        return this.request('', {
            action: 'remove_member',
            subscriberCode,
            memberEmail,
            requestorEmail
        });
    }

    // Listar membros da equipe
    async listTeamMembers(subscriberCode) {
        return this.request('', {
            action: 'list_members',
            subscriberCode
        });
    }

    // Verificar status do servidor
    async ping() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const response = await fetch(this.baseUrl, {
                method: 'GET',
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            return response.ok;
        } catch {
            return false;
        }
    }

    // Verificação de integridade
    async healthCheck() {
        try {
            const isOnline = Utils.isOnline();
            const serverOk = await this.ping();

            return {
                online: isOnline,
                serverAvailable: serverOk,
                healthy: isOnline && serverOk
            };
        } catch (error) {
            return {
                online: Utils.isOnline(),
                serverAvailable: false,
                healthy: false,
                error: error.message
            };
        }
    }
}

// Instância global
const apiClient = new APIClient();

// Monitorar conexão
window.addEventListener('online', () => {
    Utils.log('Network', 'Conexão restaurada');
    document.dispatchEvent(new CustomEvent('connectionChanged', {
        detail: { online: true }
    }));
});

window.addEventListener('offline', () => {
    Utils.log('Network', 'Conexão perdida');
    document.dispatchEvent(new CustomEvent('connectionChanged', {
        detail: { online: false }
    }));
});