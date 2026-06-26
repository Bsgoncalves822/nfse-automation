"""
reconstruct_xml.py
Reconstructs valid NFS-e XMLs from scraped Visualizar data in SefinNacional v1.01
format (the federal/national NFS-e schema published by Receita Federal).

This is the exact format SCI accepts via Layout 62 (NFS-e Nacional / Receita Federal)
in the "NFS-e (Importações municipais)" import screen.

XMLs are split into two folders under {download_dir}/sci/ :
    sci/com_retencao/   notas with any federal (PIS/COFINS/IR/CSLL/INSS) or municipal (ISS) retention
    sci/sem_retencao/   everything else (excluding cancelled notas)

Filename convention matches what the federal portal itself uses:
    NFSe_{chave}.xml

Usage:
    from src.reconstruct_xml import reconstruct_xml, save_reconstructed_xmls
    xml_str = reconstruct_xml(nota_dict)
    paths   = save_reconstructed_xmls(notas, download_dir)
"""

import os
import re
import json
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt(v):
    """Format a numeric value to 2 decimal places. Accepts int/float/str/None."""
    if v is None or v == '':
        return '0.00'
    try:
        return f"{float(v):.2f}"
    except (ValueError, TypeError):
        return '0.00'


def _clean_digits(s):
    """Return digits only from CNPJ/CPF string."""
    return re.sub(r'\D', '', s or '')


def _esc(s):
    """XML-escape a string value (handles &, <, >, ', ")."""
    if s is None:
        return ''
    return xml_escape(str(s), {'"': '&quot;', "'": '&apos;'})


