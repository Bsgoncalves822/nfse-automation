// ui.js — Injected control panel and progress UI

'use strict';

const PANEL_ID = 'nfse-orprocon-panel';

function injectPanel(isRecebidas) {
    if (document.getElementById(PANEL_ID)) return;

    // Pre-fill dates from portal filter form if present
    const dateInicio = document.getElementById('datainicio')?.value || '';
    const dateFim    = document.getElementById('datafim')?.value   || '';

    const panel = document.createElement('div');
    panel.id    = PANEL_ID;
    panel.style.cssText = [
        'position:fixed', 'bottom:20px', 'right:20px', 'width:300px',
        'background:#1e293b', 'color:#f1f5f9', 'border-radius:10px',
        'padding:16px', 'z-index:999999', 'font-family:system-ui,sans-serif',
        'font-size:12px', 'box-shadow:0 8px 32px rgba(0,0,0,0.5)',
        'border:1px solid #334155', 'user-select:none'
    ].join(';');

    panel.innerHTML = `
        <style>
            #${PANEL_ID} * { box-sizing: border-box; }
            @keyframes nfse-spin { to { transform: rotate(360deg); } }
            #nfse-spinner {
                width:12px;height:12px;border:2px solid #38bdf8;
                border-top-color:transparent;border-radius:50%;
                animation:nfse-spin 0.7s linear infinite;display:none;
            }
        </style>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span style="font-size:11px;font-weight:700;color:#38bdf8;letter-spacing:.08em;text-transform:uppercase;">
                NFS-e ORPROCON
            </span>
            <div style="display:flex;align-items:center;gap:8px;">
                <div id="nfse-spinner"></div>
                <span id="nfse-status-dot" style="width:8px;height:8px;background:#22c55e;border-radius:50%;"></span>
            </div>
        </div>

        <div style="display:flex;gap:8px;margin-bottom:10px;">
            <div style="flex:1;">
                <label style="font-size:10px;color:#94a3b8;">De</label>
                <input id="nfse-date-ini" type="text" value="${dateInicio}"
                    placeholder="DD/MM/AAAA"
                    style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:4px;
                           padding:5px 8px;color:#f1f5f9;font-size:11px;font-family:monospace;">
            </div>
            <div style="flex:1;">
                <label style="font-size:10px;color:#94a3b8;">Até</label>
                <input id="nfse-date-fim" type="text" value="${dateFim}"
                    placeholder="DD/MM/AAAA"
                    style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:4px;
                           padding:5px 8px;color:#f1f5f9;font-size:11px;font-family:monospace;">
            </div>
        </div>

        <button id="nfse-btn-start"
            style="width:100%;padding:9px;background:#0284c7;color:white;border:none;
                   border-radius:5px;cursor:pointer;font-weight:700;font-size:12px;
                   transition:background .15s;">
            ${isRecebidas ? 'Baixar Recebidas' : 'Baixar Emitidas'}
        </button>

        <div id="nfse-working" style="display:none;margin-top:12px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span id="nfse-progress-label" style="color:#94a3b8;font-size:10px;">0 / 0</span>
                <span id="nfse-progress-pct" style="color:#38bdf8;font-size:10px;">0%</span>
            </div>
            <div style="background:#334155;height:5px;border-radius:3px;overflow:hidden;margin-bottom:8px;">
                <div id="nfse-progress-bar"
                    style="width:0%;height:100%;background:#22c55e;transition:width .2s;"></div>
            </div>
            <div id="nfse-log"
                style="height:120px;overflow-y:auto;background:#0f172a;border-radius:4px;
                       padding:8px;font-size:10px;font-family:monospace;line-height:1.6;">
            </div>
        </div>

        <div id="nfse-summary" style="display:none;margin-top:12px;
            background:#0f172a;border-radius:6px;padding:10px;font-size:11px;line-height:1.8;">
        </div>
    `;

    document.body.appendChild(panel);

    // Hover effect on button
    const btn = panel.querySelector('#nfse-btn-start');
    btn.addEventListener('mouseenter', () => btn.style.background = '#0369a1');
    btn.addEventListener('mouseleave', () => btn.style.background = '#0284c7');
}

function setPanelRunning(running) {
    const spinner = document.getElementById('nfse-spinner');
    const dot     = document.getElementById('nfse-status-dot');
    const btn     = document.getElementById('nfse-btn-start');
    const working = document.getElementById('nfse-working');

    if (running) {
        spinner.style.display = 'block';
        dot.style.background  = '#f59e0b';
        btn.disabled          = true;
        btn.style.opacity     = '0.5';
        btn.style.cursor      = 'not-allowed';
        working.style.display = 'block';
    } else {
        spinner.style.display = 'none';
        dot.style.background  = '#22c55e';
        btn.disabled          = false;
        btn.style.opacity     = '1';
        btn.style.cursor      = 'pointer';
    }
}

function updateProgress(current, total, msg) {
    const pct   = total > 0 ? Math.round((current / total) * 100) : 0;
    const bar   = document.getElementById('nfse-progress-bar');
    const label = document.getElementById('nfse-progress-label');
    const pctEl = document.getElementById('nfse-progress-pct');
    const log   = document.getElementById('nfse-log');

    if (bar)   bar.style.width   = pct + '%';
    if (label) label.textContent = `${current} / ${total}`;
    if (pctEl) pctEl.textContent = pct + '%';

    if (msg && log) {
        const line = document.createElement('div');
        line.style.color = msg.startsWith('[ERRO]') ? '#f87171'
                         : msg.startsWith('[AVISO]') ? '#fbbf24'
                         : msg.startsWith('[OK]') ? '#4ade80'
                         : '#94a3b8';
        line.textContent = msg;
        log.appendChild(line);
        log.scrollTop = log.scrollHeight;
    }
}

function showSummary(stats) {
    const el = document.getElementById('nfse-summary');
    if (!el) return;
    el.style.display = 'block';
    el.innerHTML = `
        <div style="color:#38bdf8;font-weight:700;margin-bottom:6px;">✓ Concluído</div>
        <div>Total: <b>${stats.total}</b></div>
        <div style="color:#4ade80;">Federal: <b>${stats.federal}</b></div>
        <div style="color:#60a5fa;">Municipal: <b>${stats.municipal}</b></div>
        <div style="color:#94a3b8;">Sem retenção: <b>${stats.semRet}</b></div>
        <div style="color:#f87171;">Canceladas: <b>${stats.canceladas}</b></div>
        ${stats.failed > 0 ? `<div style="color:#f87171;">Falhas: <b>${stats.failed}</b></div>` : ''}
    `;
}

function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a   = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function getDateInputs() {
    return {
        ini: document.getElementById('nfse-date-ini')?.value?.trim() || '',
        fim: document.getElementById('nfse-date-fim')?.value?.trim() || '',
    };
}
