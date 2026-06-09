// excel.js — Excel report generation using ExcelJS
// Mirrors Python generate_recebidas_excel() output exactly.

'use strict';

const EXCEL_STYLES = {
    hdrFont:  { name: 'Arial', bold: true,  color: { argb: 'FFFFFFFF' }, size: 10 },
    hdrFill:  { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1A56A0' } },
    hdrFillG: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1A7A4A' } },
    hdrFillR: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFC0392B' } },
    totFont:  { name: 'Arial', bold: true,  size: 10 },
    totFill:  { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD6E4F7' } },
    nrmFont:  { name: 'Arial', size: 10 },
    ttlFont:  { name: 'Arial', bold: true,  size: 11, color: { argb: 'FF1A56A0' } },
    fillEven: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF0F5FC' } },
    fillOdd:  { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFFFFF' } },
    thin:     { style: 'thin', color: { argb: 'FFBFBFBF' } },
    money:    '#,##0.00',
    ctr:      { horizontal: 'center', vertical: 'middle' },
    lft:      { horizontal: 'left',   vertical: 'middle' },
    rgt:      { horizontal: 'right',  vertical: 'middle' },
};

function _border() {
    const t = EXCEL_STYLES.thin;
    return { left: t, right: t, top: t, bottom: t };
}

function _fill(i) {
    return i % 2 === 0 ? EXCEL_STYLES.fillEven : EXCEL_STYLES.fillOdd;
}

function _hdrRow(ws, headers, fillStyle) {
    const row = ws.addRow(headers);
    row.height = 16;
    row.eachCell(cell => {
        cell.font      = EXCEL_STYLES.hdrFont;
        cell.fill      = fillStyle || EXCEL_STYLES.hdrFill;
        cell.alignment = EXCEL_STYLES.ctr;
        cell.border    = _border();
    });
}

function _dataRow(ws, values, rowIndex, moneyColNums, centerColNums) {
    const row = ws.addRow(values);
    const fill = _fill(rowIndex);
    row.eachCell({ includeEmpty: true }, (cell, colNum) => {
        cell.font   = EXCEL_STYLES.nrmFont;
        cell.fill   = fill;
        cell.border = _border();
        if (moneyColNums.has(colNum)) {
            cell.numberFormat = EXCEL_STYLES.money;
            cell.alignment    = EXCEL_STYLES.rgt;
        } else if (centerColNums.has(colNum)) {
            cell.alignment = EXCEL_STYLES.ctr;
        } else {
            cell.alignment = EXCEL_STYLES.lft;
        }
    });
}

function _totRow(ws, values, moneyColNums) {
    const row = ws.addRow(values);
    row.eachCell({ includeEmpty: true }, (cell, colNum) => {
        cell.font   = EXCEL_STYLES.totFont;
        cell.fill   = EXCEL_STYLES.totFill;
        cell.border = _border();
        if (moneyColNums.has(colNum)) {
            cell.numberFormat = EXCEL_STYLES.money;
            cell.alignment    = EXCEL_STYLES.rgt;
        } else {
            cell.alignment = EXCEL_STYLES.lft;
        }
    });
}

/**
 * Generate full Recebidas Excel workbook.
 * @param {Array} rows - parsed note objects from parser.js
 * @param {string} companyName
 * @param {string} month - e.g. "05-2026"
 * @returns {Promise<ArrayBuffer>}
 */
async function generateRecebidas(rows, companyName, month) {
    const wb = new ExcelJS.Workbook();
    const now = new Date().toLocaleString('pt-BR');

    const fedRows    = rows.filter(r => r.isFederal);
    const munRows    = rows.filter(r => r.isMunicipal);
    const cancelRows = rows.filter(r => r.cancelada);

    // ── Sheet 1: NFS-e (all notes) ──────────────────────────────────────
    const ws1 = wb.addWorksheet('NFS-e');
    ws1.mergeCells('A1:W1');
    ws1.getCell('A1').value     = companyName;
    ws1.getCell('A1').font      = EXCEL_STYLES.ttlFont;
    ws1.getCell('A1').alignment = EXCEL_STYLES.lft;
    ws1.getRow(1).height        = 20;

    ws1.mergeCells('A2:W2');
    ws1.getCell('A2').value     = `Notas Recebidas — ${month}   Gerado em: ${now}`;
    ws1.getCell('A2').font      = { name: 'Arial', size: 9, color: { argb: 'FF7F8C8D' } };
    ws1.getCell('A2').alignment = EXCEL_STYLES.lft;

    const cols1 = [
        'Nr NFSe','Local Prest','Emissao','CNPJ Emitente','Razao Emitente',
        'CNPJ Tomador','Razao Tomador','NBS','Desc NBS','Cod Trib','Desc Trib',
        'Desc Servico','Vl Servico','ISS Valor','ISS Ret',
        'Pis Ret','Cofins Ret','IR Ret','CSLL Ret','INSS Ret',
        'CBS','IBS','Vl Liquido','Observacao'
    ];
    _hdrRow(ws1, cols1);

    // col numbers (1-based) that are money / center
    const money1  = new Set([13,14,15,16,17,18,19,20,21,22,23]);
    const center1 = new Set([1,2,3]);

    rows.forEach((r, i) => {
        const obs = r.cancelada ? 'CANCELADA' : '';
        _dataRow(ws1, [
            r.numero, r.xLocEmi, r.emissao, r.cnpjEmit, r.nomeEmit,
            r.cnpjToma, r.nomeToma, r.cNBS, r.xNBS, r.cTribNac, r.xTribNac,
            r.xDescServ, r.vServ, r.vISSQN, r.issRet,
            r.vPis, r.vCofins, r.vRetIRRF, r.vRetCSLL, r.inssVal,
            r.vCBS, r.vIBS, r.vLiq, obs
        ], i, money1, center1);
    });

    const sum1 = (key) => rows.reduce((a, r) => a + (r[key] || 0), 0);
    _totRow(ws1, [
        'TOTAIS','','','','','','','','','','','',
        sum1('vServ'), sum1('vISSQN'), sum1('issRet'),
        sum1('vPis'), sum1('vCofins'), sum1('vRetIRRF'), sum1('vRetCSLL'), sum1('inssVal'),
        sum1('vCBS'), sum1('vIBS'), sum1('vLiq'), ''
    ], money1);

    ws1.getColumn('A').width = 12;
    ws1.getColumn('D').width = 22;
    ws1.getColumn('E').width = 40;
    ws1.getColumn('G').width = 40;
    ws1.getColumn('K').width = 50;
    ws1.getColumn('L').width = 50;
    ws1.views = [{ state: "frozen", ySplit: 3 }];

    // ── Sheet 2: Retencao Federal ────────────────────────────────────────
    const ws2 = wb.addWorksheet('Retencao Federal');
    const cols2 = [
        'Nr NFSe','Emissao','CNPJ Emitente','Razao Emitente',
        'Vl Servico','ISS Ret','Pis Ret','Cofins Ret',
        'IR Ret','CSLL Ret','INSS Ret','CBS','IBS','Total Retido'
    ];
    _hdrRow(ws2, cols2);
    const money2  = new Set([5,6,7,8,9,10,11,12,13,14]);
    const center2 = new Set([1,2]);

    fedRows.forEach((r, i) => {
        _dataRow(ws2, [
            r.numero, r.emissao, r.cnpjEmit, r.nomeEmit,
            r.vServ, r.issRet, r.pisCofinsRet > 0 ? r.vPis : 0, r.pisCofinsRet > 0 ? r.vCofins : 0,
            r.vRetIRRF, r.vRetCSLL, r.inssVal, r.vCBS, r.vIBS, r.totalRet
        ], i, money2, center2);
    });

    const sum2 = (key) => fedRows.reduce((a, r) => a + (r[key] || 0), 0);
    _totRow(ws2, [
        'TOTAIS','','','',
        sum2('vServ'), sum2('issRet'), sum2('vPis'), sum2('vCofins'),
        sum2('vRetIRRF'), sum2('vRetCSLL'), sum2('inssVal'), sum2('vCBS'), sum2('vIBS'), sum2('totalRet')
    ], money2);

    ws2.getColumn('C').width = 22;
    ws2.getColumn('D').width = 40;
    ws2.views = [{ state: "frozen", ySplit: 1 }];

    // ── Sheet 3: Retencao Municipal ──────────────────────────────────────
    const ws3 = wb.addWorksheet('Retencao Municipal');
    _hdrRow(ws3, cols2, EXCEL_STYLES.hdrFillG);

    munRows.forEach((r, i) => {
        _dataRow(ws3, [
            r.numero, r.emissao, r.cnpjEmit, r.nomeEmit,
            r.vServ, r.issRet, 0, 0, 0, 0, 0, r.vCBS, r.vIBS, r.issRet
        ], i, money2, center2);
    });

    const sum3 = (key) => munRows.reduce((a, r) => a + (r[key] || 0), 0);
    _totRow(ws3, [
        'TOTAIS','','','',
        sum3('vServ'), sum3('issRet'), 0, 0, 0, 0, 0, sum3('vCBS'), sum3('vIBS'), sum3('issRet')
    ], money2);

    ws3.getColumn('C').width = 22;
    ws3.getColumn('D').width = 40;
    ws3.views = [{ state: "frozen", ySplit: 1 }];

    // ── Sheet 4: Resumo por Servico ──────────────────────────────────────
    const ws4 = wb.addWorksheet('Resumo por Servico');
    const cols4 = [
        'Cod Trib','Desc Trib','Qtd Notas','Vl Total Servicos',
        'ISS Total','ISS Ret Total','Pis Ret','Cofins Ret',
        'IR Ret','CSLL Ret','INSS Ret','Vl Liquido Total'
    ];
    _hdrRow(ws4, cols4);
    const money4  = new Set([4,5,6,7,8,9,10,11,12]);
    const center4 = new Set([1,3]);

    const groups = {};
    rows.forEach(r => {
        const k = r.cTribNac || 'N/A';
        if (!groups[k]) groups[k] = { desc: r.xTribNac, count: 0, vServ: 0, iss: 0, issRet: 0, pis: 0, cofins: 0, ir: 0, csll: 0, inss: 0, vLiq: 0 };
        const g = groups[k];
        g.count++; g.vServ += r.vServ; g.iss += r.vISSQN; g.issRet += r.issRet;
        g.pis += r.pisCofinsRet > 0 ? r.vPis : 0;
        g.cofins += r.pisCofinsRet > 0 ? r.vCofins : 0;
        g.ir += r.vRetIRRF; g.csll += r.vRetCSLL; g.inss += r.inssVal; g.vLiq += r.vLiq;
    });

    Object.entries(groups).forEach(([k, g], i) => {
        _dataRow(ws4, [
            k, g.desc, g.count, g.vServ, g.iss, g.issRet,
            g.pis, g.cofins, g.ir, g.csll, g.inss, g.vLiq
        ], i, money4, center4);
    });

    ws4.getColumn('B').width = 60;
    ws4.views = [{ state: "frozen", ySplit: 1 }];

    // ── Sheet 5: Notas Canceladas ────────────────────────────────────────
    const ws5 = wb.addWorksheet('Notas Canceladas');
    _hdrRow(ws5, cols1, EXCEL_STYLES.hdrFillR);

    cancelRows.forEach((r, i) => {
        _dataRow(ws5, [
            r.numero, r.xLocEmi, r.emissao, r.cnpjEmit, r.nomeEmit,
            r.cnpjToma, r.nomeToma, r.cNBS, r.xNBS, r.cTribNac, r.xTribNac,
            r.xDescServ, r.vServ, r.vISSQN, r.issRet,
            r.vPis, r.vCofins, r.vRetIRRF, r.vRetCSLL, r.inssVal,
            r.vCBS, r.vIBS, r.vLiq, 'CANCELADA'
        ], i, money1, center1);
    });

    ws5.getColumn('D').width = 22;
    ws5.getColumn('E').width = 40;
    ws5.views = [{ state: "frozen", ySplit: 1 }];

    return wb.xlsx.writeBuffer();
}

/**
 * Generate Emitidas Excel workbook.
 * @param {Array} rows - parsed note objects
 * @param {string} companyName
 * @param {string} month
 * @returns {Promise<ArrayBuffer>}
 */
async function generateEmitidas(rows, companyName, month) {
    const wb  = new ExcelJS.Workbook();
    const now = new Date().toLocaleString('pt-BR');

    const ws = wb.addWorksheet('Emitidas');
    ws.mergeCells('A1:G1');
    ws.getCell('A1').value     = `${companyName} — Notas Emitidas ${month}`;
    ws.getCell('A1').font      = EXCEL_STYLES.ttlFont;
    ws.getCell('A1').alignment = EXCEL_STYLES.lft;
    ws.getRow(1).height        = 20;

    ws.mergeCells('A2:G2');
    ws.getCell('A2').value = `Gerado em: ${now}`;
    ws.getCell('A2').font  = { name: 'Arial', size: 9, color: { argb: 'FF7F8C8D' } };

    const cols = ['Nr NFSe','Emissao','CNPJ Tomador','Razao Tomador','Vl Servico','ISS Valor','Observacao'];
    _hdrRow(ws, cols);

    const money  = new Set([5, 6]);
    const center = new Set([1, 2]);

    rows.forEach((r, i) => {
        const obs = r.cancelada ? 'CANCELADA' : '';
        _dataRow(ws, [
            r.numero, r.emissao, r.cnpjToma, r.nomeToma, r.vServ, r.vISSQN, obs
        ], i, money, center);
    });

    const sumE = (key) => rows.reduce((a, r) => a + (r[key] || 0), 0);
    _totRow(ws, ['TOTAIS','','','', sumE('vServ'), sumE('vISSQN'), ''], money);

    ws.getColumn('C').width = 22;
    ws.getColumn('D').width = 40;
    ws.views = [{ state: "frozen", ySplit: 3 }];

    return wb.xlsx.writeBuffer();
}
