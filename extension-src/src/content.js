// content.js — Main orchestration
// Runs on Recebidas and Emitidas pages after document_idle.

'use strict';

const LOG = '[NFSE-EXT]';
const BASE = 'https://www.nfse.gov.br';
const BATCH_SIZE  = 5;
const MAX_RETRIES = 3;
const RETRY_DELAY = 2000; // ms

const isRecebidas = window.location.href.includes('/Notas/Recebidas');
const isEmitidas  = window.location.href.includes('/Notas/Emitidas');

if (!isRecebidas && !isEmitidas) {
    console.log(LOG, 'Not a supported page, exiting.');
} else {
    console.log(LOG, 'Page detected:', isRecebidas ? 'Recebidas' : 'Emitidas');
    injectPanel(isRecebidas);
    document.getElementById('nfse-btn-start').addEventListener('click', runExtraction);
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function getMonthFromDate(dateStr) {
    // dateStr = "DD/MM/YYYY" → "MM-YYYY"
    try {
        const parts = dateStr.split('/');
        return `${parts[1]}-${parts[2]}`;
    } catch {
        const now = new Date();
        return `${String(now.getMonth() + 1).padStart(2,'0')}-${now.getFullYear()}`;
    }
}

function getCompanyName() {
    // Try to get company name from the page (JWT or page title)
    try {
        const token = window.sessionStorage.getItem('accessToken');
        if (token) {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.nome || payload.inscricao || 'Empresa';
        }
    } catch {}
    return document.title.replace('NFS-e | ', '').trim() || 'Empresa';
}

// ─────────────────────────────────────────────
// Pagination
// ─────────────────────────────────────────────

function getTotalPages() {
    const descEl = document.querySelector('.paginacao .descricao');
    if (!descEl) return 1;

    const match = descEl.textContent.match(/de\s+(\d+)\s+registros/);
    if (!match) return 1;

    const total = parseInt(match[1]);
    const rowsOnPage = document.querySelectorAll('tbody tr[data-chave]').length;
    if (rowsOnPage === 0) return 1;

    return Math.ceil(total / rowsOnPage);
}

async function fetchPage(pageNum) {
    const url = new URL(window.location.href);
    url.searchParams.set('pg', pageNum);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`Page fetch failed: ${res.status}`);
    return res.text();
}

function parseChavesFromHtml(html) {
    const doc  = new DOMParser().parseFromString(html, 'text/html');
    const rows = doc.querySelectorAll('tbody tr[data-chave]');
    return [...rows].map(tr => ({
        chave:      tr.getAttribute('data-chave'),
        cancelada:  tr.classList.contains('nfse-cancelada'),
    })).filter(r => r.chave);
}

async function collectAllChaves(totalPages) {
    const all = [];

    // Page 1 is already loaded — scrape DOM directly
    const page1rows = document.querySelectorAll('tbody tr[data-chave]');
    page1rows.forEach(tr => {
        all.push({
            chave:     tr.getAttribute('data-chave'),
            cancelada: tr.classList.contains('nfse-cancelada'),
        });
    });
    updateProgress(1, totalPages, `[OK] Página 1: ${page1rows.length} notas`);

    // Remaining pages
    for (let pg = 2; pg <= totalPages; pg++) {
        try {
            const html  = await fetchPage(pg);
            const rows  = parseChavesFromHtml(html);
            all.push(...rows);
            updateProgress(pg, totalPages, `[OK] Página ${pg}: ${rows.length} notas`);
        } catch (e) {
            updateProgress(pg, totalPages, `[AVISO] Falha na página ${pg}: ${e.message}`);
        }
    }

    return all;
}

// ─────────────────────────────────────────────
// Downloads
// ─────────────────────────────────────────────