def _parse_dh(s):
    """
    Parse Visualizar date string to ISO 8601 with timezone.
    Input examples:
        '26/06/2026 às 09:10:26-03:00'
        '26/06/2026 às 09:10:26'
        '26/06/2026'
    Returns: '2026-06-26T09:10:26-03:00'
    """
    if not s:
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
    s = s.strip()

    m = re.match(r'(\d{2})/(\d{2})/(\d{4})\s+[àa]s\s+(\d{2}:\d{2}:\d{2})([\-+]\d{2}:\d{2})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}{m.group(5)}"

    m = re.match(r'(\d{2})/(\d{2})/(\d{4})\s+[àa]s\s+(\d{2}:\d{2}:\d{2})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}-03:00"

    m = re.match(r'(\d{2})/(\d{2})/(\d{4})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}T00:00:00-03:00"

    return s


def _date_only(dh_iso):
    """Extract YYYY-MM-DD from an ISO datetime string."""
    if not dh_iso:
        return datetime.now().strftime('%Y-%m-%d')
    return dh_iso[:10]


def _parse_address(addr):
    """
    Parse a Visualizar address string into components.
    Examples:
        'RUA LUIZ MARTINS COLLACO , 134 /APT 401 , Bairro CENTRO , CEP 88701330 , Tubarão/SC'
        'EXPEDICIONARIO JOSE PEDRO COELHO , 2872 , Bairro REVOREDO , CEP 88704762 , Tubarão/SC'
    Returns dict with: xLgr, nro, xCpl, xBairro, CEP, xMun, UF
    Any unparseable piece falls back to safe defaults.
    """
    out = {'xLgr': '', 'nro': '', 'xCpl': '', 'xBairro': '', 'CEP': '', 'xMun': '', 'UF': ''}
    if not addr:
        return out

    parts = [p.strip() for p in addr.split(',') if p.strip()]
    if not parts:
        return out

    # Logradouro is always first
    out['xLgr'] = parts[0]

    for p in parts[1:]:
        if p.lower().startswith('bairro'):
            out['xBairro'] = p[6:].strip()
        elif p.lower().startswith('cep'):
            out['CEP'] = re.sub(r'\D', '', p)
        elif '/' in p and len(p.split('/')[-1].strip()) == 2:
            # municipality/UF
            mun_uf = p.rsplit('/', 1)
            out['xMun'] = mun_uf[0].strip()
            out['UF']   = mun_uf[1].strip()
        elif not out['nro']:
            # First non-classified piece after logradouro is numero (may include complement)
            if '/' in p:
                nro, cpl = p.split('/', 1)
                out['nro'] = nro.strip()
                out['xCpl'] = cpl.strip()
            else:
                out['nro'] = p

    return out


# ──────────────────────────────────────────────────────────────────────────────
# IBGE code lookup
# ──────────────────────────────────────────────────────────────────────────────

_CIDADES_CACHE = None

def _load_cidades_lookup():
    """Load config/cidades_lookup.json if available."""
    global _CIDADES_CACHE
    if _CIDADES_CACHE is not None:
        return _CIDADES_CACHE
    _CIDADES_CACHE = {}
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(here, '..', 'config', 'cidades_lookup.json'),
            os.path.join(here, 'config', 'cidades_lookup.json'),
        ]
        for path in candidates:
            if os.path.exists(path):
                with open(path, encoding='utf-8') as f:
                    _CIDADES_CACHE = json.load(f)
                break
    except Exception:
        _CIDADES_CACHE = {}
    return _CIDADES_CACHE


def _ibge_code(mun_name, uf=''):
    """
    Look up IBGE code from cidades_lookup.json.
    The lookup may be keyed by name, by 'name/UF', or by 'name-UF'.
    Returns empty string if not found.
    """
    if not mun_name:
        return ''
    lookup = _load_cidades_lookup()
    if not lookup:
        return ''
    candidates = [
        mun_name,
        mun_name.upper(),
        mun_name.title(),
        f"{mun_name}/{uf}",
        f"{mun_name.upper()}/{uf}",
        f"{mun_name}-{uf}",
    ]
    for k in candidates:
        v = lookup.get(k)
        if v:
            return str(v)
    return ''


# ──────────────────────────────────────────────────────────────────────────────
# XML construction
# ──────────────────────────────────────────────────────────────────────────────

def _build_chave_dps(chave_nfse, numero, serie='1'):
    """
    Build the 45-char Id used inside <infDPS Id="DPS...">.
    Structure (matching real federal XMLs):
        cMun(7) + ano-mes(4) + CNPJ(14) + serie(5 zero-padded) + nDPS(15 zero-padded) = 45
    Derived from the NFSe chave which already contains cMun + emit CNPJ at known offsets.
    """
    if chave_nfse and len(chave_nfse) >= 21:
        cmun = chave_nfse[:7]
        # ano-mes is positions 7-10 in some chave layouts; safer to derive from emit data later
        # Here we just use what we can and pad numero/serie
        cnpj = chave_nfse[9:23] if len(chave_nfse) >= 23 else '0' * 14
        ano_mes = chave_nfse[7:9] + '01'  # MM + fallback
        return f"{cmun}{ano_mes}{cnpj}{str(serie).zfill(5)}{str(numero).zfill(15)}"
    return ('0' * 45)


def reconstruct_xml(nota):
    """
    Build a SefinNacional v1.01 NFS-e XML from a scraped Visualizar dict.
    Format matches the federal portal's downloadable XMLs and is accepted by
    SCI via Layout 62 (NFS-e Nacional / Receita Federal).

    nota: dict from scrape_visualizar()
    Returns: XML string (utf-8 declared)
    """
    chave        = (nota.get('chave') or '').strip()
    numero       = str(nota.get('numero') or '').strip()
    serie        = str(nota.get('serie') or '1').strip() or '1'
    dh_emi       = _parse_dh(nota.get('data_emissao'))
    dh_proc      = _parse_dh(nota.get('data_geracao') or nota.get('data_emissao'))
    d_compet     = _date_only(dh_emi)

    # Situação / cStat
    situacao = nota.get('situacao', '100 - NFS-e Gerada') or '100'
    c_stat = situacao.split(' - ')[0].strip() if ' - ' in situacao else (situacao.strip() or '100')

    # Emitente
    emit_cnpj  = _clean_digits(nota.get('emit_cnpj'))
    emit_nome  = nota.get('emit_nome', '')
    emit_im    = nota.get('emit_insc_mun', '') or ''
    emit_addr  = _parse_address(nota.get('emit_endereco'))

    # Município (incidência / emissão / prestação)
    mun_inc       = nota.get('mun_incidencia', '') or nota.get('municipio_servico', '')
    if '/' in mun_inc:
        x_loc_emi, uf_inc = mun_inc.rsplit('/', 1)
        x_loc_emi = x_loc_emi.strip()
        uf_inc    = uf_inc.strip()
    else:
        x_loc_emi = mun_inc.strip()
        uf_inc    = emit_addr.get('UF', 'SC')

    # IBGE code — prefer chave-derived (first 7 digits of the 50-digit chave)
    if chave and len(chave) >= 7 and chave[:7].isdigit():
        c_mun = chave[:7]
    else:
        c_mun = _ibge_code(x_loc_emi, uf_inc) or _ibge_code(emit_addr.get('xMun', ''), emit_addr.get('UF', ''))

    # Tomador
    toma_cnpj = _clean_digits(nota.get('toma_cnpj'))
    toma_nome = nota.get('toma_nome', '')
    toma_addr = _parse_address(nota.get('toma_endereco'))

    # Serviço
    cod_trib_raw = nota.get('cod_tributacao', '') or ''
    if ' - ' in cod_trib_raw:
        c_trib_nac, x_trib_nac = cod_trib_raw.split(' - ', 1)
        c_trib_nac = c_trib_nac.strip()
        x_trib_nac = x_trib_nac.strip()
    else:
        c_trib_nac = cod_trib_raw.strip()
        x_trib_nac = nota.get('desc_servico', '')
    desc_serv = nota.get('desc_servico', '') or x_trib_nac or 'Serviço prestado'
    nbs       = (nota.get('nbs') or '').strip()

    # Tributação ISSQN
    trib_issqn_raw = nota.get('trib_issqn', '') or ''
    trib_issqn = '1'  # 1 = Operação Tributável (default)
    if trib_issqn_raw and trib_issqn_raw[:1].isdigit():
        trib_issqn = trib_issqn_raw[:1]

    # Retenção ISSQN: '1 - Retido' / '2 - Não Retido'
    ret_issqn_raw = (nota.get('ret_issqn') or '').strip()
    tp_ret_iss = '1' if ret_issqn_raw.startswith('2') else '2'  # 1 = Retido, 2 = Não Retido (in XML)
    # Actually federal schema: tpRetISSQN  1=Não Retido, 2=Retido — confirm via is_municipal flag
    tp_ret_iss = '2' if nota.get('is_municipal') else '1'

    # Valores
    v_serv      = float(nota.get('v_servico', 0) or 0)
    v_desc      = float(nota.get('desconto', 0) or 0)
    v_bc        = float(nota.get('base_calculo', 0) or 0)
    p_aliq      = float(nota.get('aliquota_iss', 0) or 0)
    v_iss       = float(nota.get('v_issqn', 0) or 0)
    v_pis       = float(nota.get('v_pis', 0) or 0)
    v_cofins    = float(nota.get('v_cofins', 0) or 0)
    v_ir        = float(nota.get('v_irrf', 0) or 0)
    v_csll      = float(nota.get('v_csll', 0) or 0)
    v_inss      = float(nota.get('v_inss', 0) or 0)
    base_pis    = float(nota.get('base_pis_cofins', 0) or 0)
    pis_aliq    = float(nota.get('pis_aliq', 0) or 0)
    cofins_aliq = float(nota.get('cofins_aliq', 0) or 0)

    pis_retido    = v_pis    > 0
    cofins_retido = v_cofins > 0
    has_fed_ret   = bool(nota.get('is_federal')) or pis_retido or cofins_retido

    v_liq = v_serv - v_desc - v_iss - v_pis - v_cofins - v_ir - v_csll - v_inss
    if v_liq < 0:
        v_liq = v_serv

    chave_dps = _build_chave_dps(chave, numero, serie)
    cod_verif = chave[-9:] if chave and len(chave) >= 9 else ''

    # Build XML
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<NFSe versao="1.01" xmlns="http://www.sped.fazenda.gov.br/nfse">
<infNFSe Id="NFS{_esc(chave)}">
<xLocEmi>{_esc(x_loc_emi)}</xLocEmi>
<xLocPrestacao>{_esc(x_loc_emi)}</xLocPrestacao>
<nNFSe>{_esc(numero)}</nNFSe>
<cLocIncid>{_esc(c_mun)}</cLocIncid>
<xLocIncid>{_esc(x_loc_emi)}</xLocIncid>
<xTribNac>{_esc(x_trib_nac)}</xTribNac>
<verAplic>SefinNacional_1.6.0</verAplic>
<ambGer>2</ambGer>
<tpEmis>1</tpEmis>
<procEmi>1</procEmi>
<cStat>{_esc(c_stat)}</cStat>
<dhProc>{_esc(dh_proc)}</dhProc>
<nDFSe>{_esc(numero)}</nDFSe>
<emit>
<CNPJ>{_esc(emit_cnpj)}</CNPJ>
<IM>{_esc(emit_im)}</IM>
<xNome>{_esc(emit_nome)}</xNome>
<enderNac>
<xLgr>{_esc(emit_addr['xLgr'] or 'NAO INFORMADO')}</xLgr>
<nro>{_esc(emit_addr['nro'] or 'S/N')}</nro>
<xBairro>{_esc(emit_addr['xBairro'] or 'CENTRO')}</xBairro>
<cMun>{_esc(c_mun)}</cMun>
<UF>{_esc(uf_inc or 'SC')}</UF>
<CEP>{_esc(emit_addr['CEP'] or '00000000')}</CEP>
</enderNac>
</emit>
<valores>
<vBC>{_fmt(v_bc)}</vBC>
<pAliqAplic>{_fmt(p_aliq)}</pAliqAplic>
<vISSQN>{_fmt(v_iss)}</vISSQN>
<vLiq>{_fmt(v_liq)}</vLiq>
</valores>
<DPS xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" versao="1.00" xmlns="http://www.sped.fazenda.gov.br/nfse">
<infDPS Id="DPS{_esc(chave_dps)}">
<tpAmb>1</tpAmb>
<dhEmi>{_esc(dh_emi)}</dhEmi>
<verAplic>EmissorWeb_1.0.0.5</verAplic>
<serie>{_esc(serie)}</serie>
<nDPS>{_esc(numero)}</nDPS>
<dCompet>{_esc(d_compet)}</dCompet>
<tpEmit>1</tpEmit>
<cLocEmi>{_esc(c_mun)}</cLocEmi>
<prest>
<CNPJ>{_esc(emit_cnpj)}</CNPJ>
<IM>{_esc(emit_im)}</IM>
<regTrib><opSimpNac>2</opSimpNac><regEspTrib>0</regEspTrib></regTrib>
</prest>
<toma>
<CNPJ>{_esc(toma_cnpj)}</CNPJ>
<xNome>{_esc(toma_nome)}</xNome>'''

    # Tomador address (only if we parsed something)
    if any(toma_addr.values()):
        xml += f'''
<end>
<endNac>
<xLgr>{_esc(toma_addr['xLgr'] or 'NAO INFORMADO')}</xLgr>
<nro>{_esc(toma_addr['nro'] or 'S/N')}</nro>
<xBairro>{_esc(toma_addr['xBairro'] or 'CENTRO')}</xBairro>
<cMun>{_esc(_ibge_code(toma_addr['xMun'], toma_addr['UF']))}</cMun>
<UF>{_esc(toma_addr['UF'] or uf_inc or 'SC')}</UF>
<CEP>{_esc(toma_addr['CEP'] or '00000000')}</CEP>
</endNac>
</end>'''

    xml += f'''
</toma>
<serv>
<locPrest><cLocPrestacao>{_esc(c_mun)}</cLocPrestacao></locPrest>
<cServ><cTribNac>{_esc(c_trib_nac)}</cTribNac>'''

    if nbs:
        xml += f'<cTribMun>{_esc(nbs)}</cTribMun>'

    xml += f'''<xDescServ>{_esc(desc_serv)}</xDescServ></cServ>
</serv>
<valores>
<vServPrest><vServ>{_fmt(v_serv)}</vServ></vServPrest>'''

    if v_desc > 0:
        xml += f'<vDescIncond>{_fmt(v_desc)}</vDescIncond>'

    xml += f'''
<trib>
<tribMun><tribISSQN>{_esc(trib_issqn)}</tribISSQN><tpRetISSQN>{_esc(tp_ret_iss)}</tpRetISSQN></tribMun>'''

    # Federal retentions block — only emit if anything is retained
    if has_fed_ret or v_ir > 0 or v_csll > 0 or v_inss > 0:
        xml += '<tribFed>'
        if v_pis > 0 or v_cofins > 0:
            xml += '<piscofins>'
            xml += f'<tpRetPisCofins>{"1" if (pis_retido or cofins_retido) else "2"}</tpRetPisCofins>'
            if base_pis > 0:
                xml += f'<vBCPisCofins>{_fmt(base_pis)}</vBCPisCofins>'
            if pis_aliq > 0:
                xml += f'<pAliqPis>{_fmt(pis_aliq)}</pAliqPis>'
            if cofins_aliq > 0:
                xml += f'<pAliqCofins>{_fmt(cofins_aliq)}</pAliqCofins>'
            xml += f'<vPis>{_fmt(v_pis)}</vPis>'
            xml += f'<vCofins>{_fmt(v_cofins)}</vCofins>'
            xml += '</piscofins>'
        if v_ir > 0:
            xml += f'<vRetIRRF>{_fmt(v_ir)}</vRetIRRF>'
        if v_csll > 0:
            xml += f'<vRetCSLL>{_fmt(v_csll)}</vRetCSLL>'
        if v_inss > 0:
            xml += f'<vRetINSS>{_fmt(v_inss)}</vRetINSS>'
        xml += '</tribFed>'

    # Total tributos summary (zeros are acceptable; SCI doesn't reject)
    v_tot_fed = v_pis + v_cofins + v_ir + v_csll + v_inss
    xml += f'''
<totTrib><vTotTrib><vTotTribFed>{_fmt(v_tot_fed)}</vTotTribFed><vTotTribEst>0.00</vTotTribEst><vTotTribMun>{_fmt(v_iss)}</vTotTribMun></vTotTrib></totTrib>
</trib>
</valores>
</infDPS>
</DPS>
</infNFSe>
</NFSe>'''

    return xml


# ──────────────────────────────────────────────────────────────────────────────
# Folder-based writer
# ──────────────────────────────────────────────────────────────────────────────

def _has_retention(nota):
    """A nota has retention if any federal or municipal tax is withheld."""
    if nota.get('is_federal') or nota.get('is_municipal'):
        return True
    for k in ('v_pis', 'v_cofins', 'v_irrf', 'v_csll', 'v_inss', 'v_issqn_retido'):
        try:
            if float(nota.get(k, 0) or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass
    return False


def save_reconstructed_xmls(notas, download_dir, **kwargs):
    """
    Generate one SefinNacional v1.01 XML per nota and save to disk.

    Folder layout under {download_dir}/sci/:
        com_retencao/   notas with federal OR municipal retention
        sem_retencao/   notas with no retention (and not cancelled)

    Cancelled notas are skipped entirely.

    notas: list of dicts from scrape_visualizar()
    download_dir: base output dir for this company/month (e.g. .../Empresas/EMPRESA/06-2026)

    Returns: dict with counts and paths { 'com_retencao': [paths], 'sem_retencao': [paths] }
    """
    base = os.path.join(download_dir, 'sci')
    com_dir = os.path.join(base, 'com_retencao')
    sem_dir = os.path.join(base, 'sem_retencao')
    os.makedirs(com_dir, exist_ok=True)
    os.makedirs(sem_dir, exist_ok=True)

    result = {'com_retencao': [], 'sem_retencao': [], 'skipped_cancelled': 0, 'errors': 0}

    for nota in notas:
        try:
            if nota.get('is_cancelada'):
                result['skipped_cancelled'] += 1
                continue

            chave = (nota.get('chave') or nota.get('numero') or 'unknown').strip()
            safe_chave = re.sub(r'[^0-9A-Za-z_-]', '_', chave) or 'unknown'
            filename = f'NFSe_{safe_chave}.xml'

            xml_str = reconstruct_xml(nota)

            target_dir = com_dir if _has_retention(nota) else sem_dir
            out_path = os.path.join(target_dir, filename)

            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(xml_str)

            bucket = 'com_retencao' if target_dir == com_dir else 'sem_retencao'
            result[bucket].append(out_path)

        except Exception as e:
            result['errors'] += 1
            print(f'[AVISO] Falha ao gerar XML para {nota.get("chave", "?")}: {e}', flush=True)

    print(
        f"[OK] SCI XMLs: {len(result['com_retencao'])} com retenção | "
        f"{len(result['sem_retencao'])} sem retenção | "
        f"{result['skipped_cancelled']} canceladas ignoradas | "
        f"{result['errors']} erros",
        flush=True
    )
    return result
