(function() {
    'use strict';

    const LOG_PREFIX = '[NFSE-EXT]';
    
    // ⚠️ VERIFICAÇÃO CRÍTICA: Executar APENAS nas páginas específicas
    const currentUrl = window.location.href;
    const allowedPages = [
        'https://www.nfse.gov.br/EmissorNacional/Notas/Recebidas',
        'https://www.nfse.gov.br/EmissorNacional/Notas/Emitidas'
    ];
    
    const isAllowedPage = allowedPages.some(page => currentUrl.startsWith(page));
    
    if (!isAllowedPage) {
        console.log(`${LOG_PREFIX} Página não permitida. Extensão desativada nesta URL:`, currentUrl);
        console.log(`${LOG_PREFIX} Páginas permitidas:`, allowedPages);
        return; // ⚠️ SAIR IMEDIATAMENTE - não executar nada
    }
    
    console.log(`${LOG_PREFIX} ✅ Página permitida detectada:`, currentUrl);
    
    // Variável para armazenar o status da licença localmente
    let currentLicenseStatus = null;

    console.log(`${LOG_PREFIX} Script iniciado. JSZip disponível:`, typeof JSZip !== 'undefined');
    console.log(`${LOG_PREFIX} ExcelJS disponível:`, typeof ExcelJS !== 'undefined');

    // --- FUNÇÃO DE VERIFICAÇÃO DE LICENÇA ---
    async function checkLicenseAndAlert() {
        if (currentLicenseStatus && currentLicenseStatus.valid) {
            return true;
        }
        
        return new Promise((resolve) => {
            chrome.storage.local.get(['licenseStatus'], function(result) {
                currentLicenseStatus = result.licenseStatus;
                
                if (currentLicenseStatus && currentLicenseStatus.valid) {
                    resolve(true);
                } else {
                    alert('Licença inválida ou não configurada.\n\nClique no ícone da extensão na barra de ferramentas para inserir sua chave.');
                    resolve(false);
                }
            });
        });
    }
    
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === 'LICENSE_UPDATED') {
            currentLicenseStatus = message.status;
            console.log(`${LOG_PREFIX} Status da licença atualizado via popup:`, currentLicenseStatus);
        }
    });

    // --- FUNÇÕES AUXILIARES ---

    // Função para mostrar dialog customizado sobre verificação de canceladas
    function mostrarDialogVerificarCanceladas() {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.style.cssText = `
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0, 0, 0, 0.35);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 99999;
                backdrop-filter: blur(2px);
                animation: nfseOverlayIn 0.18s ease-out;
            `;

            const modal = document.createElement('div');
            modal.style.cssText = `
                background: #ffffff;
                border-radius: 12px;
                width: 460px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.14), 0 1px 4px rgba(0,0,0,0.08);
                border: 1px solid #e8eaed;
                overflow: hidden;
                animation: nfseModalIn 0.2s ease-out;
            `;

            modal.innerHTML = `
                <style>
                    @keyframes nfseOverlayIn { from { opacity: 0; } to { opacity: 1; } }
                    @keyframes nfseModalIn { from { transform: translateY(-12px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
                </style>

                <!-- Header -->
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 20px 24px 18px;
                    border-bottom: 1px solid #e8eaed;
                ">
                    <div style="
                        width: 36px; height: 36px;
                        background: #eef4ff;
                        border: 1.5px solid #bdd0fa;
                        border-radius: 8px;
                        display: flex; align-items: center; justify-content: center;
                        font-size: 17px; flex-shrink: 0;
                    ">🔍</div>
                    <div>
                        <div style="font-size: 15px; font-weight: 700; color: #1e2432; line-height: 1.2;">Verificar notas canceladas?</div>
                        <div style="font-size: 12px; color: #6b7280; margin-top: 2px;">Esta etapa é opcional e ocorre antes de gerar o Excel</div>
                    </div>
                </div>

                <!-- Body -->
                <div style="padding: 20px 24px;">
                    <p style="margin: 0 0 16px; font-size: 13px; color: #4b5563; line-height: 1.6;">
                        A verificação consulta cada nota individualmente para identificar cancelamentos por substituição — útil para relatórios mais precisos.
                    </p>

                    <div style="display: flex; gap: 10px; margin-bottom: 4px;">
                        <!-- Com verificação -->
                        <div style="
                            flex: 1; padding: 12px 14px;
                            background: #edfaf1;
                            border: 1.5px solid #b7e5c7;
                            border-radius: 8px;
                        ">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
                                <span style="
                                    width: 18px; height: 18px;
                                    background: #1a7f3c; color: white;
                                    border-radius: 50%;
                                    display: inline-flex; align-items: center; justify-content: center;
                                    font-size: 11px; font-weight: 700; flex-shrink: 0;
                                ">✓</span>
                                <span style="font-size: 12px; font-weight: 700; color: #1a7f3c;">Com verificação</span>
                            </div>
                            <div style="font-size: 11px; color: #374151; line-height: 1.5;">
                                Relatório completo<br>
                                <span style="color: #6b7280;">~1-2 min por 100 notas</span>
                            </div>
                        </div>

                        <!-- Sem verificação -->
                        <div style="
                            flex: 1; padding: 12px 14px;
                            background: #fff8ed;
                            border: 1.5px solid #fed9a0;
                            border-radius: 8px;
                        ">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
                                <span style="
                                    width: 18px; height: 18px;
                                    background: #92540b; color: white;
                                    border-radius: 50%;
                                    display: inline-flex; align-items: center; justify-content: center;
                                    font-size: 11px; font-weight: 700; flex-shrink: 0;
                                ">→</span>
                                <span style="font-size: 12px; font-weight: 700; color: #92540b;">Pular verificação</span>
                            </div>
                            <div style="font-size: 11px; color: #374151; line-height: 1.5;">
                                Processamento rápido<br>
                                <span style="color: #6b7280;">Só detecta subst. no mesmo lote</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div style="
                    display: flex;
                    gap: 10px;
                    justify-content: flex-end;
                    padding: 14px 24px;
                    background: #f9fafb;
                    border-top: 1px solid #e8eaed;
                ">
                    <button id="btnNaoVerificar" style="
                        padding: 9px 18px;
                        border: 1.5px solid #e5e7eb;
                        background: #ffffff;
                        border-radius: 7px;
                        cursor: pointer;
                        font-size: 13px;
                        font-weight: 600;
                        color: #4b5563;
                        transition: all 0.15s;
                        letter-spacing: 0.01em;
                    ">Pular</button>
                    <button id="btnVerificar" style="
                        padding: 9px 18px;
                        border: 1.5px solid #b7e5c7;
                        background: #edfaf1;
                        color: #1a7f3c;
                        border-radius: 7px;
                        cursor: pointer;
                        font-size: 13px;
                        font-weight: 600;
                        transition: all 0.15s;
                        letter-spacing: 0.01em;
                    ">Verificar canceladas</button>
                </div>
            `;

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            const btnNao = modal.querySelector('#btnNaoVerificar');
            const btnSim = modal.querySelector('#btnVerificar');

            btnNao.addEventListener('mouseenter', () => { btnNao.style.filter = 'brightness(0.94)'; });
            btnNao.addEventListener('mouseleave', () => { btnNao.style.filter = 'none'; });
            btnSim.addEventListener('mouseenter', () => { btnSim.style.filter = 'brightness(0.93)'; });
            btnSim.addEventListener('mouseleave', () => { btnSim.style.filter = 'none'; });

            // Fechar ao clicar fora do modal
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    document.body.removeChild(overlay);
                    resolve(false);
                }
            });

            btnNao.addEventListener('click', () => {
                document.body.removeChild(overlay);
                resolve(false);
            });

            btnSim.addEventListener('click', () => {
                document.body.removeChild(overlay);
                resolve(true);
            });

            const handleEsc = (e) => {
                if (e.key === 'Escape') {
                    document.body.removeChild(overlay);
                    document.removeEventListener('keydown', handleEsc);
                    resolve(false);
                }
            };
            document.addEventListener('keydown', handleEsc);
        });
    }

    // Cache para evitar verificar a mesma URL múltiplas vezes
    const cancelamentoCache = new Map();
    
    // Função para limpar cache quando necessário (pode ser chamada manualmente se necessário)
    function clearCancelamentoCache() {
        cancelamentoCache.clear();
        console.log(`${LOG_PREFIX} Cache de cancelamento limpo.`);
    }

    async function checkCanceladaPorSubstituicao(visualizarUrl) {
        // Verificar cache primeiro
        if (cancelamentoCache.has(visualizarUrl)) {
            return cancelamentoCache.get(visualizarUrl);
        }
        
        try {
            // Adicionar timeout de 5 segundos para não travar
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch(visualizarUrl, { signal: controller.signal });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const result = { isCancelada: false, numeroNfSubstituta: null, dataEvento: null };
                cancelamentoCache.set(visualizarUrl, result);
                return result;
            }
            
            const html = await response.text();
            
            // Verificação rápida sem parser - procurar texto no HTML
            const temEventoCancelamento = html.includes('Evento de Cancelamento');
            
            if (!temEventoCancelamento) {
                const result = { isCancelada: false, numeroNfSubstituta: null, dataEvento: null };
                cancelamentoCache.set(visualizarUrl, result);
                return result;
            }
            
            // Se tem evento de cancelamento mas não é por substituição, retornar como cancelada sem substituta
            if (!html.includes('Evento de Cancelamento de NFS-e por Substituição')) {
                const result = { isCancelada: true, numeroNfSubstituta: null, dataEvento: null };
                cancelamentoCache.set(visualizarUrl, result);
                return result;
            }
            
            // Usar regex para extrair informações diretamente do HTML (muito mais rápido que DOM parsing)
            let chaveSubstituta = null;
            let dataEvento = null;
            
            // Procurar por chaves (sequências longas de caracteres alfanuméricos)
            const chaveRegex = /<div[^>]*class="[^"]*form-control-static[^"]*texto[^"]*"[^>]*>([A-Za-z0-9]{40,})<\/div>/g;
            const chaveMatch = chaveRegex.exec(html);
            if (chaveMatch && chaveMatch[1]) {
                chaveSubstituta = chaveMatch[1].trim();
            }
            
            // Procurar pela data (formato dd/mm/yyyy)
            const dataRegex = /Data do Evento[\s\S]{0,200}?(\d{2}\/\d{2}\/\d{4})/;
            const dataMatch = dataRegex.exec(html);
            if (dataMatch && dataMatch[1]) {
                dataEvento = dataMatch[1];
            }
            
            // Extrair número da NF da chave (posições 28 a 36 - índices 28 a 37)
            let numeroNfSubstituta = null;
            if (chaveSubstituta && chaveSubstituta.length >= 37) {
                const numeroComZeros = chaveSubstituta.substring(28, 37);
                // Remover zeros à esquerda
                numeroNfSubstituta = parseInt(numeroComZeros, 10).toString();
            }
            
            const result = { isCancelada: true, numeroNfSubstituta, dataEvento };
            cancelamentoCache.set(visualizarUrl, result);
            console.log(`${LOG_PREFIX} Cancelada por substituição: NF ${numeroNfSubstituta} em ${dataEvento}`);
            return result;
            
        } catch (error) {
            // Se der timeout ou erro, considerar como não cancelada e cachear
            if (error.name === 'AbortError') {
                console.warn(`${LOG_PREFIX} Timeout ao verificar cancelamento: ${visualizarUrl}`);
            } else {
                console.error(`${LOG_PREFIX} Erro ao verificar cancelamento:`, error);
            }
            const result = { isCancelada: false, numeroNfSubstituta: null, dataEvento: null };
            cancelamentoCache.set(visualizarUrl, result);
            return result;
        }
    }

    async function fetchPageHtml(pageNumber) {
        console.log(`${LOG_PREFIX} Buscando HTML da página ${pageNumber}...`);
        const pageUrl = new URL(window.location.href);
        pageUrl.searchParams.set('pg', pageNumber);
        const response = await fetch(pageUrl.toString());
        if (!response.ok) throw new Error(`Falha ao buscar página ${pageNumber}`);
        return await response.text();
    }

    function parsePageHtml(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const downloadUrls = [];
        const notes = doc.querySelectorAll('tbody tr');
        notes.forEach(note => {
            const downloadLinks = note.querySelectorAll('.td-opcoes a');
            // Verificar se a nota foi substituída ou cancelada
            const situacaoTd = note.querySelector('.td-situacao');
            let isSubstituida = false;
            let isCancelada = false;
            let visualizarUrl = null;
            
            if (situacaoTd) {
                const img = situacaoTd.querySelector('img[data-original-title], img[title]');
                if (img) {
                    const tooltip = img.getAttribute('data-original-title') || img.getAttribute('title') || '';
                    const imgSrc = img.getAttribute('src') || '';
                    
                    // Verificar substituição
                    if (tooltip.toLowerCase().includes('substituição') || tooltip.toLowerCase().includes('substituida')) {
                        isSubstituida = true;
                    }
                    
                    // Verificar cancelamento: pelo tooltip ou pelo src da imagem
                    if (tooltip.toLowerCase().includes('cancelada') || imgSrc.includes('tb-cancelada.svg')) {
                        isCancelada = true;
                    }
                }
                
                // Verificar cancelamento: td-situacao contendo apenas "-" (sem imagem)
                if (!isCancelada && !isSubstituida) {
                    const tdText = situacaoTd.textContent.trim();
                    if (tdText === '-') {
                        isCancelada = true;
                    }
                }
            }
            
            // Capturar URL de visualização
            const visualizarLink = note.querySelector('a[href*="/Visualizar/"]');
            if (visualizarLink) {
                visualizarUrl = visualizarLink.href;
            }
            
            downloadLinks.forEach(link => {
                if (link.textContent.includes('Download XML')) {
                    downloadUrls.push({
                        url: link.href,
                        filename: getFilenameFromLink(link, doc),
                        isSubstituida: isSubstituida,
                        isCancelada: isCancelada,
                        visualizarUrl: visualizarUrl
                    });
                }
            });
        });
        console.log(`${LOG_PREFIX} Encontrados ${downloadUrls.length} links de download na página.`);
        return downloadUrls;
    }

    function getFilenameFromLink(link, doc) {
        const urlParts = link.href.split('/');
        const noteNumber = urlParts[urlParts.length - 1];
        const noteRow = link.closest('tr');
        const dateElement = noteRow.querySelector('.td-datahora');
        let filename = `NFS-e_${noteNumber}`;
        if (dateElement) {
            const dateText = dateElement.textContent.trim().replace(/\//g, '-').replace(/:/g, '-');
            filename += `_${dateText}`;
        }
        return `${filename}.xml`;
    }

    async function getFilenameFromXml(xmlText, isRecebidas) {
        try {
            const xmlTextCleaned = xmlText.replace(/xmlns="[^"]*"/g, '');
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlTextCleaned, "text/xml");
            
            // Extrair dados do XML
            const nNFSe = getXmlValue(xmlDoc, 'nNFSe');
            const dhEmi = getXmlValue(xmlDoc, 'DPS>infDPS>dhEmi');
            // Formato de data: dd-mm-aaaa (sem hora)
            const dataEmissao = dhEmi ? new Date(dhEmi).toLocaleDateString('pt-BR').replace(/\//g, '-') : '';
            
            let nomeArquivo;
            if (isRecebidas) {
                // Para notas RECEBIDAS: usar dados do PRESTADOR (quem emitiu para você)
                const cnpjPrestador = getXmlValue(xmlDoc, 'DPS>infDPS>prest>CNPJ') || getXmlValue(xmlDoc, 'emit>CNPJ');
                const nomeCompletoEmit = getXmlValue(xmlDoc, 'emit>xNome');
                // Pegar apenas o primeiro nome (antes do primeiro espaço)
                const nomePrestador = nomeCompletoEmit ? nomeCompletoEmit.split(' ')[0] : 'Prestador';
                const cnpjFormatado = cnpjPrestador ? formatCnpj(cnpjPrestador) : '';
                nomeArquivo = `Recebida_${cnpjFormatado}_${nomePrestador}_${nNFSe}_${dataEmissao}.xml`;
            } else {
                // Para notas EMITIDAS: usar dados do TOMADOR (quem recebeu de você)
                const cnpjTomador = getXmlValue(xmlDoc, 'DPS>infDPS>toma>CNPJ');
                const cpfTomador = getXmlValue(xmlDoc, 'DPS>infDPS>toma>CPF');
                const nomeCompletoToma = getXmlValue(xmlDoc, 'DPS>infDPS>toma>xNome');
                // Pegar apenas o primeiro nome (antes do primeiro espaço)
                const nomeTomador = nomeCompletoToma ? nomeCompletoToma.split(' ')[0] : 'Tomador';
                const documentoTomador = cnpjTomador ? formatCnpj(cnpjTomador) : (cpfTomador ? formatCpf(cpfTomador) : '');
                nomeArquivo = `Emitida_${documentoTomador}_${nomeTomador}_${nNFSe}_${dataEmissao}.xml`;
            }
            
            // Limpar caracteres inválidos do nome do arquivo
            nomeArquivo = nomeArquivo.replace(/[/\\?%*:|"<>]/g, '-');
            
            return nomeArquivo;
        } catch (error) {
            console.error(`${LOG_PREFIX} Erro ao extrair nome do arquivo do XML:`, error);
            // Fallback para nome genérico
            return `NFS-e_${Date.now()}.xml`;
        }
    }

    // --- FUNÇÕES DE INTERFACE ---

    function addCheckboxesToTable() {
        const table = document.querySelector('table.table-striped');
        if (!table || table.querySelector('th.checkbox-column')) return;
        
        console.log(`${LOG_PREFIX} Adicionando coluna de seleção...`);
        const headerRow = table.querySelector('thead tr');

        // Injetar estilos globais de UX
        if (!document.getElementById('nfse-ux-styles')) {
            const style = document.createElement('style');
            style.id = 'nfse-ux-styles';
            style.textContent = `
                table.table-striped tbody tr {
                    transition: background-color 0.15s ease;
                    cursor: default;
                }
                table.table-striped tbody tr:hover {
                    background-color: #f0f4ff !important;
                }
                table.table-striped tbody tr.nfse-cancelada {
                    background-color: #fff5f5 !important;
                }
                table.table-striped tbody tr.nfse-cancelada:hover {
                    background-color: #ffe8e8 !important;
                }
                table.table-striped tbody tr.nfse-cancelamento-analise {
                    background-color: #fffde7 !important;
                }
                table.table-striped tbody tr.nfse-cancelamento-analise:hover {
                    background-color: #fff9c4 !important;
                }
                table.table-striped tbody tr.nfse-row-selected {
                    background-color: #eef4ff !important;
                }
                .checkbox-column input[type="checkbox"] {
                    width: 16px;
                    height: 16px;
                    cursor: pointer;
                    accent-color: #1a4dba;
                }
                #selectAllCheckbox-wrapper {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                    cursor: pointer;
                }
                .nfse-cancelada-badge {
                    display: inline-block;
                    font-size: 10px;
                    font-weight: 700;
                    color: #b91c1c;
                    background: #fee2e2;
                    border: 1px solid #fca5a5;
                    border-radius: 4px;
                    padding: 1px 5px;
                    margin-left: 4px;
                    letter-spacing: 0.02em;
                    vertical-align: middle;
                }
                .nfse-analise-badge {
                    display: inline-block;
                    font-size: 10px;
                    font-weight: 700;
                    color: #92400e;
                    background: #fef3c7;
                    border: 1px solid #fcd34d;
                    border-radius: 4px;
                    padding: 1px 5px;
                    margin-left: 4px;
                    letter-spacing: 0.02em;
                    vertical-align: middle;
                }
                .quick-actions-column {
                    white-space: nowrap;
                }
                /* Ocultar coluna Competência quando redundante */
                .nfse-competencia-hidden .td-competencia,
                .nfse-competencia-hidden th.td-competencia {
                    display: none;
                }
                /* Estilizar botões de manifestação no menu suspenso */
                .td-opcoes .btnManifestacao[data-evento="1"] {
                    color: #1a7f3c !important;
                    font-weight: 500;
                }
                .td-opcoes .btnManifestacao[data-evento="2"] {
                    color: #b91c1c !important;
                    font-weight: 500;
                }
                .td-opcoes .btnManifestacao[data-evento="1"]:hover {
                    background-color: #edfaf1 !important;
                }
                .td-opcoes .btnManifestacao[data-evento="2"]:hover {
                    background-color: #fff5f5 !important;
                }
                /* Melhorar visual do menu suspenso */
                .menu-suspenso-tabela .list-group {
                    border-radius: 8px !important;
                    box-shadow: 0 4px 16px rgba(0,0,0,0.12) !important;
                    border: 1px solid #e8eaed !important;
                    overflow: hidden;
                    min-width: 180px;
                }
                .menu-suspenso-tabela .list-group-item {
                    border-left: none !important;
                    border-right: none !important;
                    padding: 9px 14px !important;
                    font-size: 13px !important;
                    transition: background 0.15s !important;
                }
                .menu-suspenso-tabela .list-group-item:first-child {
                    border-top: none !important;
                    border-radius: 8px 8px 0 0 !important;
                }
                .menu-suspenso-tabela .list-group-item:last-child {
                    border-bottom: none !important;
                    border-radius: 0 0 8px 8px !important;
                }
            `;
            document.head.appendChild(style);
        }
        
        // Adicionar coluna de checkbox com tooltip melhorado
        const selectAllTh = document.createElement('th');
        selectAllTh.className = 'checkbox-column';
        selectAllTh.style.cssText = 'width: 44px; text-align: center; vertical-align: middle;';
        selectAllTh.innerHTML = `
            <div id="selectAllCheckbox-wrapper" title="Marcar/Desmarcar todos">
                <input type="checkbox" id="selectAllCheckbox">
                <svg style="width:11px;height:11px;color:#666;flex-shrink:0;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l4-4 4 4m0 6l-4 4-4-4"/>
                </svg>
            </div>
        `;
        headerRow.insertBefore(selectAllTh, headerRow.firstChild);

        // Adicionar coluna de Ações com estilo clean
        const quickActionsTh = document.createElement('th');
        quickActionsTh.className = 'quick-actions-column';
        quickActionsTh.style.cssText = `
            width: 86px;
            text-align: center;
            color: #6b7280;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        `;
        quickActionsTh.textContent = 'Ações';
        const lastTh = headerRow.querySelector('th:last-child');
        headerRow.insertBefore(quickActionsTh, lastTh);

        // Verificar se todas as competências são iguais (esconder coluna se for)
        const bodyRows = table.querySelectorAll('tbody tr');
        const competencias = new Set();
        bodyRows.forEach(row => {
            const comp = row.querySelector('.td-competencia');
            if (comp) competencias.add(comp.textContent.trim());
        });
        if (competencias.size <= 1) {
            table.classList.add('nfse-competencia-hidden');
            // Adicionar info da competência na barra de botões depois
            setTimeout(() => {
                const bar = document.getElementById('nfse-extension-buttons');
                if (bar && competencias.size === 1) {
                    const compInfo = document.createElement('span');
                    compInfo.style.cssText = `
                        font-size: 11px;
                        color: #6b7280;
                        background: #f3f4f6;
                        border: 1px solid #e5e7eb;
                        border-radius: 5px;
                        padding: 3px 9px;
                        font-weight: 500;
                        margin-left: auto;
                    `;
                    compInfo.textContent = `📅 Competência: ${[...competencias][0]}`;
                    bar.appendChild(compInfo);
                }
            }, 300);
        }

        bodyRows.forEach(row => {
            // Detectar se a linha é cancelada (td-situacao com "-" ou sem imagem gerada)
            const situacaoTd = row.querySelector('.td-situacao');
            let isCancelada = false;
            let isCancelamentoAnalise = false;
            if (situacaoTd) {
                const img = situacaoTd.querySelector('img');
                const tdText = situacaoTd.textContent.trim();
                const imgSrc = img ? (img.getAttribute('src') || '') : '';
                if (tdText === '-' || imgSrc.includes('tb-cancelada')) {
                    isCancelada = true;
                } else if (imgSrc.includes('tb-pendente')) {
                    isCancelamentoAnalise = true;
                }
            }

            if (isCancelada) {
                row.classList.add('nfse-cancelada');
                // Adicionar badge visual na coluna de situação
                if (situacaoTd) {
                    const badge = document.createElement('span');
                    badge.className = 'nfse-cancelada-badge';
                    badge.textContent = 'CANCELADA';
                    situacaoTd.appendChild(badge);
                }
            }

            if (isCancelamentoAnalise) {
                row.classList.add('nfse-cancelamento-analise');
                // Adicionar badge visual na coluna de situação
                if (situacaoTd) {
                    const badge = document.createElement('span');
                    badge.className = 'nfse-analise-badge';
                    badge.textContent = 'Cancelamento em análise';
                    situacaoTd.appendChild(badge);
                }
            }

            // Hover row highlight + seleção ao clicar na linha
            row.addEventListener('click', function(e) {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || e.target.closest('a') || e.target.closest('.menu-suspenso-tabela')) return;
                const cb = row.querySelector('.note-checkbox');
                if (cb) {
                    cb.checked = !cb.checked;
                    row.classList.toggle('nfse-row-selected', cb.checked);
                }
            });

            // Adicionar checkbox
            const checkboxTd = document.createElement('td');
            checkboxTd.className = 'checkbox-column';
            checkboxTd.style.cssText = 'text-align: center; vertical-align: middle;';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'note-checkbox';
            checkbox.addEventListener('change', function() {
                row.classList.toggle('nfse-row-selected', checkbox.checked);
            });
            checkboxTd.appendChild(checkbox);
            row.insertBefore(checkboxTd, row.firstChild);

            // Adicionar coluna de Ações
            const quickActionsTd = document.createElement('td');
            quickActionsTd.className = 'quick-actions-column';
            quickActionsTd.style.cssText = 'text-align: center; vertical-align: middle;';
            const lastTd = row.querySelector('td:last-child');
            row.insertBefore(quickActionsTd, lastTd);
        });

        // Paginação: mostrar contagem da página atual
        const paginacaoDesc = document.querySelector('.paginacao .descricao');
        if (paginacaoDesc) {
            const totalText = paginacaoDesc.textContent;
            const totalMatch = totalText.match(/(\d+)/);
            if (totalMatch) {
                const total = totalMatch[1];
                const naPagina = bodyRows.length;
                paginacaoDesc.textContent = `${naPagina} de ${total} registros`;
            }
        }

        // Select-all com feedback visual
        document.getElementById('selectAllCheckbox').addEventListener('change', function(e) {
            document.querySelectorAll('.note-checkbox').forEach(cb => {
                cb.checked = e.target.checked;
                cb.closest('tr').classList.toggle('nfse-row-selected', e.target.checked);
            });
        });
    }

    function addDirectDownloadButtons() {
        console.log(`${LOG_PREFIX} Adicionando botões de download direto...`);
        const table = document.querySelector('table.table-striped');
        if (!table) return;

        // Detectar se é página de notas recebidas ou emitidas
        const pageTitle = document.querySelector('h1, h2, .page-title');
        const isRecebidas = pageTitle && pageTitle.textContent.toLowerCase().includes('recebida');

        const bodyRows = table.querySelectorAll('tbody tr');
        bodyRows.forEach(row => {
            const quickActionsTd = row.querySelector('.quick-actions-column');
            if (!quickActionsTd) return;

            // Verificar se já tem os botões de download
            if (quickActionsTd.querySelector('.direct-download-xml')) return;

            // Buscar os links de download no menu de opções
            const downloadLinks = row.querySelectorAll('.td-opcoes a');
            let xmlUrl = null;
            let pdfUrl = null;

            downloadLinks.forEach(link => {
                if (link.textContent.includes('Download XML')) {
                    xmlUrl = link.href;
                }
                if (link.textContent.includes('Download DANFS-e')) {
                    pdfUrl = link.href;
                }
            });

            // Extrair informações da linha para nomenclatura
            const dataHoraTd = row.querySelector('.td-datahora');
            const textoGrandeTd = row.querySelector('.td-texto-grande');
            
            let nomeEmpresa = '';
            let numeroNFSe = '';
            let dataEmissao = '';

            // Extrair nome da empresa (Emitente para recebidas, Tomador para emitidas)
            if (textoGrandeTd) {
                const textoCompleto = textoGrandeTd.textContent.trim();
                // Pegar o texto após o CNPJ/CPF e hífen
                const partes = textoCompleto.split('-');
                if (partes.length > 1) {
                    nomeEmpresa = partes[1].trim().replace(/[/\\?%*:|"<>]/g, '-');
                }
            }

            // Extrair data/hora
            if (dataHoraTd) {
                const dataTexto = dataHoraTd.textContent.trim();
                // Formato: 03/02/26 12:18 -> 03-02-26
                dataEmissao = dataTexto.split(' ')[0].replace(/\//g, '-');
            }

            // Extrair número da NFSe da URL
            if (xmlUrl) {
                const urlParts = xmlUrl.split('/');
                numeroNFSe = urlParts[urlParts.length - 1];
            }

            // Container para os ícones
            const iconsContainer = document.createElement('div');
            iconsContainer.style.cssText = `
                display: flex;
                gap: 8px;
                justify-content: center;
                align-items: center;
            `;

            // Botão XML (Azul) - REQUER LICENÇA
            if (xmlUrl) {
                const xmlBtn = document.createElement('a');
                xmlBtn.href = '#';
                xmlBtn.className = 'direct-download-xml';
                xmlBtn.title = 'Download XML (Requer Licença)';
                xmlBtn.style.cssText = `
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 34px;
                    height: 26px;
                    background: #eef4ff;
                    border: 1.5px solid #bdd0fa;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.2s;
                    text-decoration: none;
                    color: #1a4dba;
                    font-weight: 700;
                    font-size: 10px;
                    font-family: Arial, sans-serif;
                    letter-spacing: 0.03em;
                `;
                
                xmlBtn.innerHTML = `XML`;
                
                // Efeitos hover
                xmlBtn.addEventListener('mouseenter', function() {
                    this.style.filter = 'brightness(0.93)';
                    this.style.transform = 'translateY(-1px)';
                });
                xmlBtn.addEventListener('mouseleave', function() {
                    this.style.filter = 'none';
                    this.style.transform = 'scale(1)';
                    this.style.boxShadow = 'none';
                });

                // Download com verificação de licença
                xmlBtn.addEventListener('click', async function(e) {
                    e.preventDefault();
                    
                    // Verificar licença
                    const hasLicense = await checkLicenseAndAlert();
                    if (!hasLicense) {
                        return; // Bloqueia se não tiver licença
                    }

                    try {
                        // Baixar XML para extrair informações
                        const response = await fetch(xmlUrl);
                        if (!response.ok) throw new Error('Falha ao baixar XML');
                        
                        const xmlText = await response.text();
                        const blob = new Blob([xmlText], { type: 'application/xml' });
                        
                        // Parse do XML para extrair dados
                        const xmlTextCleaned = xmlText.replace(/xmlns="[^"]*"/g, '');
                        const parser = new DOMParser();
                        const xmlDoc = parser.parseFromString(xmlTextCleaned, "text/xml");
                        
                        // Extrair dados do XML
                        const nNFSe = getXmlValue(xmlDoc, 'nNFSe') || numeroNFSe;
                        const dhEmi = getXmlValue(xmlDoc, 'DPS>infDPS>dhEmi');
                        // Formato de data: dd-mm-aaaa (sem hora)
                        const dataEmissao = dhEmi ? new Date(dhEmi).toLocaleDateString('pt-BR').replace(/\//g, '-') : '';
                        
                        let nomeArquivo;
                        if (isRecebidas) {
                            // Para notas RECEBIDAS: usar dados do PRESTADOR (quem emitiu para você)
                            const cnpjPrestador = getXmlValue(xmlDoc, 'DPS>infDPS>prest>CNPJ') || getXmlValue(xmlDoc, 'emit>CNPJ');
                            const nomeCompletoEmit = getXmlValue(xmlDoc, 'emit>xNome');
                            // Pegar apenas o primeiro nome (antes do primeiro espaço)
                            const nomePrestador = nomeCompletoEmit ? nomeCompletoEmit.split(' ')[0] : 'Prestador';
                            const cnpjFormatado = cnpjPrestador ? formatCnpj(cnpjPrestador) : '';
                            nomeArquivo = `Recebida_${cnpjFormatado}_${nomePrestador}_${nNFSe}_${dataEmissao}.xml`;
                        } else {
                            // Para notas EMITIDAS: usar dados do TOMADOR (quem recebeu de você)
                            const cnpjTomador = getXmlValue(xmlDoc, 'DPS>infDPS>toma>CNPJ');
                            const cpfTomador = getXmlValue(xmlDoc, 'DPS>infDPS>toma>CPF');
                            const nomeCompletoToma = getXmlValue(xmlDoc, 'DPS>infDPS>toma>xNome');
                            // Pegar apenas o primeiro nome (antes do primeiro espaço)
                            const nomeTomador = nomeCompletoToma ? nomeCompletoToma.split(' ')[0] : 'Tomador';
                            const documentoTomador = cnpjTomador ? formatCnpj(cnpjTomador) : (cpfTomador ? formatCpf(cpfTomador) : '');
                            nomeArquivo = `Emitida_${documentoTomador}_${nomeTomador}_${nNFSe}_${dataEmissao}.xml`;
                        }
                        
                        // Limpar caracteres inválidos do nome do arquivo
                        nomeArquivo = nomeArquivo.replace(/[/\\?%*:|"<>]/g, '-');
                        
                        // Realizar download
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = nomeArquivo;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        
                    } catch (error) {
                        console.error(`${LOG_PREFIX} Erro ao baixar XML:`, error);
                        // Fallback para download direto
                        window.location.href = xmlUrl;
                    }
                });

                iconsContainer.appendChild(xmlBtn);
            }

            // Botão PDF (Vermelho) - LIVRE
            if (pdfUrl) {
                const pdfBtn = document.createElement('a');
                pdfBtn.href = '#';
                pdfBtn.className = 'direct-download-pdf';
                pdfBtn.title = 'Download DANFS-e (PDF)';
                pdfBtn.style.cssText = `
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 34px;
                    height: 26px;
                    background: #fff1f0;
                    border: 1.5px solid #ffc4c0;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.2s;
                    text-decoration: none;
                    color: #b91c1c;
                    font-weight: 700;
                    font-size: 10px;
                    font-family: Arial, sans-serif;
                    letter-spacing: 0.03em;
                `;
                
                pdfBtn.innerHTML = `PDF`;
                
                // Efeitos hover
                pdfBtn.addEventListener('mouseenter', function() {
                    this.style.filter = 'brightness(0.93)';
                    this.style.transform = 'translateY(-1px)';
                });
                pdfBtn.addEventListener('mouseleave', function() {
                    this.style.filter = 'none';
                    this.style.transform = 'scale(1)';
                    this.style.boxShadow = 'none';
                });

                // Download SEM verificação de licença
                pdfBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const tipoNota = isRecebidas ? 'Recebida' : 'Emitida';
                    const nomeArquivo = `${nomeEmpresa}_${numeroNFSe}_${dataEmissao}.pdf`;
                    
                    fetch(pdfUrl)
                        .then(response => response.blob())
                        .then(blob => {
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = nomeArquivo;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                        })
                        .catch(error => {
                            console.error(`${LOG_PREFIX} Erro ao baixar PDF:`, error);
                            // Fallback para download direto
                            window.location.href = pdfUrl;
                        });
                });

                iconsContainer.appendChild(pdfBtn);
            }

            quickActionsTd.appendChild(iconsContainer);
        });
    }

    function addButton() {
        if (document.getElementById('downloadAllZipBtn')) {
            console.log(`${LOG_PREFIX} Botões já existem, pulando adição.`);
            return;
        }

        // Procurar pelo elemento #searchbar (que é o navbar-collapse)
        const searchbar = document.querySelector('#searchbar');
        
        if (!searchbar) {
            console.error(`${LOG_PREFIX} Elemento #searchbar não encontrado.`);
            return;
        }

        console.log(`${LOG_PREFIX} Elemento #searchbar encontrado.`);

        // Criar container principal com design moderno
        const buttonContainer = document.createElement('div');
        buttonContainer.id = 'nfse-extension-buttons';
        buttonContainer.className = 'container-fluid';
        buttonContainer.style.cssText = `
            display: flex !important;
            gap: 12px;
            align-items: center;
            margin-top: 20px;
            margin-bottom: 20px;
            padding: 16px 20px;
            background: #ffffff;
            border-radius: 10px;
            border: 1px solid #e8eaed;
            box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08);
            flex-wrap: wrap;
            width: 100%;
            box-sizing: border-box;
        `;

        // Adicionar título/logo da extensão
        const headerDiv = document.createElement('div');
        headerDiv.style.cssText = `
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 0 0 auto;
            color: #3c4257;
            font-weight: 700;
            font-size: 14px;
            margin-right: 16px;
            padding-right: 16px;
            border-right: 1px solid #e8eaed;
            letter-spacing: 0.01em;
        `;
        headerDiv.innerHTML = `
            <span style="font-size: 20px;">📄</span>
            <span>NFS-e Download Helper</span>
        `;

        // Container para os botões
        const buttonsWrapper = document.createElement('div');
        buttonsWrapper.style.cssText = `
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            flex: 1;
            align-items: center;
        `;

        // Estilo base para todos os botões
        const baseButtonStyle = `
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 9px 18px !important;
            border: 1.5px solid transparent !important;
            border-radius: 7px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            text-decoration: none !important;
            white-space: nowrap !important;
            box-shadow: none !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.01em !important;
        `;

        const buttonHoverEffect = `
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
        `;

        // Botão 1: Baixar Tudo (Verde)
        const downloadAllBtn = document.createElement('a');
        downloadAllBtn.id = 'downloadAllZipBtn';
        downloadAllBtn.href = '#';
        downloadAllBtn.title = 'Baixar todas as notas da página atual em um arquivo ZIP';
        downloadAllBtn.style.cssText = baseButtonStyle + `
            background: #edfaf1 !important;
            color: #1a7f3c !important;
            border-color: #b7e5c7 !important;
        `;
        downloadAllBtn.innerHTML = `
            <svg style="width: 20px; height: 20px; margin-right: 8px;" fill="currentColor" viewBox="0 0 20 20">
                <path d="M13 8V2H7v6H2l8 8 8-8h-5zM0 18h20v2H0v-2z"/>
            </svg>
            <span>Baixar Tudo</span>
        `;

        // Botão 2: Baixar Selecionados (Laranja)
        const downloadSelectedBtn = document.createElement('a');
        downloadSelectedBtn.id = 'downloadSelectedZipBtn';
        downloadSelectedBtn.href = '#';
        downloadSelectedBtn.title = 'Baixar apenas as notas selecionadas (use os checkboxes)';
        downloadSelectedBtn.style.cssText = baseButtonStyle + `
            background: #fff8ed !important;
            color: #92540b !important;
            border-color: #fed9a0 !important;
        `;
        downloadSelectedBtn.innerHTML = `
            <svg style="width: 20px; height: 20px; margin-right: 8px;" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/>
                <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd"/>
            </svg>
            <span>Baixar Selecionados</span>
        `;

        // Botão 3: Gerar Excel (Azul)
        const generateExcelBtn = document.createElement('a');
        generateExcelBtn.id = 'generateExcelBtn';
        generateExcelBtn.href = '#';
        generateExcelBtn.title = 'Gerar relatório Excel (XLSX) com todas as notas e impostos retidos';
        generateExcelBtn.style.cssText = baseButtonStyle + `
            background: #eef4ff !important;
            color: #1a4dba !important;
            border-color: #bdd0fa !important;
        `;
        generateExcelBtn.innerHTML = `
            <svg style="width: 20px; height: 20px; margin-right: 8px;" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z" clip-rule="evenodd"/>
            </svg>
            <span>Gerar Relatório Excel</span>
        `;

        // Badge de status (contador de selecionados)
        const statusBadge = document.createElement('div');
        statusBadge.id = 'nfse-selection-badge';
        statusBadge.style.cssText = `
            display: none;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            background: #f1f3f5;
            border-radius: 20px;
            color: #3c4257;
            font-weight: 600;
            font-size: 12px;
            border: 1px solid #dee2e6;
            margin-left: auto;
        `;
        statusBadge.innerHTML = `
            <svg style="width: 16px; height: 16px;" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
            <span id="nfse-selection-count">0 selecionada(s)</span>
        `;

        // Adicionar efeitos hover nos botões
        function addHoverEffects(btn) {
            btn.addEventListener('mouseenter', function() {
                this.style.filter = 'brightness(0.94)';
                this.style.transform = 'translateY(-1px)';
            });
            btn.addEventListener('mouseleave', function() {
                this.style.filter = 'none';
                this.style.transform = 'translateY(0)';
            });
            btn.addEventListener('mousedown', function() {
                this.style.transform = 'translateY(0)';
            });
            btn.addEventListener('mouseup', function() {
                this.style.transform = 'translateY(-1px)';
            });
        }

        addHoverEffects(downloadAllBtn);
        addHoverEffects(downloadSelectedBtn);
        addHoverEffects(generateExcelBtn);

        // Event listeners
        downloadAllBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            if (await checkLicenseAndAlert()) {
                downloadAllAndZip();
            }
        });

        downloadSelectedBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            if (await checkLicenseAndAlert()) {
                downloadSelectedAndZip();
            }
        });

        generateExcelBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            if (await checkLicenseAndAlert()) {
                generateExcelReport();
            }
        });

        // Montar a estrutura
        buttonsWrapper.appendChild(downloadAllBtn);
        buttonsWrapper.appendChild(downloadSelectedBtn);
        buttonsWrapper.appendChild(generateExcelBtn);

        buttonContainer.appendChild(headerDiv);
        buttonContainer.appendChild(buttonsWrapper);
        buttonContainer.appendChild(statusBadge);

        // Inserir o container de botões DEPOIS do #pnlComandos (fora do navbar)
        const pnlComandos = document.querySelector('#pnlComandos');
        if (pnlComandos) {
            pnlComandos.parentNode.insertBefore(buttonContainer, pnlComandos.nextSibling);
        } else {
            searchbar.parentNode.insertBefore(buttonContainer, searchbar.nextSibling);
        }
        
        console.log(`${LOG_PREFIX} Botões com UI melhorada adicionados com sucesso!`);

        // Atualizar contador de selecionados
        function updateSelectionBadge() {
            const checkboxes = document.querySelectorAll('input[type="checkbox"].nfse-checkbox:checked');
            const count = checkboxes.length;
            const badge = document.getElementById('nfse-selection-badge');
            const countSpan = document.getElementById('nfse-selection-count');
            
            if (badge && countSpan) {
                if (count > 0) {
                    badge.style.display = 'flex';
                    countSpan.textContent = `${count} selecionada${count > 1 ? 's' : ''}`;
                } else {
                    badge.style.display = 'none';
                }
            }
        }

        // Observer para mudanças nos checkboxes
        document.addEventListener('change', function(e) {
            if (e.target.classList.contains('nfse-checkbox')) {
                updateSelectionBadge();
            }
        });

        // Atualizar inicialmente
        setTimeout(updateSelectionBadge, 500);
        
        // Verificação de visibilidade
        setTimeout(() => {
            console.log(`${LOG_PREFIX} === VERIFICAÇÃO DE VISIBILIDADE ===`);
            console.log(`${LOG_PREFIX} Container ID:`, buttonContainer.id);
            console.log(`${LOG_PREFIX} Container display:`, window.getComputedStyle(buttonContainer).display);
            console.log(`${LOG_PREFIX} Container width:`, buttonContainer.offsetWidth);
            
            const allBtn = document.getElementById('downloadAllZipBtn');
            const selBtn = document.getElementById('downloadSelectedZipBtn');
            const excelBtn = document.getElementById('generateExcelBtn');
            
            console.log(`${LOG_PREFIX} Botão "Baixar Tudo" visível:`, allBtn && allBtn.offsetWidth > 0);
            console.log(`${LOG_PREFIX} Botão "Baixar Selecionados" visível:`, selBtn && selBtn.offsetWidth > 0);
            console.log(`${LOG_PREFIX} Botão "Gerar Excel" visível:`, excelBtn && excelBtn.offsetWidth > 0);
        }, 500);
    }

    // --- FUNÇÕES PRINCIPAIS DE AÇÃO ---

    async function downloadSelectedAndZip() {
        const downloadSelectedBtn = document.getElementById('downloadSelectedZipBtn');
        const originalHtml = downloadSelectedBtn.innerHTML;
        
        function updateButtonText(text) {
            downloadSelectedBtn.innerHTML = `
                <img src="/EmissorNacional/img/btn-download.svg" 
                     style="height: 21px; margin-right: 8px; vertical-align: middle;" />
                <span>${text}</span>
            `;
        }

        const checkboxes = document.querySelectorAll('.note-checkbox:checked');
        if (checkboxes.length === 0) {
            alert('Nenhuma nota selecionada.');
            return;
        }

        try {
            downloadSelectedBtn.disabled = true;
            updateButtonText('Coletando notas selecionadas...');

            // Detectar se é página de notas recebidas ou emitidas
            const pageTitle = document.querySelector('h1, h2, .page-title');
            const isRecebidas = pageTitle && pageTitle.textContent.toLowerCase().includes('recebida');

            const downloadUrls = [];
            checkboxes.forEach(checkbox => {
                const row = checkbox.closest('tr');
                const downloadLinks = row.querySelectorAll('.td-opcoes a');
                downloadLinks.forEach(link => {
                    if (link.textContent.includes('Download XML')) {
                        downloadUrls.push({
                            url: link.href,
                            filename: getFilenameFromLink(link, document)
                        });
                    }
                });
            });

            console.log(`${LOG_PREFIX} ${downloadUrls.length} notas selecionadas para download.`);

            if (typeof JSZip === 'undefined') {
                alert('Biblioteca JSZip não carregada. Verifique a extensão.');
                return;
            }

            const zip = new JSZip();
            let downloadedCount = 0;

            for (const item of downloadUrls) {
                downloadedCount++;
                updateButtonText(`Baixando ${downloadedCount} de ${downloadUrls.length}...`);
                
                try {
                    const response = await fetch(item.url);
                    if (!response.ok) throw new Error(`Falha ao baixar ${item.filename}`);
                    const xmlText = await response.text();
                    
                    // Gerar nome de arquivo descritivo
                    const filename = await getFilenameFromXml(xmlText, isRecebidas);
                    const blob = new Blob([xmlText], { type: 'application/xml' });
                    
                    // Organizar por pasta de competência
                    const folder = getCompetenciaFolder(xmlText);
                    zip.file(`${folder}/${filename}`, blob);
                } catch (error) {
                    console.error(`${LOG_PREFIX} Erro ao baixar ${item.filename}:`, error);
                }
            }

            updateButtonText('Compactando arquivos...');
            const zipBlob = await zip.generateAsync({ type: 'blob' });
            
            const url = URL.createObjectURL(zipBlob);
            const downloadLink = document.createElement('a');
            downloadLink.href = url;
            const today = new Date();
            const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
            const timeStr = today.toTimeString().slice(0, 5).replace(/:/g, '');
            downloadLink.download = `NFS-e_Selecionadas_${dateStr}_${timeStr}.zip`;
            
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            setTimeout(() => URL.revokeObjectURL(url), 1000);

            updateButtonText('Download concluído!');
            setTimeout(() => {
                downloadSelectedBtn.innerHTML = originalHtml;
                downloadSelectedBtn.disabled = false;
            }, 3000);

        } catch (error) {
            console.error(`${LOG_PREFIX} Erro no download selecionado:`, error);
            alert('Ocorreu um erro durante o download: ' + error.message);
            downloadSelectedBtn.innerHTML = originalHtml;
            downloadSelectedBtn.disabled = false;
        }
    }

    async function downloadAllAndZip() {
        const downloadAllBtn = document.getElementById('downloadAllZipBtn');
        const originalHtml = downloadAllBtn.innerHTML;
        
        function updateButtonText(text) {
            downloadAllBtn.innerHTML = `
                <img src="/EmissorNacional/img/btn-download.svg" 
                     style="height: 21px; margin-right: 8px; vertical-align: middle;" />
                <span>${text}</span>
            `;
        }

        try {
            downloadAllBtn.disabled = true;
            updateButtonText('Analisando páginas...');

            // Detectar se é página de notas recebidas ou emitidas
            const pageTitle = document.querySelector('h1, h2, .page-title');
            const isRecebidas = pageTitle && pageTitle.textContent.toLowerCase().includes('recebida');

            let totalPages = 1;
            const descricaoDiv = document.querySelector('.paginacao .descricao');
            if (descricaoDiv) {
                const totalRecordsText = descricaoDiv.textContent.match(/de\s+(\d+)\s+registros/);
                if (totalRecordsText && totalRecordsText[1]) {
                    const totalRecords = parseInt(totalRecordsText[1]);
                    const recordsPerPage = document.querySelectorAll('tbody tr').length;
                    if (recordsPerPage > 0) totalPages = Math.ceil(totalRecords / recordsPerPage);
                }
            }

            console.log(`${LOG_PREFIX} Total de páginas: ${totalPages}`);

            const allDownloadUrls = [];
            for (let page = 1; page <= totalPages; page++) {
                updateButtonText(`Coletando links da página ${page} de ${totalPages}...`);
                const pageHtml = await fetchPageHtml(page);
                const pageUrls = parsePageHtml(pageHtml);
                allDownloadUrls.push(...pageUrls);
            }

            console.log(`${LOG_PREFIX} Total de notas para download: ${allDownloadUrls.length}`);

            if (typeof JSZip === 'undefined') {
                alert('Biblioteca JSZip não carregada. Verifique a extensão.');
                return;
            }

            const zip = new JSZip();
            let downloadedCount = 0;

            for (const item of allDownloadUrls) {
                downloadedCount++;
                updateButtonText(`Baixando ${downloadedCount} de ${allDownloadUrls.length}...`);
                
                try {
                    const response = await fetch(item.url);
                    if (!response.ok) throw new Error(`Falha ao baixar ${item.filename}`);
                    const xmlText = await response.text();
                    
                    // Gerar nome de arquivo descritivo
                    const filename = await getFilenameFromXml(xmlText, isRecebidas);
                    const blob = new Blob([xmlText], { type: 'application/xml' });
                    
                    // Organizar por pasta de competência
                    const folder = getCompetenciaFolder(xmlText);
                    zip.file(`${folder}/${filename}`, blob);
                } catch (error) {
                    console.error(`${LOG_PREFIX} Erro ao baixar ${item.filename}:`, error);
                }
            }

            updateButtonText('Compactando arquivos...');
            const zipBlob = await zip.generateAsync({ type: 'blob' });
            
            const url = URL.createObjectURL(zipBlob);
            const downloadLink = document.createElement('a');
            downloadLink.href = url;
            const today = new Date();
            const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
            const timeStr = today.toTimeString().slice(0, 5).replace(/:/g, '');
            downloadLink.download = `NFS-e_Todas_${dateStr}_${timeStr}.zip`;
            
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            setTimeout(() => URL.revokeObjectURL(url), 1000);

            updateButtonText('Download concluído!');
            setTimeout(() => {
                downloadAllBtn.innerHTML = originalHtml;
                downloadAllBtn.disabled = false;
            }, 3000);

        } catch (error) {
            console.error(`${LOG_PREFIX} Erro no download:`, error);
            alert('Ocorreu um erro durante o download: ' + error.message);
            downloadAllBtn.innerHTML = originalHtml;
            downloadAllBtn.disabled = false;
        }
    }

    // --- FUNÇÕES AUXILIARES PARA PROCESSAMENTO DE XML ---

    function getCompetenciaFolder(xmlText) {
        try {
            const xmlTextCleaned = xmlText.replace(/xmlns="[^"]*"/g, '');
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlTextCleaned, 'text/xml');
            const dCompet = getXmlValue(xmlDoc, 'DPS>infDPS>dCompet');
            if (dCompet) {
                // dCompet formato: AAAA-MM-DD → pasta: Competencia MM-AAAA
                const parts = dCompet.split('-');
                if (parts.length >= 2) {
                    return `Competencia ${parts[1]}-${parts[0]}`;
                }
            }
        } catch (e) {
            console.warn(`${LOG_PREFIX} Não foi possível extrair dCompet:`, e);
        }
        return 'Competencia Desconhecida';
    }

    function getXmlValue(xmlDoc, path) {
        const parts = path.split('>');
        let current = xmlDoc.documentElement;
        for (const part of parts) {
            if (!current) return '';
            const found = current.querySelector(part);
            if (!found) return '';
            current = found;
        }
        return current ? current.textContent.trim() : '';
    }

    function formatCnpj(cnpj) {
        if (!cnpj || cnpj.length !== 14) return cnpj;
        return cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
    }

    function formatCpf(cpf) {
        if (!cpf || cpf.length !== 11) return cpf;
        return cpf.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
    }

    function getTomadorDocument(xmlDoc) {
        // Primeiro tenta buscar CNPJ
        const cnpjNode = xmlDoc.querySelector('DPS>infDPS>toma>CNPJ');
        if (cnpjNode && cnpjNode.textContent.trim()) {
            return formatCnpj(cnpjNode.textContent.trim());
        }
        
        // Se não encontrar CNPJ, tenta CPF
        const cpfNode = xmlDoc.querySelector('DPS>infDPS>toma>CPF');
        if (cpfNode && cpfNode.textContent.trim()) {
            return formatCpf(cpfNode.textContent.trim());
        }
        
        return '';
    }

    function getEmitenteDocument(xmlDoc) {
        // Primeiro tenta buscar CNPJ
        const cnpjNode = xmlDoc.querySelector('emit>CNPJ');
        if (cnpjNode && cnpjNode.textContent.trim()) {
            return formatCnpj(cnpjNode.textContent.trim());
        }
        
        // Se não encontrar CNPJ, tenta CPF
        const cpfNode = xmlDoc.querySelector('emit>CPF');
        if (cpfNode && cpfNode.textContent.trim()) {
            return formatCpf(cpfNode.textContent.trim());
        }
        
        return '';
    }

    function getChaveCompletaFromXml(xmlDoc) {
        try {
            const infNFSe = xmlDoc.querySelector('infNFSe');
            if (infNFSe) {
                const idAttr = infNFSe.getAttribute('Id');
                if (idAttr && idAttr.startsWith('NFS')) {
                    return idAttr.substring(3); // Remove 'NFS' do início
                }
            }
        } catch (e) {
            // Ignorar erros
        }
        return '';
    }

    function formatCurrencyPtBr(value) {
        if (!value || value === '') return '0,00';
        
        // Tentar converter para número
        let numValue;
        
        if (typeof value === 'number') {
            numValue = value;
        } else {
            // Se já estiver no formato brasileiro (com vírgula como decimal), converter
            if (value.includes(',') && !value.includes('.')) {
                // Formato: "12754,00"
                numValue = parseFloat(value.replace(',', '.'));
            } else if (value.includes('.') && value.includes(',')) {
                // Formato: "12.754,00" - remover pontos de milhar
                const withoutThousandSeparators = value.replace(/\./g, '');
                numValue = parseFloat(withoutThousandSeparators.replace(',', '.'));
            } else {
                // Formato simples: "12754.00" ou "12754"
                numValue = parseFloat(value.replace(',', '.'));
            }
        }
        
        if (isNaN(numValue)) return '0,00';
        
        // Formatar no padrão brasileiro com separadores de milhar
        return numValue.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
    
    function parseToNumber(value) {
        if (!value || value === '') return 0;
        
        if (typeof value === 'number') {
            return value;
        }
        
        // Converter string para número
        let cleanedValue = value.toString();
        
        // Remover separadores de milhar (pontos)
        cleanedValue = cleanedValue.replace(/\./g, '');
        
        // Substituir vírgula decimal por ponto
        cleanedValue = cleanedValue.replace(',', '.');
        
        const numValue = parseFloat(cleanedValue);
        return isNaN(numValue) ? 0 : numValue;
    }

    // --- FUNÇÃO PARA GERAR RELATÓRIO EXCEL ---
    async function generateExcelReport() {
        const generateExcelBtn = document.getElementById('generateExcelBtn');
        const originalHtml = generateExcelBtn.innerHTML;
        const originalText = 'Gerar Relatório Excel';
        
        function updateButtonText(text) {
            generateExcelBtn.innerHTML = `
                <img src="/EmissorNacional/img/btn-download.svg" 
                     style="height: 21px; margin-right: 8px; vertical-align: middle;" />
                <span style="display: inline-block !important; 
                             visibility: visible !important; 
                             opacity: 1 !important;">
                    ${text}
                </span>
            `;
        }
        
        function getCompanyInfo() {
            try {
                // Seletor CSS específico para o dropdown
                const dropdownHeader = document.querySelector('#navbar > ul > li.dropdown.perfil > ul > li.dropdown-header');
                let companyName = '';
                let companyCNPJ = '';
                
                if (dropdownHeader) {
                    // Clonar o elemento para manipular sem afetar o DOM
                    const clone = dropdownHeader.cloneNode(true);
                    
                    // Pegar o texto antes do primeiro <br>
                    const fullText = clone.innerHTML;
                    
                    // Extrair nome da empresa (primeira linha antes do <br>)
                    const nameMatch = fullText.match(/^([^<]+)</);
                    if (nameMatch) {
                        companyName = nameMatch[1].trim();
                    }
                    
                    // Extrair CNPJ do span com class "cnpj"
                    const cnpjSpan = dropdownHeader.querySelector('span.cnpj');
                    if (cnpjSpan) {
                        companyCNPJ = cnpjSpan.textContent.trim();
                    }
                    
                    console.log(`${LOG_PREFIX} Empresa extraída do dropdown: ${companyName} - CNPJ: ${companyCNPJ}`);
                }
                
                return { companyName, companyCNPJ };
            } catch (error) {
                console.error(`${LOG_PREFIX} Erro ao obter informações da empresa:`, error);
                return { companyName: '', companyCNPJ: '' };
            }
        }

        try {
            generateExcelBtn.disabled = true;
            updateButtonText('Analisando páginas...');
            
            // Obter informações da empresa
            const companyInfo = getCompanyInfo();
            
            // Determinar o tipo de relatório baseado na URL
            const currentUrl = window.location.href;
            let reportType = '';
            let reportPrefix = '';
            
            if (currentUrl.includes('/Notas/Emitidas')) {
                reportType = 'Emitidas';
                reportPrefix = 'Emitidas';
            } else if (currentUrl.includes('/Notas/Recebidas')) {
                reportType = 'Recebidas';
                reportPrefix = 'Recebidas';
            } else {
                reportType = 'Notas';
                reportPrefix = 'Relatorio';
            }

            // Detectar se é página de notas recebidas
            const isRecebidas = reportType === 'Recebidas';

            console.log(`${LOG_PREFIX} Tipo de relatório: ${reportType}`);
            console.log(`${LOG_PREFIX} Empresa: ${companyInfo.companyName} - CNPJ: ${companyInfo.companyCNPJ}`);
            
            // Verificar se ExcelJS está disponível
            if (typeof ExcelJS === 'undefined') {
                alert('Biblioteca ExcelJS não carregada. Verifique se o arquivo exceljs.min.js está na pasta da extensão.');
                generateExcelBtn.disabled = false;
                generateExcelBtn.innerHTML = originalHtml;
                return;
            }
            
            // Criar nova pasta de trabalho Excel
            const workbook = new ExcelJS.Workbook();
            workbook.creator = 'NFSe Extension';
            workbook.created = new Date();
            
            // Adicionar planilha
            const worksheet = workbook.addWorksheet('NFS-e');
            
            // ===== ADICIONAR CABEÇALHO COM DADOS DA EMPRESA =====
            // Linha 1: Nome da empresa
            const companyNameRow = worksheet.addRow([companyInfo.companyName || 'Empresa não identificada']);
            companyNameRow.font = { bold: true, size: 14 };
            companyNameRow.alignment = { horizontal: 'left' };
            worksheet.mergeCells(1, 1, 1, 24);
            
            // Linha 2: CNPJ
            const cnpjRow = worksheet.addRow([`CNPJ: ${companyInfo.companyCNPJ || 'Não identificado'}`]);
            cnpjRow.font = { bold: true, size: 12 };
            cnpjRow.alignment = { horizontal: 'left' };
            worksheet.mergeCells(2, 1, 2, 24);
            
            // Linha 3: Tipo de relatório
            const reportTypeRow = worksheet.addRow([`Relatório de Notas ${reportType}`]);
            reportTypeRow.font = { bold: true, size: 12, color: { argb: 'FF0070C0' } };
            reportTypeRow.alignment = { horizontal: 'left' };
            worksheet.mergeCells(3, 1, 3, 24);
            
            // Linha 4: Data de geração
            const today2 = new Date();
            const dateStr2 = today2.toLocaleDateString('pt-BR');
            const timeStr2 = today2.toLocaleTimeString('pt-BR');
            const generationRow = worksheet.addRow([`Gerado em: ${dateStr2} às ${timeStr2}`]);
            generationRow.font = { size: 10, italic: true };
            generationRow.alignment = { horizontal: 'left' };
            worksheet.mergeCells(4, 1, 4, 24);
            
            // Linha 5: Espaço em branco
            worksheet.addRow([]);
            // ===== FIM DO CABEÇALHO =====
            
            // Definir cabeçalhos - ATUALIZADO PARA CNPJ/CPF
            const headers = [
                'Nº NFSe', 'Local Prest', 'Emissão', 'CNPJ/CPF Emitente', 'Razao Emitente',
                'CNPJ/CPF Tomador', 'Razao Tomador', 'NBS', 'Desc. NBS', 'Cod. Tributacao',
                'Descr. Tributacao', 'Descr. Servico', 'Vl. Servico', 'ISS',
                'ISS Valor', 'ISS Ret.', 'Pis Ret.', 'Cofins Ret.', 'IR Ret.', 'CSLL Ret.', 
                'INSS Retido', 'Tipo Ret. Pis/Cofins', 'Vl. Liquido', 'Observação'
            ];
            
            // Adicionar linha de cabeçalho com estilo
            const headerRow = worksheet.addRow(headers);
            headerRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
            headerRow.fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FF0070C0' }
            };
            headerRow.alignment = { vertical: 'middle', horizontal: 'left' };
            
            // Ajustar largura das colunas
            worksheet.columns = [
                { width: 15 }, // Nº NFSe
                { width: 20 }, // Local Prest
                { width: 12 }, // Emissão
                { width: 18 }, // CNPJ/CPF Emitente
                { width: 30 }, // Razao Emitente
                { width: 18 }, // CNPJ/CPF Tomador
                { width: 30 }, // Razao Tomador
                { width: 10 }, // NBS
                { width: 25 }, // Desc. NBS
                { width: 15 }, // Cod. Tributacao
                { width: 25 }, // Descr. Tributacao
                { width: 40 }, // Descr. Servico
                { width: 15 }, // Vl. Servico
                { width: 10 }, // ISS (Status)
                { width: 12 }, // ISS Valor
                { width: 12 }, // ISS Ret.
                { width: 12 }, // Pis Ret.
                { width: 15 }, // Cofins Ret.
                { width: 12 }, // IR Ret.
                { width: 12 }, // CSLL Ret.
                { width: 12 }, // INSS Retido
                { width: 20 }, // Tipo Ret. Pis/Cofins
                { width: 15 }, // Vl. Liquido
                { width: 30 }  // Observação
            ];

            let totalPages = 1;
            const descricaoDiv = document.querySelector('.paginacao .descricao');
            if (descricaoDiv) {
                const totalRecordsText = descricaoDiv.textContent.match(/de\s+(\d+)\s+registros/);
                if (totalRecordsText && totalRecordsText[1]) {
                    const totalRecords = parseInt(totalRecordsText[1]);
                    const recordsPerPage = document.querySelectorAll('tbody tr').length;
                    if (recordsPerPage > 0) totalPages = Math.ceil(totalRecords / recordsPerPage);
                }
            }
            console.log(`${LOG_PREFIX} Total de páginas para o Excel: ${totalPages}`);

            let processedCount = 0;
            const allDownloadUrls = [];
            for (let page = 1; page <= totalPages; page++) {
                updateButtonText(`Coletando links da página ${page} de ${totalPages}...`);
                const pageHtml = await fetchPageHtml(page);
                const pageUrls = parsePageHtml(pageHtml);
                allDownloadUrls.push(...pageUrls);
            }

            console.log(`${LOG_PREFIX} Total de notas para processar no Excel: ${allDownloadUrls.length}`);

            // --- VERIFICAÇÃO INTELIGENTE DE CANCELAMENTO PARA NOTAS RECEBIDAS ---
            let verificarCanceladas = false;
            
            if (isRecebidas) {
                // Perguntar ao usuário se deseja verificar canceladas usando modal customizado
                verificarCanceladas = await mostrarDialogVerificarCanceladas();
                
                if (verificarCanceladas) {
                    updateButtonText(`Consultando canceladas (requisições externas)...`);
                    
                    // Processar em lotes paralelos para acelerar (máximo 5 requisições simultâneas)
                    const batchSize = 5;
                    const notasParaVerificar = allDownloadUrls.filter(item => 
                        item.visualizarUrl && !item.isSubstituida && !item.isCancelada
                    );
                    
                    console.log(`${LOG_PREFIX} Total de notas RECEBIDAS para verificar cancelamento: ${notasParaVerificar.length}`);
                    
                    for (let i = 0; i < notasParaVerificar.length; i += batchSize) {
                        const batch = notasParaVerificar.slice(i, Math.min(i + batchSize, notasParaVerificar.length));
                        const progress = Math.min(i + batchSize, notasParaVerificar.length);
                        updateButtonText(`Consultando canceladas ${progress} de ${notasParaVerificar.length}...`);
                        
                        // Processar batch em paralelo
                        await Promise.all(batch.map(async (item) => {
                            const cancelamentoInfo = await checkCanceladaPorSubstituicao(item.visualizarUrl);
                            if (cancelamentoInfo.isCancelada) {
                                item.isCanceladaPorSubstituicao = true;
                                item.numeroNfSubstituta = cancelamentoInfo.numeroNfSubstituta;
                                item.dataEventoCancelamento = cancelamentoInfo.dataEvento;
                            }
                        }));
                    }
                } else {
                    console.log(`${LOG_PREFIX} Usuário optou por NÃO verificar cancelamento por substituição`);
                    console.log(`${LOG_PREFIX} Executando verificação inteligente de cancelamento (apenas com dados já carregados)...`);
                    updateButtonText('Verificando cancelamentos inteligente...');
                    
                    // Mapear todas as notas pelo número/chave para referência rápida
                    const notasMap = new Map();
                    
                    // Primeiro, coletar todas as notas e suas chaves
                    for (const item of allDownloadUrls) {
                        try {
                            const response = await fetch(item.url);
                            if (response.ok) {
                                const xmlText = await response.text();
                                const xmlTextCleaned = xmlText.replace(/xmlns="[^"]*"/g, '');
                                const parser = new DOMParser();
                                const xmlDoc = parser.parseFromString(xmlTextCleaned, "text/xml");
                                
                                // Pegar o número da NF
                                const nNFSe = getXmlValue(xmlDoc, 'nNFSe');
                                
                                // Pegar a chave completa da NF
                                const chaveCompleta = getChaveCompletaFromXml(xmlDoc);
                                
                                if (nNFSe && chaveCompleta) {
                                    notasMap.set(chaveCompleta, {
                                        numero: nNFSe,
                                        item: item,
                                        xmlDoc: xmlDoc
                                    });
                                }
                            }
                        } catch (error) {
                            // Ignorar erros nesta fase
                        }
                    }
                    
                    console.log(`${LOG_PREFIX} Mapeadas ${notasMap.size} notas com suas chaves para verificação inteligente`);
                    
                    // Agora, verificar cada nota se ela substitui alguma outra
                    for (const item of allDownloadUrls) {
                        try {
                            const response = await fetch(item.url);
                            if (response.ok) {
                                const xmlText = await response.text();
                                const xmlTextCleaned = xmlText.replace(/xmlns="[^"]*"/g, '');
                                const parser = new DOMParser();
                                const xmlDoc = parser.parseFromString(xmlTextCleaned, "text/xml");
                                
                                // Verificar se esta nota tem tag <subst> com chave substituída
                                const chSubstda = getXmlValue(xmlDoc, 'DPS>infDPS>subst>chSubstda');
                                
                                if (chSubstda) {
                                    // Esta nota é uma substituta - procurar a nota substituída no mapa
                                    const notaSubstituida = notasMap.get(chSubstda);
                                    
                                    if (notaSubstituida) {
                                        // Encontramos a nota substituída na memória!
                                        const nNFSeSubstituta = getXmlValue(xmlDoc, 'nNFSe');
                                        console.log(`${LOG_PREFIX} VERIFICAÇÃO INTELIGENTE: Nota ${notaSubstituida.numero} (chave: ${chSubstda}) foi substituída pela nota ${nNFSeSubstituta}`);
                                        
                                        // Marcar a nota substituída como cancelada por substituição
                                        notaSubstituida.item.isCanceladaPorSubstituicao = true;
                                        notaSubstituida.item.numeroNfSubstituta = nNFSeSubstituta;
                                        
                                        // Extrair data do evento da nota substituta (data de emissão)
                                        const dhEmi = getXmlValue(xmlDoc, 'DPS>infDPS>dhEmi');
                                        if (dhEmi) {
                                            notaSubstituida.item.dataEventoCancelamento = new Date(dhEmi).toLocaleDateString('pt-BR');
                                        }
                                    }
                                }
                            }
                        } catch (error) {
                            // Ignorar erros nesta verificação
                        }
                    }
                    
                    console.log(`${LOG_PREFIX} Verificação inteligente concluída.`);
                }
            } else {
                console.log(`${LOG_PREFIX} Pulando verificação de cancelamento (não é página de recebidas)`);
            }

            for (const item of allDownloadUrls) {
                processedCount++;
                updateButtonText(`Processando ${processedCount} de ${allDownloadUrls.length}...`);
                try {
                    const response = await fetch(item.url);
                    if (!response.ok) throw new Error(`Falha ao baixar XML para o Excel`);
                    const xmlText = await response.text();
                    
                    const xmlTextCleaned = xmlText.replace(/xmlns="[^"]*"/g, '');
                    const parser = new DOMParser();
                    const xmlDoc = parser.parseFromString(xmlTextCleaned, "text/xml");

                    const nNFSe = getXmlValue(xmlDoc, 'nNFSe');
                    const localPrest = getXmlValue(xmlDoc, 'xLocPrestacao');
                    const dhEmi = getXmlValue(xmlDoc, 'DPS>infDPS>dhEmi');
                    const emissao = dhEmi ? new Date(dhEmi).toLocaleDateString('pt-BR') : '';
                    
                    // Usar as novas funções para obter CNPJ/CPF formatado
                    const documentoEmitente = getEmitenteDocument(xmlDoc);
                    const razaoEmitente = getXmlValue(xmlDoc, 'emit>xNome');
                    const documentoTomador = getTomadorDocument(xmlDoc);
                    const razaoTomador = getXmlValue(xmlDoc, 'DPS>infDPS>toma>xNome');
                    
                    // Se for o primeiro XML e o cabeçalho ainda não tiver dados da empresa,
                    // atualizar com base no tipo de relatório
                    if (!companyInfo.companyName && processedCount === 1) {
                        if (reportType === 'Emitidas') {
                            // Para notas emitidas, usar dados do tomador
                            companyInfo.companyName = razaoTomador;
                            companyInfo.companyCNPJ = documentoTomador;
                        } else if (reportType === 'Recebidas') {
                            // Para notas recebidas, usar dados do emitente
                            companyInfo.companyName = razaoEmitente;
                            companyInfo.companyCNPJ = documentoEmitente;
                        }
                        // Atualizar cabeçalho
                        if (companyInfo.companyName) {
                            worksheet.getRow(1).getCell(1).value = companyInfo.companyName;
                        }
                        if (companyInfo.companyCNPJ) {
                            worksheet.getRow(2).getCell(1).value = `CNPJ/CPF: ${companyInfo.companyCNPJ}`;
                        }
                    }
                    
                    const nbs = getXmlValue(xmlDoc, 'DPS>infDPS>serv>cServ>cNBS');
                    const descNbs = getXmlValue(xmlDoc, 'xNBS');
                    const codTrib = getXmlValue(xmlDoc, 'DPS>infDPS>serv>cServ>cTribNac');
                    const descTrib = getXmlValue(xmlDoc, 'xTribNac');
                    const descServico = getXmlValue(xmlDoc, 'DPS>infDPS>serv>cServ>xDescServ')
                                           .replace(/(\r\n|\n|\r)/gm, ' ')
                                           .replace(/\s+/g, ' ')
                                           .trim();

                    const vlServico = getXmlValue(xmlDoc, 'DPS>infDPS>valores>vServPrest>vServ');
                    
                    // Obter o valor do ISSQN da tag <vISSQN>
                    const vISSQN = getXmlValue(xmlDoc, 'valores>vISSQN');
                    
                    const tpRetIss = getXmlValue(xmlDoc, 'DPS>infDPS>valores>trib>tribMun>tpRetISSQN');
                    let issStatus = '';
                    switch(tpRetIss) {
                        case '1': issStatus = 'Não retido'; break;
                        case '2': issStatus = 'Retido'; break;
                        case '3': issStatus = 'Retido Interm.'; break;
                        default: issStatus = '';
                    }
                    
                    // Valor do ISSQN Retido - apenas se tpRetIss for '2' (Retido)
                    let vRetIss = '';
                    if (tpRetIss === '2') {
                        vRetIss = getXmlValue(xmlDoc, 'valores>vISSQN');
                    }

                    const tpRetPisCofins = getXmlValue(xmlDoc, 'DPS>infDPS>valores>trib>tribFed>piscofins>tpRetPisCofins');
                    
                    // Tipo Ret. Pis/Cofins
                    let tipoRetPisCofins = '';
                    if (tpRetPisCofins === '1') {
                        tipoRetPisCofins = 'Retido';
                    }
                    
                    let vRetPis = '';
                    let vRetCofins = '';
                    if (tpRetPisCofins === '1') {
                        vRetPis = getXmlValue(xmlDoc, 'DPS>infDPS>valores>trib>tribFed>piscofins>vPis');
                        vRetCofins = getXmlValue(xmlDoc, 'DPS>infDPS>valores>trib>tribFed>piscofins>vCofins');
                    }

                    const vRetIrrf = getXmlValue(xmlDoc, 'DPS>infDPS>valores>trib>tribFed>vRetIRRF');
                    const vRetCsll = getXmlValue(xmlDoc, 'DPS>infDPS>valores>trib>tribFed>vRetCSLL');
                    
                    // INSS Retido (vRetCP)
                    const vRetInss = getXmlValue(xmlDoc, 'DPS>infDPS>valores>trib>tribFed>vRetCP');
                    
                    const vlLiquido = getXmlValue(xmlDoc, 'valores>vLiq');

                    // DETECTAR SE A NOTA FOI SUBSTITUÍDA OU CANCELADA
                    let observacao = '';
                    const isInvalida = item.isSubstituida || item.isCancelada || item.isCanceladaPorSubstituicao;
                    
                    if (item.isSubstituida) {
                        observacao = 'CANCELADA - NFS-e substituída';
                    } else if (item.isCanceladaPorSubstituicao) {
                        // MODIFICAÇÃO: Para notas recebidas, se foi detectada pela verificação inteligente
                        if (isRecebidas) {
                            if (item.numeroNfSubstituta) {
                                observacao = `CANCELADA POR SUBSTITUIÇÃO - NF ${item.numeroNfSubstituta}`;
                            } else {
                                observacao = 'CANCELADA POR SUBSTITUIÇÃO';
                            }
                        } else {
                            // Para notas emitidas, manter o formato completo com número e data
                            if (item.numeroNfSubstituta && item.dataEventoCancelamento) {
                                observacao = `CANCELADA POR SUBSTITUIÇÃO - NF ${item.numeroNfSubstituta} em ${item.dataEventoCancelamento}`;
                            } else if (item.numeroNfSubstituta) {
                                observacao = `CANCELADA POR SUBSTITUIÇÃO - NF ${item.numeroNfSubstituta}`;
                            } else {
                                observacao = 'CANCELADA POR SUBSTITUIÇÃO';
                            }
                        }
                    } else if (item.isCancelada) {
                        observacao = 'CANCELADA - NFS-e cancelada';
                    }

                    // LÓGICA MODIFICADA: Se ISS for "Não retido", colocar o valor do ISSQN na coluna "ISS Valor"
                    // Se for "Retido", colocar o valor na coluna "ISS Ret." (já existente)
                    let issValor = '';
                    let issRetValor = '';
                    
                    if (issStatus === 'Não retido') {
                        issValor = isInvalida ? '0,00' : formatCurrencyPtBr(vISSQN);
                        issRetValor = '0,00';
                    } else if (issStatus === 'Retido') {
                        issValor = '';
                        issRetValor = isInvalida ? '0,00' : formatCurrencyPtBr(vRetIss);
                    } else if (issStatus === 'Retido Interm.') {
                        issValor = '';
                        issRetValor = isInvalida ? '0,00' : formatCurrencyPtBr(vISSQN);
                    } else {
                        // Para qualquer outro status ou vazio
                        issValor = '';
                        issRetValor = '0,00';
                    }

                    // Adicionar linha na planilha
                    const rowData = [
                        nNFSe, 
                        localPrest, 
                        emissao, 
                        documentoEmitente, 
                        razaoEmitente,
                        documentoTomador, 
                        razaoTomador, 
                        nbs, 
                        descNbs, 
                        codTrib,
                        descTrib, 
                        descServico, 
                        isInvalida ? '0,00' : formatCurrencyPtBr(vlServico), 
                        isInvalida ? '' : issStatus,
                        issValor,
                        issRetValor,
                        isInvalida ? '0,00' : formatCurrencyPtBr(vRetPis), 
                        isInvalida ? '0,00' : formatCurrencyPtBr(vRetCofins), 
                        isInvalida ? '0,00' : formatCurrencyPtBr(vRetIrrf), 
                        isInvalida ? '0,00' : formatCurrencyPtBr(vRetCsll),
                        isInvalida ? '0,00' : formatCurrencyPtBr(vRetInss),
                        tipoRetPisCofins,
                        isInvalida ? '0,00' : formatCurrencyPtBr(vlLiquido),
                        observacao
                    ];
                    
                    const row = worksheet.addRow(rowData);
                    
                    // Estilizar linhas de notas canceladas/substituídas
                    if (isInvalida) {
                        row.font = { color: { argb: 'FFFF0000' }, italic: true }; // Vermelho e itálico
                        row.fill = {
                            type: 'pattern',
                            pattern: 'solid',
                            fgColor: { argb: 'FFFFF0F0' } // Vermelho muito claro
                        };
                    }

                } catch (e) {
                    console.error(`${LOG_PREFIX} Erro ao processar XML ${item.filename}:`, e);
                }
            }

            updateButtonText('Criando arquivo Excel...');
            
            // Agora precisamos converter os valores de string para números no Excel
            worksheet.eachRow((row, rowNumber) => {
                if (rowNumber > 6) { // Pular cabeçalho (linhas 1-6)
                    // Colunas que contêm valores monetários (0-based index)
                    const currencyColumns = [12, 14, 15, 16, 17, 18, 19, 20, 22];
                    
                    currencyColumns.forEach(colIndex => {
                        const cell = row.getCell(colIndex + 1); // ExcelJS é 1-based
                        if (cell.value && cell.value !== '' && cell.value !== '0,00') {
                            try {
                                // Converter string formatada em pt-BR para número
                                let cellValue = cell.value.toString();
                                
                                // Se já está formatado como "12.754,00"
                                if (cellValue.includes('.')) {
                                    // Remover pontos de milhar
                                    cellValue = cellValue.replace(/\./g, '');
                                }
                                
                                // Substituir vírgula decimal por ponto
                                cellValue = cellValue.replace(',', '.');
                                
                                const numValue = parseFloat(cellValue);
                                if (!isNaN(numValue)) {
                                    cell.value = numValue;
                                    cell.numFmt = '#,##0.00';
                                    cell.alignment = { horizontal: 'right' };
                                }
                            } catch (e) {
                                console.log(`${LOG_PREFIX} Erro ao converter valor da célula:`, cell.value, e);
                            }
                        } else if (cell.value === '0,00' || cell.value === '') {
                            // Para valores zerados ou vazios, colocar 0
                            cell.value = 0;
                            cell.numFmt = '#,##0.00';
                            cell.alignment = { horizontal: 'right' };
                        }
                    });
                }
            });

            // Congelar linha do cabeçalho (linha 6 agora, pois as linhas 1-5 são o cabeçalho da empresa)
            worksheet.views = [
                { state: 'frozen', ySplit: 6, xSplit: 0 }
            ];

            // Aplicar bordas a todas as células com dados
            const rowCount = worksheet.rowCount;
            const colCount = worksheet.columnCount;
            
            for (let i = 1; i <= rowCount; i++) {
                const row = worksheet.getRow(i);
                for (let j = 1; j <= colCount; j++) {
                    const cell = row.getCell(j);
                    cell.border = {
                        top: { style: 'thin' },
                        left: { style: 'thin' },
                        bottom: { style: 'thin' },
                        right: { style: 'thin' }
                    };
                }
            }

            // ADICIONAR LINHA DE TOTAIS
            const totalRow = worksheet.addRow([]);
            totalRow.getCell(1).value = 'TOTAIS';
            totalRow.getCell(1).font = { bold: true, size: 12 };
            totalRow.getCell(1).fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FFFFEB3B' }
            };
            
            // Definir fórmulas de soma para as colunas numéricas
            const sumColumns = [13, 15, 16, 17, 18, 19, 20, 21, 23];
            sumColumns.forEach(colNum => {
                const cell = totalRow.getCell(colNum);
                cell.value = { formula: `SUM(${worksheet.getColumn(colNum).letter}7:${worksheet.getColumn(colNum).letter}${rowCount})` };
                cell.numFmt = '#,##0.00';
                cell.font = { bold: true, size: 11 };
                cell.fill = {
                    type: 'pattern',
                    pattern: 'solid',
                    fgColor: { argb: 'FFFFEB3B' }
                };
                cell.alignment = { horizontal: 'right' };
                cell.border = {
                    top: { style: 'double' },
                    left: { style: 'thin' },
                    bottom: { style: 'double' },
                    right: { style: 'thin' }
                };
            });
            
            // Aplicar borda dupla em todas as células da linha de totais
            for (let j = 1; j <= colCount; j++) {
                const cell = totalRow.getCell(j);
                if (!cell.border) {
                    cell.border = {
                        top: { style: 'double' },
                        left: { style: 'thin' },
                        bottom: { style: 'double' },
                        right: { style: 'thin' }
                    };
                }
            }

            // =====================================================
            // CRIAR ABA DE RESUMO POR SERVIÇO
            // =====================================================
            const worksheetResumo = workbook.addWorksheet('Resumo por Serviço');
            
            // Criar objeto para agrupar por serviço
            const servicoMap = new Map();
            
            worksheet.eachRow((row, rowNumber) => {
                if (rowNumber > 6 && rowNumber <= rowCount) { // Pular cabeçalho (linhas 1-6) e linha de totais
                    const codTributacao = row.getCell(10).value || '';
                    const descrTributacao = row.getCell(11).value || 'Sem descrição';
                    const vlServico = parseFloat(row.getCell(13).value) || 0;
                    const issValor = parseFloat(row.getCell(15).value) || 0;
                    const issRet = parseFloat(row.getCell(16).value) || 0;
                    const pisRet = parseFloat(row.getCell(17).value) || 0;
                    const cofinsRet = parseFloat(row.getCell(18).value) || 0;
                    const irRet = parseFloat(row.getCell(19).value) || 0;
                    const csllRet = parseFloat(row.getCell(20).value) || 0;
                    const inssRet = parseFloat(row.getCell(21).value) || 0;
                    const vlLiq = parseFloat(row.getCell(23).value) || 0;
                    
                    const key = `${codTributacao}|${descrTributacao}`;
                    
                    if (!servicoMap.has(key)) {
                        servicoMap.set(key, {
                            codTributacao: codTributacao,
                            descrTributacao: descrTributacao,
                            quantidade: 0,
                            vlServico: 0,
                            issValor: 0,
                            issRet: 0,
                            pisRet: 0,
                            cofinsRet: 0,
                            irRet: 0,
                            csllRet: 0,
                            inssRet: 0,
                            vlLiq: 0
                        });
                    }
                    
                    const item = servicoMap.get(key);
                    item.quantidade++;
                    item.vlServico += vlServico;
                    item.issValor += issValor;
                    item.issRet += issRet;
                    item.pisRet += pisRet;
                    item.cofinsRet += cofinsRet;
                    item.irRet += irRet;
                    item.csllRet += csllRet;
                    item.inssRet += inssRet;
                    item.vlLiq += vlLiq;
                }
            });
            
            // Cabeçalhos do resumo
            const resumoHeaders = [
                'Cod. Tributacao', 'Descr. Tributacao', 'Qtd. Notas', 'Vl. Total Serviços', 
                'ISS Valor Total', 'ISS Ret. Total', 'Pis Ret. Total', 'Cofins Ret. Total',
                'IR Ret. Total', 'CSLL Ret. Total', 'INSS Ret. Total', 'Vl. Líquido Total'
            ];
            
            const resumoHeaderRow = worksheetResumo.addRow(resumoHeaders);
            resumoHeaderRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
            resumoHeaderRow.fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FF0070C0' }
            };
            resumoHeaderRow.alignment = { vertical: 'middle', horizontal: 'center' };
            
            // Ajustar largura das colunas
            worksheetResumo.columns = [
                { width: 18 }, { width: 40 }, { width: 12 }, { width: 18 },
                { width: 15 }, { width: 15 }, { width: 15 }, { width: 15 },
                { width: 15 }, { width: 15 }, { width: 15 }, { width: 18 }
            ];
            
            // Adicionar dados agrupados
            servicoMap.forEach((item) => {
                const resumoRow = worksheetResumo.addRow([
                    item.codTributacao,
                    item.descrTributacao,
                    item.quantidade,
                    item.vlServico,
                    item.issValor,
                    item.issRet,
                    item.pisRet,
                    item.cofinsRet,
                    item.irRet,
                    item.csllRet,
                    item.inssRet,
                    item.vlLiq
                ]);
                
                // Formatar valores monetários (colunas 4 a 12)
                for (let i = 4; i <= 12; i++) {
                    resumoRow.getCell(i).numFmt = '#,##0.00';
                    resumoRow.getCell(i).alignment = { horizontal: 'right' };
                }
                
                // Formatar quantidade
                resumoRow.getCell(3).alignment = { horizontal: 'center' };
            });
            
            // Linha de totais do resumo
            const resumoTotalRow = worksheetResumo.addRow([]);
            resumoTotalRow.getCell(1).value = 'TOTAIS GERAIS';
            resumoTotalRow.getCell(1).font = { bold: true, size: 12 };
            resumoTotalRow.getCell(1).fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FFFFEB3B' }
            };
            
            const lastResumoRow = worksheetResumo.rowCount;
            const resumoSumColumns = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
            resumoSumColumns.forEach(colNum => {
                const cell = resumoTotalRow.getCell(colNum);
                cell.value = { formula: `SUM(${worksheetResumo.getColumn(colNum).letter}2:${worksheetResumo.getColumn(colNum).letter}${lastResumoRow - 1})` };
                if (colNum > 3) {
                    cell.numFmt = '#,##0.00';
                }
                cell.font = { bold: true, size: 11 };
                cell.fill = {
                    type: 'pattern',
                    pattern: 'solid',
                    fgColor: { argb: 'FFFFEB3B' }
                };
                cell.alignment = { horizontal: colNum === 3 ? 'center' : 'right' };
            });
            
            // Aplicar bordas na aba de resumo
            worksheetResumo.eachRow((row) => {
                row.eachCell((cell) => {
                    cell.border = {
                        top: { style: 'thin' },
                        left: { style: 'thin' },
                        bottom: { style: 'thin' },
                        right: { style: 'thin' }
                    };
                });
            });
            
            // Congelar cabeçalho do resumo
            worksheetResumo.views = [
                { state: 'frozen', ySplit: 1, xSplit: 0 }
            ];

            // =====================================================
            // CRIAR ABA DE IMPOSTOS RETIDOS
            // =====================================================
            const worksheetImpostos = workbook.addWorksheet('Impostos Retidos');
            
            // Cabeçalhos da aba de impostos - dinâmicos baseados no tipo de relatório
            let cnpjHeader, razaoHeader;
            if (reportType === 'Recebidas') {
                cnpjHeader = 'CNPJ/CPF Emitente';
                razaoHeader = 'Razão Emitente';
            } else {
                cnpjHeader = 'CNPJ/CPF Tomador';
                razaoHeader = 'Razão Tomador';
            }
            
            const impostosHeaders = [
                'Nº NFSe', 'Emissão', cnpjHeader, razaoHeader,
                'Vl. Serviço', 'ISS Ret.', 'Pis Ret.', 'Cofins Ret.',
                'IR Ret.', 'CSLL Ret.', 'INSS Ret.', 'Total Retido'
            ];
            
            const impostosHeaderRow = worksheetImpostos.addRow(impostosHeaders);
            impostosHeaderRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
            impostosHeaderRow.fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FFFF6B6B' }
            };
            impostosHeaderRow.alignment = { vertical: 'middle', horizontal: 'center' };
            
            // Ajustar largura das colunas
            worksheetImpostos.columns = [
                { width: 15 }, { width: 12 }, { width: 18 }, { width: 30 },
                { width: 15 }, { width: 12 }, { width: 12 }, { width: 12 },
                { width: 12 }, { width: 12 }, { width: 12 }, { width: 15 }
            ];
            
            // Adicionar apenas notas com impostos retidos
            worksheet.eachRow((row, rowNumber) => {
                if (rowNumber > 6 && rowNumber <= rowCount) { // Pular cabeçalho (linhas 1-6) e linha de totais
                    const issRet = parseFloat(row.getCell(16).value) || 0;
                    const pisRet = parseFloat(row.getCell(17).value) || 0;
                    const cofinsRet = parseFloat(row.getCell(18).value) || 0;
                    const irRet = parseFloat(row.getCell(19).value) || 0;
                    const csllRet = parseFloat(row.getCell(20).value) || 0;
                    const inssRet = parseFloat(row.getCell(21).value) || 0;
                    
                    const totalRetido = issRet + pisRet + cofinsRet + irRet + csllRet + inssRet;
                    
                    // Só adicionar se tiver algum imposto retido
                    if (totalRetido > 0) {
                        const nNFSe = row.getCell(1).value;
                        const emissao = row.getCell(3).value;
                        const vlServico = parseFloat(row.getCell(13).value) || 0;
                        
                        // Determinar qual CNPJ/CPF e Razão usar baseado no tipo de relatório
                        let documento, razao;
                        if (reportType === 'Recebidas') {
                            // Para notas recebidas, usar dados do emitente
                            documento = row.getCell(4).value;  // CNPJ/CPF Emitente
                            razao = row.getCell(5).value; // Razão Emitente
                        } else {
                            // Para notas emitidas, usar dados do tomador
                            documento = row.getCell(6).value;  // CNPJ/CPF Tomador
                            razao = row.getCell(7).value; // Razão Tomador
                        }
                        
                        const impostosRow = worksheetImpostos.addRow([
                            nNFSe,
                            emissao,
                            documento,
                            razao,
                            vlServico,
                            issRet,
                            pisRet,
                            cofinsRet,
                            irRet,
                            csllRet,
                            inssRet,
                            totalRetido
                        ]);
                        
                        // Formatar valores monetários (colunas 5 a 12)
                        for (let i = 5; i <= 12; i++) {
                            impostosRow.getCell(i).numFmt = '#,##0.00';
                            impostosRow.getCell(i).alignment = { horizontal: 'right' };
                        }
                    }
                }
            });
            
            // Linha de totais dos impostos
            const impostosTotalRow = worksheetImpostos.addRow([]);
            impostosTotalRow.getCell(1).value = 'TOTAIS';
            impostosTotalRow.getCell(1).font = { bold: true, size: 12 };
            impostosTotalRow.getCell(1).fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FFFFEB3B' }
            };
            
            const lastImpostosRow = worksheetImpostos.rowCount;
            const impostosSumColumns = [5, 6, 7, 8, 9, 10, 11, 12];
            impostosSumColumns.forEach(colNum => {
                const cell = impostosTotalRow.getCell(colNum);
                cell.value = { formula: `SUM(${worksheetImpostos.getColumn(colNum).letter}2:${worksheetImpostos.getColumn(colNum).letter}${lastImpostosRow - 1})` };
                cell.numFmt = '#,##0.00';
                cell.font = { bold: true, size: 11 };
                cell.fill = {
                    type: 'pattern',
                    pattern: 'solid',
                    fgColor: { argb: 'FFFFEB3B' }
                };
                cell.alignment = { horizontal: 'right' };
            });
            
            // Aplicar bordas na aba de impostos
            worksheetImpostos.eachRow((row) => {
                row.eachCell((cell) => {
                    cell.border = {
                        top: { style: 'thin' },
                        left: { style: 'thin' },
                        bottom: { style: 'thin' },
                        right: { style: 'thin' }
                    };
                });
            });
            
            // Congelar cabeçalho dos impostos
            worksheetImpostos.views = [
                { state: 'frozen', ySplit: 1, xSplit: 0 }
            ];

            // =====================================================
            // CRIAR ABA DE NOTAS CANCELADAS
            // =====================================================
            const worksheetCanceladas = workbook.addWorksheet('Notas Canceladas');

            // Cabeçalhos da aba de canceladas (mesmos da aba principal)
            const canceladasHeaderRow = worksheetCanceladas.addRow(headers);
            canceladasHeaderRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
            canceladasHeaderRow.fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FFB91C1C' } // Vermelho escuro para diferenciar
            };
            canceladasHeaderRow.alignment = { vertical: 'middle', horizontal: 'left' };

            // Mesmas larguras de coluna da aba principal
            worksheetCanceladas.columns = [
                { width: 15 }, { width: 20 }, { width: 12 }, { width: 18 }, { width: 30 },
                { width: 18 }, { width: 30 }, { width: 10 }, { width: 25 }, { width: 15 },
                { width: 25 }, { width: 40 }, { width: 15 }, { width: 10 }, { width: 12 },
                { width: 12 }, { width: 12 }, { width: 15 }, { width: 12 }, { width: 12 },
                { width: 12 }, { width: 20 }, { width: 15 }, { width: 30 }
            ];

            let canceladasCount = 0;

            // Copiar apenas as linhas canceladas da aba principal
            worksheet.eachRow((row, rowNumber) => {
                if (rowNumber > 6 && rowNumber <= rowCount) {
                    const observacaoCell = row.getCell(24).value || '';
                    if (observacaoCell.toString().includes('CANCELADA')) {
                        const rowValues = [];
                        for (let c = 1; c <= 24; c++) {
                            rowValues.push(row.getCell(c).value);
                        }
                        const canceladaRow = worksheetCanceladas.addRow(rowValues);
                        canceladaRow.font = { color: { argb: 'FFB91C1C' }, italic: true };
                        canceladaRow.fill = {
                            type: 'pattern',
                            pattern: 'solid',
                            fgColor: { argb: 'FFFFF0F0' }
                        };
                        // Formatar colunas monetárias
                        const currColsCanceladas = [13, 15, 16, 17, 18, 19, 20, 21, 23];
                        currColsCanceladas.forEach(ci => {
                            const cell = canceladaRow.getCell(ci);
                            cell.numFmt = '#,##0.00';
                            cell.alignment = { horizontal: 'right' };
                        });
                        canceladasCount++;
                    }
                }
            });

            // Linha de totais das canceladas
            if (canceladasCount > 0) {
                const canceladasTotalRow = worksheetCanceladas.addRow([]);
                canceladasTotalRow.getCell(1).value = 'TOTAIS';
                canceladasTotalRow.getCell(1).font = { bold: true, size: 12 };
                canceladasTotalRow.getCell(1).fill = {
                    type: 'pattern',
                    pattern: 'solid',
                    fgColor: { argb: 'FFFFEB3B' }
                };
                const lastCancelRow = worksheetCanceladas.rowCount;
                [13, 15, 16, 17, 18, 19, 20, 21, 23].forEach(colNum => {
                    const cell = canceladasTotalRow.getCell(colNum);
                    cell.value = { formula: `SUM(${worksheetCanceladas.getColumn(colNum).letter}2:${worksheetCanceladas.getColumn(colNum).letter}${lastCancelRow - 1})` };
                    cell.numFmt = '#,##0.00';
                    cell.font = { bold: true, size: 11 };
                    cell.fill = {
                        type: 'pattern',
                        pattern: 'solid',
                        fgColor: { argb: 'FFFFEB3B' }
                    };
                    cell.alignment = { horizontal: 'right' };
                });
            } else {
                // Mensagem caso não haja canceladas
                const semCanceladasRow = worksheetCanceladas.addRow(['Nenhuma nota cancelada encontrada.']);
                semCanceladasRow.font = { italic: true, color: { argb: 'FF6B7280' } };
                worksheetCanceladas.mergeCells(2, 1, 2, 24);
            }

            // Aplicar bordas na aba de canceladas
            worksheetCanceladas.eachRow((row) => {
                row.eachCell((cell) => {
                    cell.border = {
                        top: { style: 'thin' },
                        left: { style: 'thin' },
                        bottom: { style: 'thin' },
                        right: { style: 'thin' }
                    };
                });
            });

            // Congelar cabeçalho
            worksheetCanceladas.views = [
                { state: 'frozen', ySplit: 1, xSplit: 0 }
            ];

            // Gerar o arquivo Excel
            updateButtonText('Salvando arquivo...');
            const buffer = await workbook.xlsx.writeBuffer();
            const blob = new Blob([buffer], { 
                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
            });
            
            const url = URL.createObjectURL(blob);
            const downloadLink = document.createElement('a');
            downloadLink.href = url;
            const today = new Date();
            const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
            const timeStr = today.toTimeString().slice(0, 5).replace(/:/g, '');
            downloadLink.download = `${reportPrefix}_NFS-e_${dateStr}_${timeStr}.xlsx`;
            
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            setTimeout(() => URL.revokeObjectURL(url), 1000);

            updateButtonText('Concluído!');
            setTimeout(() => {
                generateExcelBtn.innerHTML = originalHtml;
                generateExcelBtn.disabled = false;
            }, 3000);

        } catch (error) {
            console.error(`${LOG_PREFIX} Erro no processo de geração de Excel:`, error);
            alert('Ocorreu um erro ao gerar o relatório Excel: ' + error.message);
            generateExcelBtn.innerHTML = originalHtml;
            generateExcelBtn.disabled = false;
        }
    }

    // --- LÓGICA DE INICIALIZAÇÃO ---
    function initialize() {
        console.log(`${LOG_PREFIX} Iniciando verificação de elementos...`);
        
        const table = document.querySelector('table.table-striped');
        console.log(`${LOG_PREFIX} Tabela encontrada:`, !!table);
        
        if (table) {
            const rows = table.querySelectorAll('tbody tr');
            console.log(`${LOG_PREFIX} Linhas na tabela:`, rows.length);
        }
        
        addCheckboxesToTable();
        addDirectDownloadButtons();
        addButton();
        
        chrome.storage.local.get(['licenseStatus'], function(result) {
            currentLicenseStatus = result.licenseStatus;
            console.log(`${LOG_PREFIX} Status da licença carregado:`, currentLicenseStatus);
        });
    }

    // MutationObserver para detectar quando a tabela é carregada
    const observer = new MutationObserver(() => {
        const table = document.querySelector('table.table-striped tbody tr');
        const hasCheckbox = document.querySelector('th.checkbox-column');
        const hasButton = document.getElementById('downloadAllZipBtn');
        
        if (table && !hasCheckbox) {
            console.log(`${LOG_PREFIX} Tabela detectada, adicionando checkboxes...`);
            addCheckboxesToTable();
        }
        
        if (table && !hasButton) {
            console.log(`${LOG_PREFIX} Tabela detectada, adicionando botões...`);
            addButton();
        }
        
        // Adicionar botões de download direto sempre que a tabela mudar
        if (table) {
            addDirectDownloadButtons();
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    console.log(`${LOG_PREFIX} Script de inicialização configurado.`);

})();