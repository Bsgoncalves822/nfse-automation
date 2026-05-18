// ============================================
// POPUP - INTERFACE PRINCIPAL
// ============================================

// Gerenciador de UI local
class PopupUI {
    constructor() {
        this.elements = {};
        this.message = new UIMessage('status-message');
        this.isValidating = false;
        
        this.init();
    }

    // Inicializar
    async init() {
        this.cacheElements();
        this.setupEventListeners();
        await this.loadStoredLicense();
        this.setupStateListener();
        this.checkConnectionStatus();
    }

    // Cachear elementos do DOM
    cacheElements() {
        this.elements = {
            statusMessage: document.getElementById('status-message'),
            inputArea: document.getElementById('input-area'),
            infoArea: document.getElementById('info-area'),
            requestLicenseArea: document.getElementById('request-license-area'),
            licenseKeyInput: document.getElementById('license-key'),
            validateBtn: document.getElementById('validate-btn'),
            clearBtn: document.getElementById('clear-btn'),
            buyLicenseBtn: document.getElementById('buy-license-btn'),
            manageTeamBtn: document.getElementById('manage-team-btn'),
            teamInfo: document.getElementById('team-info'),
            connectionStatus: document.getElementById('connection-status')
        };
    }

    // Configurar event listeners
    setupEventListeners() {
        // Validar com debounce
        const debouncedValidate = Utils.debounce(() => this.validateLicense(), 300);
        
        this.elements.validateBtn?.addEventListener('click', debouncedValidate);
        
        // Enter no input
        this.elements.licenseKeyInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.isValidating) {
                debouncedValidate();
            }
        });

        // Limpar
        this.elements.clearBtn?.addEventListener('click', () => this.clearLicense());

        // Comprar
        this.elements.buyLicenseBtn?.addEventListener('click', () => this.openSalesPage());

        // Gerenciar equipe
        this.elements.manageTeamBtn?.addEventListener('click', () => this.openTeamManager());

        // Listener de conexão
        document.addEventListener('connectionChanged', (e) => {
            this.updateConnectionStatus(e.detail.online);
        });

        // Auto-validação quando input muda (opcional)
        this.elements.licenseKeyInput?.addEventListener('input', (e) => {
            const email = e.target.value.trim();
            if (email && Utils.isValidEmail(email)) {
                // Remover mensagem de erro quando email fica válido
                if (this.message.container.classList.contains('error')) {
                    this.message.hide();
                }
            }
        });
    }

    // Carregar licença armazenada
    async loadStoredLicense() {
        try {
            const license = await licenseState.get();
            this.updateUI(license);

            // Verificar se precisa revalidar silenciosamente
            const needsRevalidation = await licenseState.needsRevalidation();
            if (needsRevalidation && license?.data?.email) {
                Utils.log('Popup', 'Cache expirado, revalidando...');
                this.revalidateSilently(license.data.email);
            }
        } catch (error) {
            Utils.log('Popup', 'Erro ao carregar licença', error);
            this.updateUI(null);
        }
    }

    // Revalidar silenciosamente em background
    async revalidateSilently(email) {
        try {
            await licenseState.validate(email);
            Utils.log('Popup', 'Revalidação silenciosa concluída');
        } catch (error) {
            Utils.log('Popup', 'Erro na revalidação silenciosa', error);
            // Não mostrar erro para o usuário, pois ainda tem cache
        }
    }

    // Configurar listener para mudanças de estado
    setupStateListener() {
        licenseState.addListener((license) => {
            this.updateUI(license);
        });
    }

    // Validar licença
    async validateLicense() {
        // Prevenir múltiplas validações simultâneas
        if (this.isValidating) {
            Utils.log('Popup', 'Validação já em progresso');
            return;
        }

        const email = Utils.sanitizeEmail(this.elements.licenseKeyInput.value);

        // Validações
        if (!email) {
            this.message.warning('Por favor, insira seu email.');
            this.elements.licenseKeyInput.focus();
            return;
        }

        if (!Utils.isValidEmail(email)) {
            this.message.error('⚠️ Email inválido. Verifique o formato.');
            this.elements.licenseKeyInput.focus();
            return;
        }

        // Verificar conexão
        if (!Utils.isOnline()) {
            this.message.error('❌ Sem conexão com a internet. Verifique sua rede.');
            return;
        }

        // Iniciar validação
        this.isValidating = true;
        this.setValidationState(true);
        loadingManager.start('validation');

        try {
            Utils.log('Popup', `Validando email: ${email}`);
            
            const result = await licenseState.validate(email);

            Utils.log('Popup', 'Resultado da validação:', result);

            if (result.valid) {
                this.message.success('✅ ' + result.message);
                this.elements.licenseKeyInput.value = '';
                
                // Notificar content scripts
                this.notifyContentScripts(result);
                
                // Analytics (opcional)
                this.trackEvent('license_validated', { status: 'success' });
            } else {
                this.message.error('❌ ' + result.message);
                this.trackEvent('license_validated', { status: 'failed' });
            }

        } catch (error) {
            Utils.log('Popup', 'Erro ao validar', error);
            
            let errorMessage = 'Erro ao validar assinatura.';
            
            if (error.message.includes('Tempo limite')) {
                errorMessage = '⏱️ Tempo limite excedido. Verifique sua conexão.';
            } else if (error.message.includes('internet')) {
                errorMessage = '🌐 ' + error.message;
            } else {
                errorMessage = `❌ ${error.message}`;
            }
            
            this.message.error(errorMessage, 7000);
            this.trackEvent('license_validation_error', { error: error.message });

        } finally {
            this.isValidating = false;
            this.setValidationState(false);
            loadingManager.stop('validation');
        }
    }

    // Atualizar estado do botão de validação
    setValidationState(validating) {
        const btn = this.elements.validateBtn;
        if (!btn) return;

        btn.disabled = validating;
        btn.textContent = validating ? '🔄 Validando...' : 'Validar Assinatura';
        
        if (validating) {
            btn.classList.add('loading');
        } else {
            btn.classList.remove('loading');
        }
    }

    // Atualizar UI baseado no status da licença
    updateUI(license) {
        const isValid = license?.valid;

        // Atualizar mensagem de status
        this.updateStatusMessage(license);

        // Mostrar/esconder áreas
        this.elements.inputArea.style.display = isValid ? 'none' : 'flex';
        this.elements.infoArea.style.display = isValid ? 'block' : 'none';
        this.elements.requestLicenseArea.style.display = isValid ? 'none' : 'block';

        if (isValid && license.data) {
            this.updateLicenseInfo(license.data);
        }

        // Adicionar indicador de cache
        if (license?.fromCache) {
            this.addCacheIndicator();
        }
    }

    // Atualizar mensagem de status
    updateStatusMessage(license) {
        const statusEl = this.elements.statusMessage;
        if (!statusEl) return;

        if (license?.valid) {
            statusEl.textContent = `✅ ${license.message}`;
            statusEl.className = 'status-message success';
        } else if (license?.message) {
            statusEl.textContent = `❌ ${license.message}`;
            statusEl.className = 'status-message error';
        } else {
            statusEl.textContent = 'Insira seu email para validar assinatura';
            statusEl.className = 'status-message info';
        }
    }

    // Atualizar informações da licença
    updateLicenseInfo(data) {
        // Informações básicas
        this.setElementText('info-name', data.name || 'N/A');
        this.setElementText('info-status', 
            data.status + (data.isTrial ? ' (Trial)' : ''));
        this.setElementText('info-plan', data.planName || 'N/A');
        
        // Formatar data de próxima cobrança
        let nextChargeText = 'Cobrança recorrente';
        if (data.nextChargeDate) {
            const formatted = Utils.formatDate(data.nextChargeDate);
            if (formatted && formatted !== 'N/A') {
                nextChargeText = formatted;
            }
        }
        this.setElementText('info-expiration', nextChargeText);

        // Informações de equipe
        if (data.team?.isTeamPlan) {
            this.elements.teamInfo.style.display = 'flex';
            this.setElementText('info-team-usage', 
                `${data.team.currentUsers}/${data.team.maxUsers}`);
            
            // Botão de gerenciar apenas para titular
            if (this.elements.manageTeamBtn) {
                this.elements.manageTeamBtn.style.display = 
                    data.team.isOwner ? 'block' : 'none';
            }
        } else {
            this.elements.teamInfo.style.display = 'none';
            if (this.elements.manageTeamBtn) {
                this.elements.manageTeamBtn.style.display = 'none';
            }
        }
    }

    // Helper para atualizar texto de elemento
    setElementText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    // Adicionar indicador de cache
    addCacheIndicator() {
        const statusEl = this.elements.statusMessage;
        if (!statusEl) return;

        const existingBadge = statusEl.querySelector('.cache-badge');
        if (existingBadge) return;

        const badge = document.createElement('span');
        badge.className = 'cache-badge';
        badge.textContent = '💾 Cache';
        badge.title = 'Informação em cache';
        badge.style.cssText = 'font-size: 10px; margin-left: 8px; opacity: 0.7;';
        
        statusEl.appendChild(badge);
    }

    // Limpar licença
    async clearLicense() {
        if (!confirm('Deseja realmente limpar a licença salva?')) {
            return;
        }

        try {
            await licenseState.clear();
            this.elements.licenseKeyInput.value = '';
            this.message.info('Licença removida com sucesso.');
            
            // Notificar content scripts
            this.notifyContentScripts(null);
            
            this.trackEvent('license_cleared');
        } catch (error) {
            Utils.log('Popup', 'Erro ao limpar licença', error);
            this.message.error('Erro ao limpar licença.');
        }
    }

    // Notificar content scripts
    notifyContentScripts(license) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (chrome.runtime.lastError) {
                Utils.log('Popup', 'Erro ao query tabs', chrome.runtime.lastError);
                return;
            }

            if (tabs[0]?.id) {
                chrome.tabs.sendMessage(
                    tabs[0].id,
                    { 
                        type: 'LICENSE_UPDATED', 
                        status: license 
                    },
                    (response) => {
                        if (chrome.runtime.lastError) {
                            // Ignorar erro se content script não estiver carregado
                            Utils.log('Popup', 'Content script não disponível');
                        }
                    }
                );
            }
        });
    }

    // Abrir página de vendas
    openSalesPage() {
        chrome.tabs.create({ 
            url: CONFIG.SALES_PAGE_URL,
            active: true 
        }, (tab) => {
            // Fallback para Hotmart se falhar
            if (!tab || chrome.runtime.lastError) {
                window.open(CONFIG.HOTMART_CHECKOUT_URL, '_blank');
            }
        });

        this.trackEvent('sales_page_opened');
    }

    // Abrir gerenciador de equipe
    openTeamManager() {
        chrome.tabs.create({ 
            url: chrome.runtime.getURL('team-manager.html'),
            active: true 
        });

        this.trackEvent('team_manager_opened');
    }

    // Atualizar status de conexão
    updateConnectionStatus(online) {
        const statusEl = this.elements.connectionStatus;
        if (!statusEl) return;

        if (online) {
            statusEl.style.display = 'none';
        } else {
            statusEl.style.display = 'block';
            statusEl.textContent = '⚠️ Sem conexão com a internet';
            statusEl.className = 'connection-status offline';
        }
    }

    // Verificar status de conexão
    checkConnectionStatus() {
        this.updateConnectionStatus(Utils.isOnline());
    }

    // Track eventos (analytics - implementar se necessário)
    trackEvent(eventName, data = {}) {
        Utils.log('Analytics', eventName, data);
        // Implementar integração com analytics aqui
    }
}

// Inicializar quando DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    new PopupUI();
});