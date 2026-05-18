// ============================================
// GERENCIADOR DE EQUIPE
// ============================================

class TeamManager {
    constructor() {
        this.currentTeamData = null;
        this.currentLicenseData = null;
        this.message = new UIMessage('message');
        this.isLoading = false;
        this.pendingOperations = new Set();
        
        this.init();
    }

    // Inicializar
    async init() {
        this.cacheElements();
        this.setupEventListeners();
        await this.loadTeamData();
        this.setupStateListener();
    }

    // Cachear elementos
    cacheElements() {
        this.elements = {
            loading: document.getElementById('loading'),
            mainContent: document.getElementById('main-content'),
            addSection: document.getElementById('add-section'),
            
            // Stats
            statTotal: document.getElementById('stat-total'),
            statUsed: document.getElementById('stat-used'),
            statAvailable: document.getElementById('stat-available'),
            
            // Plan info
            planName: document.getElementById('plan-name'),
            ownerEmail: document.getElementById('owner-email'),
            planStatus: document.getElementById('plan-status'),
            nextCharge: document.getElementById('next-charge'),
            
            // Slots e membros
            slotsContainer: document.getElementById('slots-container'),
            membersList: document.getElementById('members-list'),
            memberCount: document.getElementById('member-count'),
            
            // Inputs
            newMemberEmail: document.getElementById('new-member-email'),
            addMemberBtn: document.getElementById('add-member-btn'),
            
            // Botões
            backBtn: document.getElementById('back-btn'),
            refreshBtn: document.getElementById('refresh-btn')
        };
    }