async function fetchWithRetry(url, retries = MAX_RETRIES) {
    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            const res = await fetch(url);

            if (res.status === 429) {
                console.log(LOG, 'Rate limit 429, waiting 30s...');
                await sleep(30000);
                continue;
            }
            if (res.status === 403) {
                await sleep(5000);
                continue;
            }
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }

            // Detect session expiry: portal returns HTML login page
            const ct = res.headers.get('content-type') || '';
            if (ct.includes('text/html')) {
                throw new Error('SESSION_EXPIRED');
            }

            return res;
        } catch (e) {
            if (e.message === 'SESSION_EXPIRED') throw e;
            if (attempt < retries) {
                await sleep(RETRY_DELAY);
            } else {
                throw e;
            }
        }
    }
}

async function fetchXml(chave) {
    const url = `${BASE}/emissornacional/DPS/ModalCaptcha/NFSe/${chave}`;
    const res = await fetchWithRetry(url);
    const text = await res.text();

    // Double-check it's XML and not HTML (session expiry fallback)
    if (text.trimStart().startsWith('<!')) {
        throw new Error('SESSION_EXPIRED');
    }
    return text;
}

async function fetchPdf(chave) {
    const url = `${BASE}/emissornacional/DPS/ModalCaptcha/DANFSe/${chave}`;
    const res = await fetchWithRetry(url);
    return res.arrayBuffer();
}

// ─────────────────────────────────────────────
// ZIP builder
// ─────────────────────────────────────────────

function buildZip(noteResults, excelBuffer, companyName, month, isRecebidas) {
    const zip = new JSZip();

    noteResults.forEach(({ chave, xmlText, pdfBuffer, parsed }) => {
        if (!xmlText) return;
        const fname = chave;

        // all/
        zip.file(`all/xmls/${fname}.xml`, xmlText);
        if (pdfBuffer) zip.file(`all/pdfs/${fname}.pdf`, pdfBuffer);

        if (isRecebidas) {
            if (parsed?.cancelada) {
                zip.file(`canceladas/xmls/${fname}.xml`, xmlText);
            } else if (parsed?.isFederal) {
                zip.file(`federal/xmls/${fname}.xml`, xmlText);
                if (pdfBuffer) zip.file(`federal/pdfs/${fname}.pdf`, pdfBuffer);
            } else if (parsed?.isMunicipal) {
                zip.file(`municipal/xmls/${fname}.xml`, xmlText);
                if (pdfBuffer) zip.file(`municipal/pdfs/${fname}.pdf`, pdfBuffer);
            } else {
                zip.file(`sem_retencao/xmls/${fname}.xml`, xmlText);
            }
        }
    });

    // Excel
    if (excelBuffer) {
        const safeName = companyName.replace(/[/\\:]/g, '_');
        const xlsxName = isRecebidas
            ? `Recebidas_NFS-e_${safeName}_${month}.xlsx`
            : `Emitidas_NFS-e_${safeName}_${month}.xlsx`;
        zip.file(xlsxName, excelBuffer);
    }

    return zip;
}

// ─────────────────────────────────────────────
// Main flow
// ─────────────────────────────────────────────

