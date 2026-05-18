// ============================================
// BACKGROUND SERVICE WORKER
// ============================================

// Estado global do service worker
const workerState = {
    initialized: false,
    lastValidation: null,
    alarmScheduled: false
};

// Inicialização
chrome.runtime.onInstalled.addListener(async (details) => {
    Utils.log('Background', 'Extensão instalada/atualizada', details);

    if (details.reason === 'install') {
        // Primeira instalação
        await handleFirstInstall();
    } else if (details.reason === 'update') {
        // Atualização
        await handleUpdate(details.previousVersion);
    }

    // Configurar alarmes
    await setupAlarms();
});

// Inicialização ao iniciar
chrome.runtime.onStartup.addListener(async () => {
    Utils.log('Background', 'Service worker iniciado');
    workerState.initialized = true;
    
    // Verificar alarmes
    await setupAlarms();
});

// ============================================
// ALARMES - REVALIDAÇÃO AUTOMÁTICA
// ============================================

async function setupAlarms() {
    try {
        // Limpar alarmes existentes
        await chrome.alarms.clearAll();

        // Criar alarme para revalidação periódica
        await chrome.alarms.create('periodicValidation', {
            periodInMinutes: CONFIG.REVALIDATE_INTERVAL
        });

        workerState.alarmScheduled = true;
        Utils.log('Background', `Alarme configurado: a cada ${CONFIG.REVALIDATE_INTERVAL} minutos`);
    } catch (error) {
        Utils.log('Background', 'Erro ao configurar alarmes', error);
    }
}

// Listener de alarmes
chrome.alarms.onAlarm.addListener(async (alarm) => {
    Utils.log('Background', 'Alarme disparado:', alarm.name);

    if (alarm.name === 'periodicValidation') {
        await handlePeriodicValidation();
    }
});

// Revalidação periódica
async function handlePeriodicValidation() {
    try {
        // Obter licença atual
        const license = await licenseState.get();

        if (!license?.valid || !license?.data?.email) {
            Utils.log('Background', 'Nenhuma licença válida para revalidar');
            return;
        }

        // Verificar se realmente precisa revalidar
        const needsRevalidation = await licenseState.needsRevalidation();
        
        if (!needsRevalidation) {
            Utils.log('Background', 'Cache ainda válido, pulando revalidação');
            return;
        }

        Utils.log('Background', 'Iniciando revalidação automática');

        // Revalidar
        const result = await licenseState.validate(license.data.email);

        // Notificar sobre mudanças
        if (result.valid !== license.valid) {
            await notifyLicenseStatusChange(result);
        }

        Utils.log('Background', 'Revalidação concluída', result);

    } catch (error) {
        Utils.log('Background', 'Erro na revalidação automática', error);
    }
}

// ============================================
// MENSAGENS
// ============================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    Utils.log('Background', 'Mensagem recebida:', request);

    // Processar de forma assíncrona
    handleMessage(request, sender).then(sendResponse);

    // Retornar true para manter o canal aberto
    return true;
});

// Handler de mensagens
async function handleMessage(request, sender) {
    try {
        switch (request.action) {
            case 'ping':
                return { status: 'ok', timestamp: Date.now() };

            case 'validateLicense':
                return await handleValidateLicense(request.email);

            case 'getLicenseStatus':
                return await handleGetLicenseStatus();

            case 'clearLicense':
                return await handleClearLicense();

            case 'healthCheck':
                return await handleHealthCheck();

            case 'getDebugInfo':
                return await handleGetDebugInfo();

            default:
                return { error: 'Ação desconhecida' };
        }
    } catch (error) {
        Utils.log('Background', 'Erro ao processar mensagem', error);
        return { error: error.message };
    }
}

// ============================================
// HANDLERS DE AÇÕES
// ============================================

