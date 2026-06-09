// parser.js — NFS-e XML classification
// Ported from Python src/downloader.py
// CRITICAL: Do not change classification rules without full audit.

'use strict';

/**
 * Get text content of first matching tag (namespace-agnostic).
 * Works correctly even when XML has namespaces like nfse:vRetIRRF
 */
function _getText(doc, tag) {
    // Try direct tag name first
    let els = doc.getElementsByTagName(tag);
    if (els.length > 0 && els[0].textContent) return els[0].textContent.trim();
    // Try with any namespace prefix by iterating all elements
    const all = doc.getElementsByTagName('*');
    for (let i = 0; i < all.length; i++) {
        const localName = all[i].localName || all[i].tagName.split(':').pop();
        if (localName === tag && all[i].textContent) {
            return all[i].textContent.trim();
        }
    }
    return '';
}

function _getFloat(doc, tag) {
    const val = _getText(doc, tag);
    const parsed = parseFloat(val.replace(',', '.'));
    return isNaN(parsed) ? 0.0 : parsed;
}

function _fmtCnpj(raw) {
    const digits = raw.replace(/\D/g, '');
    if (digits.length === 14) {
        return `${digits.slice(0,2)}.${digits.slice(2,5)}.${digits.slice(5,8)}/${digits.slice(8,12)}-${digits.slice(12)}`;
    } else if (digits.length === 11) {
        return `${digits.slice(0,3)}.${digits.slice(3,6)}.${digits.slice(6,9)}-${digits.slice(9)}`;
    }
    return raw;
}

function _fmtDate(dhEmi) {
    try {
        const dt = new Date(dhEmi.slice(0, 19));
        const d = String(dt.getDate()).padStart(2, '0');
        const m = String(dt.getMonth() + 1).padStart(2, '0');
        const y = dt.getFullYear();
        return `${d}/${m}/${y}`;
    } catch {
        return dhEmi.slice(0, 10);
    }
}

/**
 * Parse a Recebidas XML string.
 * Returns structured data + classification.
 *
 * Classification rules (must match Python is_federal exactly):
 *   is_federal = vRetIRRF > 0
 *             OR vRetCSLL > 0
 *             OR vRetINSS > 0
 *             OR vRetCP   > 0
 *             OR (tpRetPisCofins === '1' AND (vPis > 0 OR vCofins > 0))
 *
 *   is_municipal = !is_federal AND tpRetISSQN === '1'
 *
 *   cancelada = cStat !== '100' AND cStat !== ''
 *
 *   CBS (vCBSTot/vCBS) and IBS (vIBSTot) = reforma tributaria ISS replacements
 *   → present in data/Excel but DO NOT count toward is_federal
 */
function parseNfseXml(xmlString) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlString, 'application/xml');

    const parseError = doc.querySelector('parsererror');
    if (parseError) {
        console.error('[NFSE-EXT] XML parse error:', parseError.textContent.slice(0, 100));
        return null;
    }

    const nNFSe     = _getText(doc, 'nNFSe');
    const dhEmi     = _getText(doc, 'dhEmi');
    const cStat     = _getText(doc, 'cStat');
    const xLocEmi   = _getText(doc, 'xLocEmi');
    const xTribNac  = _getText(doc, 'xTribNac');
    const cTribNac  = _getText(doc, 'cTribNac');
    const xDescServ = _getText(doc, 'xDescServ');
    const cNBS      = _getText(doc, 'cNBS');
    const xNBS      = _getText(doc, 'xNBS');

    // Emitente: first CNPJ/xNome in doc
    const cnpjEmit = _getText(doc, 'CNPJ');
    const nomeEmit = _getText(doc, 'xNome');

    // Tomador: find <toma> element
    let cnpjToma = '', nomeToma = '';
    const all = doc.getElementsByTagName('*');
    for (let i = 0; i < all.length; i++) {
        const ln = all[i].localName || all[i].tagName.split(':').pop();
        if (ln === 'toma') {
            cnpjToma = _getText(all[i], 'CNPJ');
            nomeToma = _getText(all[i], 'xNome');
            break;
        }
    }

    // Retention values
    const vRetIRRF  = _getFloat(doc, 'vRetIRRF');
    const vRetCSLL  = _getFloat(doc, 'vRetCSLL');
    const vRetINSS  = _getFloat(doc, 'vRetINSS');
    const vRetCP    = _getFloat(doc, 'vRetCP');
    const vPis      = _getFloat(doc, 'vPis');
    const vCofins   = _getFloat(doc, 'vCofins');
    const tpRetPis  = _getText(doc, 'tpRetPisCofins');
    const vISSQN    = _getFloat(doc, 'vISSQN');
    const tpRetISS  = _getText(doc, 'tpRetISSQN');

    // CBS/IBS: reforma tributaria — NOT federal retention
    const vCBS = _getFloat(doc, 'vCBSTot') || _getFloat(doc, 'vCBS');
    const vIBS = _getFloat(doc, 'vIBSTot');

    // Effective values
    const pisCofinsRet = tpRetPis === '1' ? (vPis + vCofins) : 0.0;
    const inssVal      = vRetCP > 0 ? vRetCP : vRetINSS;
    const issRet       = tpRetISS === '1' ? vISSQN : 0.0;
    const totalRet     = vRetIRRF + vRetCSLL + pisCofinsRet + inssVal;
    const vServ        = _getFloat(doc, 'vServ') || _getFloat(doc, 'vLiq');
    const vLiq         = _getFloat(doc, 'vLiq') || vServ;

    // Classification
    const isFederal   = totalRet > 0;
    const isMunicipal = !isFederal && tpRetISS === '1';
    const cancelada   = cStat !== '100' && cStat !== '';

    return {
        numero:     nNFSe,
        emissao:    _fmtDate(dhEmi),
        cStat,
        cancelada,
        cnpjEmit:   _fmtCnpj(cnpjEmit),
        nomeEmit,
        cnpjToma:   _fmtCnpj(cnpjToma),
        nomeToma,
        xLocEmi,
        xTribNac:   xTribNac.slice(0, 90),
        cTribNac,
        xDescServ:  xDescServ.slice(0, 200),
        cNBS,
        xNBS,
        vServ,
        vISSQN,
        issRet,
        vPis,
        vCofins,
        tpRetPis,
        pisCofinsRet,
        vRetIRRF,
        vRetCSLL,
        inssVal,
        vCBS,
        vIBS,
        totalRet,
        vLiq,
        isFederal,
        isMunicipal,
    };
}

/**
 * Parse an Emitidas XML — same fields but tomador perspective.
 */
function parseNfseXmlEmitidas(xmlString) {
    // Emitidas uses same XML structure — reuse parseNfseXml
    // For emitidas we care about tomador (the client receiving the service)
    return parseNfseXml(xmlString);
}