async function runExtraction() {
    const { ini, fim } = getDateInputs();
    if (!ini || !fim) {
        alert('Por favor preencha as datas antes de iniciar.');
        return;
    }

    setPanelRunning(true);
    document.getElementById('nfse-summary').style.display = 'none';

    const companyName = getCompanyName();
    const month       = getMonthFromDate(ini);
    const totalPages  = getTotalPages();

    updateProgress(0, 1, `[OK] ${totalPages} página(s) detectada(s)`);

    // Step 1: collect all chaves
    updateProgress(0, totalPages, '[OK] Coletando lista de notas...');
    let allChaves;
    try {
        allChaves = await collectAllChaves(totalPages);
    } catch (e) {
        updateProgress(0, 1, `[ERRO] Falha ao coletar notas: ${e.message}`);
        setPanelRunning(false);
        return;
    }

    updateProgress(0, allChaves.length, `[OK] ${allChaves.length} nota(s) encontrada(s) — iniciando downloads...`);

    if (allChaves.length === 0) {
        updateProgress(0, 1, '[AVISO] Nenhuma nota encontrada no período.');
        setPanelRunning(false);
        return;
    }

    // Step 2: download + parse in batches
    const noteResults = [];
    const stats = { total: 0, federal: 0, municipal: 0, semRet: 0, canceladas: 0, failed: 0 };
    let downloaded = 0;

    for (let i = 0; i < allChaves.length; i += BATCH_SIZE) {
        const batch = allChaves.slice(i, Math.min(i + BATCH_SIZE, allChaves.length));

        await Promise.all(batch.map(async ({ chave, cancelada: isCanceladaRow }) => {
            let xmlText   = null;
            let pdfBuffer = null;
            let parsed    = null;

            try {
                xmlText = await fetchXml(chave);
            } catch (e) {
                if (e.message === 'SESSION_EXPIRED') {
                    updateProgress(downloaded, allChaves.length,
                        '[ERRO] Sessão expirada — faça login novamente e repita.');
                    setPanelRunning(false);
                    throw e; // abort entire run
                }
                updateProgress(downloaded, allChaves.length,
                    `[AVISO] XML falhou: ${chave.slice(0,16)}...`);
                stats.failed++;
                return;
            }

            try {
                pdfBuffer = await fetchPdf(chave);
            } catch {
                updateProgress(downloaded, allChaves.length,
                    `[AVISO] PDF falhou: ${chave.slice(0,16)}... (XML ok)`);
            }

            parsed = parseNfseXml(xmlText);
            downloaded++;
            stats.total++;

            if (!parsed) {
                stats.failed++;
                updateProgress(downloaded, allChaves.length,
                    `[AVISO] XML inválido: ${chave.slice(0,16)}...`);
            } else if (parsed.cancelada || isCanceladaRow) {
                stats.canceladas++;
                updateProgress(downloaded, allChaves.length,
                    `[OK] CANCELADA | Nota ${parsed.numero}`);
            } else if (parsed.isFederal) {
                stats.federal++;
                updateProgress(downloaded, allChaves.length,
                    `[OK] FEDERAL | Nota ${parsed.numero}`);
            } else if (parsed.isMunicipal) {
                stats.municipal++;
                updateProgress(downloaded, allChaves.length,
                    `[OK] MUNICIPAL | Nota ${parsed.numero}`);
            } else {
                stats.semRet++;
                updateProgress(downloaded, allChaves.length,
                    `[OK] SEM RETENCAO | Nota ${parsed.numero}`);
            }

            noteResults.push({ chave, xmlText, pdfBuffer, parsed });
        }));
    }

    // Step 3: generate Excel
    updateProgress(downloaded, allChaves.length, '[OK] Gerando planilha Excel...');
    let excelBuffer = null;
    try {
        const parsedRows = noteResults.map(r => r.parsed).filter(Boolean);
        excelBuffer = isRecebidas
            ? await generateRecebidas(parsedRows, companyName, month)
            : await generateEmitidas(parsedRows, companyName, month);
    } catch (e) {
        updateProgress(downloaded, allChaves.length, `[AVISO] Erro ao gerar Excel: ${e.message}`);
    }

    // Step 4: build and download ZIP
    updateProgress(downloaded, allChaves.length, '[OK] Comprimindo ZIP...');
    try {
        const zip      = buildZip(noteResults, excelBuffer, companyName, month, isRecebidas);
        const safeName = companyName.replace(/[/\\:]/g, '_');
        const zipName  = isRecebidas
            ? `reinf_${safeName}_${month}.zip`
            : `emitidas_${safeName}_${month}.zip`;
        const blob = await zip.generateAsync({ type: 'blob', compression: 'DEFLATE' });
        triggerDownload(blob, zipName);
        updateProgress(downloaded, allChaves.length, `[OK] ZIP gerado: ${zipName}`);
    } catch (e) {
        updateProgress(downloaded, allChaves.length, `[ERRO] Falha ao gerar ZIP: ${e.message}`);
    }

    // Done
    showSummary(stats);
    setPanelRunning(false);
    console.log(LOG, 'Run complete:', stats);
}