async function handleValidateLicense(email) {
    try {
        const result = await licenseState.validate(email);
        
        // Notificar todas as tabs
        await notifyAllTabs('LICENSE_UPDATED', result);
        
        return { success: true, result };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function handleGetLicenseStatus() {
    try {
        const license = await licenseState.get();
        return { success: true, license };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function handleClearLicense() {
    try {
        await licenseState.clear();
        
        // Notificar todas as tabs
        await notifyAllTabs('LICENSE_UPDATED', null);
        
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function handleHealthCheck() {
    try {
        const health = await apiClient.healthCheck();
        const license = await licenseState.get();
        
        return {
            success: true,
            health,
            hasLicense: !!license,
            isValid: license?.valid || false
        };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function handleGetDebugInfo() {
    try {
        const debugInfo = await licenseState.getDebugInfo();
        const health = await apiClient.healthCheck();
        
        return {
            success: true,
            debug: {
                ...debugInfo,
                health,
                worker: workerState,
                version: chrome.runtime.getManifest().version
            }
        };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// ============================================
// NOTIFICAÇÕES
// ============================================

// Notificar todas as tabs abertas
async function notifyAllTabs(type, data) {
    try {
        const tabs = await chrome.tabs.query({});
        
        for (const tab of tabs) {
            try {
                await chrome.tabs.sendMessage(tab.id, {
                    type,
                    data
                });
            } catch (error) {
                // Ignorar tabs sem content script
            }
        }
    } catch (error) {
        Utils.log('Background', 'Erro ao notificar tabs', error);
    }
}

// Notificar mudança de status da licença
async function notifyLicenseStatusChange(newStatus) {
    Utils.log('Background', 'Status da licença mudou', newStatus);

    // Notificar via system notification (opcional)
    if (newStatus.valid) {
        await Utils.showNotification(
            'Licença Validada',
            'Sua assinatura foi validada com sucesso!',
            'success'
        );
    } else {
        await Utils.showNotification(
            'Licença Inválida',
            'Sua assinatura não pôde ser validada.',
            'error'
        );
    }

    // Notificar tabs
    await notifyAllTabs('LICENSE_STATUS_CHANGED', newStatus);
}

// ============================================
// INSTALAÇÃO E ATUALIZAÇÃO
// ============================================

async function handleFirstInstall() {
    Utils.log('Background', 'Primeira instalação');

    // Abrir página de boas-vindas (opcional)
    await chrome.tabs.create({
        url: chrome.runtime.getURL('welcome.html'),
        active: true
    });

    // Inicializar configurações padrão
    await chrome.storage.local.set({
        firstInstall: Date.now(),
        version: chrome.runtime.getManifest().version
    });
}

async function handleUpdate(previousVersion) {
    Utils.log('Background', `Atualizado de ${previousVersion} para ${chrome.runtime.getManifest().version}`);

    // Migração de dados se necessário
    await migrateData(previousVersion);

    // Salvar nova versão
    await chrome.storage.local.set({
        lastUpdate: Date.now(),
        version: chrome.runtime.getManifest().version
    });
}

// Migração de dados entre versões
async function migrateData(fromVersion) {
    Utils.log('Background', 'Verificando necessidade de migração de dados');

    try {
        // Implementar migrações específicas aqui
        // Exemplo:
        // if (compareVersions(fromVersion, '2.0.0') < 0) {
        //     await migrateToV2();
        // }

    } catch (error) {
        Utils.log('Background', 'Erro na migração de dados', error);
    }
}

// ============================================
// LIMPEZA E MANUTENÇÃO
// ============================================

// Limpar dados antigos periodicamente
chrome.alarms.create('cleanup', {
    periodInMinutes: 1440 // 24 horas
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
    if (alarm.name === 'cleanup') {
        await performCleanup();
    }
});

async function performCleanup() {
    Utils.log('Background', 'Executando limpeza de dados antigos');

    try {
        // Limpar cache muito antigo
        const result = await chrome.storage.local.get([
            CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP
        ]);

        const timestamp = result[CONFIG.STORAGE_KEYS.VALIDATION_TIMESTAMP];
        
        if (timestamp) {
            const age = Date.now() - timestamp;
            const maxAge = 30 * 24 * 60 * 60 * 1000; // 30 dias

            if (age > maxAge) {
                Utils.log('Background', 'Cache muito antigo, limpando...');
                await licenseState.clear();
            }
        }

    } catch (error) {
        Utils.log('Background', 'Erro na limpeza', error);
    }
}

// ============================================
// KEEP ALIVE (para Service Workers)
// ============================================

// Manter o service worker ativo quando necessário
let keepAliveInterval = null;

function startKeepAlive() {
    if (keepAliveInterval) return;

    keepAliveInterval = setInterval(() => {
        chrome.runtime.getPlatformInfo(() => {
            // Apenas para manter o service worker ativo
        });
    }, 20000); // A cada 20 segundos
}

function stopKeepAlive() {
    if (keepAliveInterval) {
        clearInterval(keepAliveInterval);
        keepAliveInterval = null;
    }
}

// Log de inicialização
Utils.log('Background', 'Service worker carregado', {
    version: chrome.runtime.getManifest().version,
    manifest: chrome.runtime.getManifest().manifest_version
});