    // Configurar event listeners
    setupEventListeners() {
        // Adicionar membro com debounce
        const debouncedAdd = Utils.debounce(() => this.addMember(), 300);
        
        this.elements.addMemberBtn?.addEventListener('click', debouncedAdd);

        // Enter no input
        this.elements.newMemberEmail?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.isOperationPending('add')) {
                debouncedAdd();
            }
        });

        // Auto-validação do email
        this.elements.newMemberEmail?.addEventListener('input', (e) => {
            this.validateEmailInput(e.target.value);
        });

        // Botões de navegação
        this.elements.backBtn?.addEventListener('click', () => window.close());
        this.elements.refreshBtn?.addEventListener('click', () => this.refresh());

        // Listener de conexão
        document.addEventListener('connectionChanged', (e) => {
            if (e.detail.online) {
                this.message.info('Conexão restaurada');
            } else {
                this.message.warning('Sem conexão com a internet', 0);
            }
        });
    }

    // Configurar listener de estado
    setupStateListener() {
        licenseState.addListener((license) => {
            if (license?.data?.team) {
                this.currentTeamData = license.data.team;
                this.currentLicenseData = license.data;
                this.updateUI();
            }
        });
    }

    // ============================================
    // CARREGAMENTO DE DADOS
    // ============================================

    async loadTeamData() {
        try {
            this.showLoading(true);

            // Buscar dados salvos
            const license = await licenseState.get();

            // Validações
            if (!license?.valid) {
                this.showError('Nenhuma assinatura válida encontrada. Por favor, valide sua assinatura primeiro.');
                return;
            }

            if (!license.data.team?.isTeamPlan) {
                this.showError('Esta assinatura não é um plano de equipe.');
                return;
            }

            if (!license.data.team.isOwner) {
                this.showError('Somente o titular pode gerenciar a equipe.');
                this.elements.addSection.style.display = 'none';
                return;
            }

            // Atualizar dados locais
            this.currentTeamData = license.data.team;
            this.currentLicenseData = license.data;

            // Atualizar UI
            this.updateUI();
            
            // Verificar se precisa revalidar
            const needsRevalidation = await licenseState.needsRevalidation();
            if (needsRevalidation) {
                await this.revalidateAndReload(true); // silent = true
            }

        } catch (error) {
            Utils.log('TeamManager', 'Erro ao carregar dados', error);
            this.showError('Erro ao carregar dados da equipe: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    // ============================================
    // ATUALIZAÇÃO DE UI
    // ============================================

    updateUI() {
        if (!this.currentTeamData || !this.currentLicenseData) return;

        this.updateStats();
        this.updatePlanInfo();
        this.renderSlots();
        this.renderMembers();
    }

    // Atualizar estatísticas
    updateStats() {
        this.elements.statTotal.textContent = this.currentTeamData.maxUsers;
        this.elements.statUsed.textContent = this.currentTeamData.currentUsers;
        this.elements.statAvailable.textContent = this.currentTeamData.availableSlots;

        // Animação nos números
        this.animateNumber(this.elements.statUsed, this.currentTeamData.currentUsers);
        this.animateNumber(this.elements.statAvailable, this.currentTeamData.availableSlots);
    }

    // Atualizar informações do plano
    updatePlanInfo() {
        this.elements.planName.textContent = this.currentLicenseData.planName || '-';
        this.elements.ownerEmail.textContent = 
            this.currentTeamData.ownerEmail || this.currentLicenseData.email || '-';
        
        const statusText = this.currentLicenseData.status + 
            (this.currentLicenseData.isTrial ? ' (Trial)' : '');
        this.elements.planStatus.textContent = statusText;
        
        this.elements.nextCharge.textContent = 
            Utils.formatDate(this.currentLicenseData.nextChargeDate) || '-';
    }

    // Renderizar slots visuais
    renderSlots() {
        const container = this.elements.slotsContainer;
        container.innerHTML = '';

        const totalSlots = this.currentTeamData.maxUsers;
        const usedSlots = this.currentTeamData.currentUsers;

        const fragment = document.createDocumentFragment();

        for (let i = 0; i < totalSlots; i++) {
            const slot = Utils.createElement('div', {
                className: i < usedSlots ? 'slot filled' : 'slot empty'
            });

            if (i === 0) {
                slot.textContent = '👑';
                slot.title = 'Titular';
            } else if (i < usedSlots) {
                slot.textContent = '✓';
                slot.title = 'Membro ativo';
            } else {
                slot.textContent = '-';
                slot.title = 'Slot disponível';
            }

            // Animação de entrada
            slot.style.opacity = '0';
            slot.style.transform = 'scale(0.8)';
            
            fragment.appendChild(slot);

            // Animar com delay
            setTimeout(() => {
                Utils.animate(slot, [
                    { opacity: 0, transform: 'scale(0.8)' },
                    { opacity: 1, transform: 'scale(1)' }
                ], {
                    duration: 300,
                    delay: i * 50,
                    fill: 'forwards',
                    easing: 'ease-out'
                });
            }, 10);
        }

        container.appendChild(fragment);
    }

    // Renderizar lista de membros
    renderMembers() {
        const container = this.elements.membersList;
        const members = this.currentTeamData.members || [];

        // Atualizar contador
        const countText = 
            members.length === 0 ? 'Nenhum membro' :
            members.length === 1 ? '1 membro' :
            `${members.length} membros`;
        
        this.elements.memberCount.textContent = countText;

        // Estado vazio
        if (members.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <div class="empty-state-text">Nenhum membro adicionado ainda</div>
                    <div class="empty-state-subtext">Adicione membros abaixo para compartilhar o acesso</div>
                </div>
            `;
            return;
        }

        // Renderizar lista
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        members.forEach((email, index) => {
            const item = this.createMemberItem(email, index);
            fragment.appendChild(item);
        });

        container.appendChild(fragment);
    }

    // Criar item de membro
    createMemberItem(email, index) {
        const initial = Utils.getInitial(email);

        const item = Utils.createElement('div', {
            className: 'member-item',
            style: { opacity: 0, transform: 'translateY(-10px)' }
        });

        item.innerHTML = `
            <div class="member-info">
                <div class="member-avatar">${Utils.escapeHtml(initial)}</div>
                <div class="member-details">
                    <div class="member-email" title="${Utils.escapeHtml(email)}">
                        ${Utils.escapeHtml(email)}
                    </div>
                    <span class="member-badge badge-member">Membro ${index + 1}</span>
                </div>
            </div>
            <button class="remove-btn" data-email="${Utils.escapeHtml(email)}" 
                    title="Remover ${Utils.escapeHtml(email)}">
                🗑️ Remover
            </button>
        `;

        // Event listener no botão de remover
        const removeBtn = item.querySelector('.remove-btn');
        removeBtn.addEventListener('click', () => {
            this.removeMember(removeBtn.dataset.email);
        });

        // Animação de entrada
        setTimeout(() => {
            Utils.animate(item, [
                { opacity: 0, transform: 'translateY(-10px)' },
                { opacity: 1, transform: 'translateY(0)' }
            ], {
                duration: 300,
                delay: index * 50,
                fill: 'forwards',
                easing: 'ease-out'
            });
        }, 10);

        return item;
    }

    // ============================================
    // OPERAÇÕES DE EQUIPE
    // ============================================

    // Adicionar membro
    async addMember() {
        const email = Utils.sanitizeEmail(this.elements.newMemberEmail.value);

        // Validações
        if (!this.validateAddMember(email)) {
            return;
        }

        // Prevenir múltiplas operações
        if (this.isOperationPending('add')) {
            return;
        }

        this.startOperation('add');
        this.setAddButtonState(true);

        try {
            Utils.log('TeamManager', `Adicionando membro: ${email}`);

            const response = await apiClient.addTeamMember(
                this.currentTeamData.subscriberCode,
                email,
                this.currentLicenseData.email // Email do usuário logado (titular)
            );

            if (response.success) {
                this.message.success(`✅ ${email} foi adicionado com sucesso à equipe!`);
                this.elements.newMemberEmail.value = '';

                // Atualização otimista da UI
                this.optimisticAddMember(email);

                // Revalidar em background
                setTimeout(() => this.revalidateAndReload(true), 1000);

                this.trackEvent('member_added', { email });
            } else {
                throw new Error(response.message || 'Falha ao adicionar membro');
            }

        } catch (error) {
            Utils.log('TeamManager', 'Erro ao adicionar membro', error);
            this.message.error('Erro ao adicionar membro: ' + error.message);
            this.trackEvent('member_add_error', { error: error.message });

        } finally {
            this.stopOperation('add');
            this.setAddButtonState(false);
        }
    }

    // Remover membro
    async removeMember(email) {
        if (!confirm(`Tem certeza que deseja remover ${email} da equipe?\n\nO acesso será revogado imediatamente.`)) {
            return;
        }

        // Prevenir múltiplas operações
        if (this.isOperationPending(`remove-${email}`)) {
            return;
        }

        this.startOperation(`remove-${email}`);

        try {
            Utils.log('TeamManager', `Removendo membro: ${email}`);

            const response = await apiClient.removeTeamMember(
                this.currentTeamData.subscriberCode,
                email,
                this.currentLicenseData.email // Email do usuário logado (titular)
            );

            if (response.success) {
                this.message.success(`✅ ${email} foi removido da equipe.`);

                // Atualização otimista da UI
                this.optimisticRemoveMember(email);

                // Revalidar em background
                setTimeout(() => this.revalidateAndReload(true), 1000);

                this.trackEvent('member_removed', { email });
            } else {
                throw new Error(response.message || 'Falha ao remover membro');
            }

        } catch (error) {
            Utils.log('TeamManager', 'Erro ao remover membro', error);
            this.message.error('Erro ao remover membro: ' + error.message);
            this.trackEvent('member_remove_error', { error: error.message });

        } finally {
            this.stopOperation(`remove-${email}`);
        }
    }

    // ============================================
    // VALIDAÇÕES
    // ============================================

    validateAddMember(email) {
        if (!email) {
            this.message.warning('Digite um email válido.');
            this.elements.newMemberEmail.focus();
            return false;
        }

        if (!Utils.isValidEmail(email)) {
            this.message.error('Email inválido. Verifique o formato.');
            this.elements.newMemberEmail.focus();
            return false;
        }

        if (!this.currentTeamData) {
            this.message.error('Dados da equipe não carregados.');
            return false;
        }

        if (this.currentTeamData.availableSlots <= 0) {
            this.message.error(
                `Limite de ${this.currentTeamData.maxUsers} acessos atingido. ` +
                `Remova um membro para adicionar outro.`
            );
            return false;
        }

        if (this.currentTeamData.members.includes(email)) {
            this.message.error('Este email já está na equipe.');
            return false;
        }

        const ownerEmail = this.currentTeamData.ownerEmail || this.currentLicenseData.email;
        if (email === ownerEmail) {
            this.message.error('Este é o email do titular. Não é necessário adicioná-lo como membro.');
            return false;
        }

        return true;
    }

    // Validar input de email em tempo real
    validateEmailInput(email) {
        const input = this.elements.newMemberEmail;
        if (!input) return;

        if (!email) {
            input.classList.remove('valid', 'invalid');
            return;
        }

        if (Utils.isValidEmail(email)) {
            input.classList.add('valid');
            input.classList.remove('invalid');
        } else {
            input.classList.add('invalid');
            input.classList.remove('valid');
        }
    }

    // ============================================
    // ATUALIZAÇÕES OTIMISTAS
    // ============================================

    optimisticAddMember(email) {
        if (!this.currentTeamData) return;

        this.currentTeamData.members.push(email);
        this.currentTeamData.currentUsers++;
        this.currentTeamData.availableSlots--;

        this.updateUI();
    }

    optimisticRemoveMember(email) {
        if (!this.currentTeamData) return;

        const index = this.currentTeamData.members.indexOf(email);
        if (index > -1) {
            this.currentTeamData.members.splice(index, 1);
            this.currentTeamData.currentUsers--;
            this.currentTeamData.availableSlots++;

            this.updateUI();
        }
    }

    // ============================================
    // REVALIDAÇÃO
    // ============================================

    async revalidateAndReload(silent = false) {
        try {
            if (!silent) {
                this.showLoading(true);
            }

            const email = this.currentLicenseData?.email || this.currentTeamData?.ownerEmail;

            if (!email) {
                throw new Error('Email do titular não encontrado.');
            }

            Utils.log('TeamManager', 'Revalidando assinatura');

            const result = await licenseState.validate(email);

            if (result.valid && result.data.team) {
                this.currentTeamData = result.data.team;
                this.currentLicenseData = result.data;
                this.updateUI();

                if (!silent) {
                    this.message.success('Dados atualizados com sucesso');
                }
            } else {
                throw new Error(result.message || 'Falha na revalidação');
            }

        } catch (error) {
            Utils.log('TeamManager', 'Erro ao revalidar', error);
            
            if (!silent) {
                this.message.error('Erro ao atualizar dados: ' + error.message);
            }

        } finally {
            if (!silent) {
                this.showLoading(false);
            }
        }
    }

    // Refresh manual
    async refresh() {
        await this.revalidateAndReload(false);
        this.trackEvent('manual_refresh');
    }

    // ============================================
    // GERENCIAMENTO DE ESTADO DE UI
    // ============================================

    showLoading(show) {
        this.isLoading = show;
        this.elements.loading.style.display = show ? 'block' : 'none';
        this.elements.mainContent.style.display = show ? 'none' : 'block';
    }

    showError(text) {
        this.elements.mainContent.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-text">${Utils.escapeHtml(text)}</div>
                <div style="margin-top: 20px;">
                    <button class="btn-secondary" onclick="window.close()">← Voltar</button>
                </div>
            </div>
        `;
        this.elements.mainContent.style.display = 'block';
    }

    setAddButtonState(loading) {
        const btn = this.elements.addMemberBtn;
        if (!btn) return;

        btn.disabled = loading;
        btn.textContent = loading ? '⏳ Adicionando...' : 'Adicionar Membro';
        
        if (loading) {
            btn.classList.add('loading');
        } else {
            btn.classList.remove('loading');
        }
    }

    // Gerenciar operações pendentes
    startOperation(id) {
        this.pendingOperations.add(id);
    }

    stopOperation(id) {
        this.pendingOperations.delete(id);
    }

    isOperationPending(id) {
        return this.pendingOperations.has(id);
    }

    // ============================================
    // ANIMAÇÕES
    // ============================================

    animateNumber(element, targetValue) {
        if (!element) return;

        const currentValue = parseInt(element.textContent) || 0;
        const diff = targetValue - currentValue;
        const duration = 500;
        const steps = 20;
        const stepValue = diff / steps;
        const stepDuration = duration / steps;

        let current = currentValue;
        let step = 0;

        const interval = setInterval(() => {
            step++;
            current += stepValue;

            if (step >= steps) {
                element.textContent = targetValue;
                clearInterval(interval);
            } else {
                element.textContent = Math.round(current);
            }
        }, stepDuration);
    }

    // ============================================
    // ANALYTICS
    // ============================================

    trackEvent(eventName, data = {}) {
        Utils.log('Analytics', eventName, data);
        // Implementar integração com analytics aqui
    }
}

// Inicializar quando DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    new TeamManager();
});