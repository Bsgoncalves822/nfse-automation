"""
reconstruct_xml.py
Reconstructs a minimal valid NFS-e XML from scraped Visualizar data.
Produces XMLs compatible with generate_fiscal.py and brazilfiscalreport.

Usage:
    from src.reconstruct_xml import reconstruct_xml
    xml_str = reconstruct_xml(nota_dict)
"""

import re
import os
from datetime import datetime


def _fmt_float(v):
    """Format float to 2 decimal places string."""
    return f"{v:.2f}"


def _clean_cnpj(s):
    """Return digits only from CNPJ/CPF string."""
    return re.sub(r'\D', '', s or '')


def _parse_date(s):
    """Parse date string from Visualizar page to ISO format."""
    if not s:
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
    # Format: "13/05/2026 às 03:36:40-03:00"
    s = s.strip()
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})\s+[àa]s\s+(\d{2}:\d{2}:\d{2})([\-+]\d{2}:\d{2})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}{m.group(5)}"
    # Format: "13/05/2026 às 03:36:40-03:00" without timezone
    m2 = re.match(r'(\d{2})/(\d{2})/(\d{4})', s)
    if m2:
        return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}T00:00:00-03:00"
    return s


def reconstruct_xml(nota):
    """
    Build a minimal NFS-e XML from a scraped Visualizar dict.
    Compatible with generate_fiscal.py parse_xml() function.
    
    nota: dict from scrape_visualizar()
    Returns: XML string
    """
    cnpj_emit = _clean_cnpj(nota.get('emit_cnpj', ''))
    cnpj_toma = _clean_cnpj(nota.get('toma_cnpj', ''))
    
    # Parse UF from municipality
    mun = nota.get('mun_incidencia', 'Tubarão/SC')
    uf = mun.split('/')[-1].strip() if '/' in mun else 'SC'
    cidade = mun.split('/')[0].strip() if '/' in mun else mun

    # Parse date
    dh_emi = _parse_date(nota.get('data_emissao', ''))
    
    # Format INSS - use vRetCP if aliq is 3.5%, else vRetINSS
    v_inss = nota.get('v_inss', 0.0)
    # We don't have aliquota INSS from scraper, default to vRetINSS
    v_ret_inss = _fmt_float(v_inss)
    v_ret_cp   = '0.00'

    # Situação - extract cStat
    situacao = nota.get('situacao', '100 - NFS-e Gerada')
    c_stat = situacao.split(' - ')[0].strip() if ' - ' in situacao else '100'

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe>
    <nNFSe>{nota.get('numero', '')}</nNFSe>
    <cStat>{c_stat}</cStat>
    <xLocEmi>{cidade}</xLocEmi>
    <serie>{nota.get('serie', '')}</serie>
    <dhEmi>{dh_emi}</dhEmi>
    <chNFSe>{nota.get('chave', '')}</chNFSe>
    <emit>
      <CNPJ>{cnpj_emit}</CNPJ>
      <xNome>{nota.get('emit_nome', '')}</xNome>
      <enderNac>
        <UF>{uf}</UF>
        <cMun></cMun>
      </enderNac>
    </emit>
    <toma>
      <CNPJ>{cnpj_toma}</CNPJ>
      <xNome>{nota.get('toma_nome', '')}</xNome>
    </toma>
    <serv>
      <xTribNac>{nota.get('cod_tributacao', '')}</xTribNac>
      <xDescServ>{nota.get('desc_servico', '')}</xDescServ>
    </serv>
    <valores>
      <vServ>{_fmt_float(nota.get('v_servico', 0.0))}</vServ>
      <vBC>{_fmt_float(nota.get('base_calculo', 0.0))}</vBC>
      <pAliq>{_fmt_float(nota.get('aliquota_iss', 0.0))}</pAliq>
      <vISSQN>{_fmt_float(nota.get('v_issqn', 0.0))}</vISSQN>
      <tpRetISSQN>{'1' if nota.get('is_municipal') else '0'}</tpRetISSQN>
      <tpRetPisCofins>{'1' if (nota.get('v_pis', 0) > 0 or nota.get('v_cofins', 0) > 0) and nota.get('is_federal') else '0'}</tpRetPisCofins>
      <vPis>{_fmt_float(nota.get('v_pis', 0.0))}</vPis>
      <vCofins>{_fmt_float(nota.get('v_cofins', 0.0))}</vCofins>
      <vRetIRRF>{_fmt_float(nota.get('v_irrf', 0.0))}</vRetIRRF>
      <vRetCSLL>{_fmt_float(nota.get('v_csll', 0.0))}</vRetCSLL>
      <vRetINSS>{v_ret_inss}</vRetINSS>
      <vRetCP>{v_ret_cp}</vRetCP>
    </valores>
  </infNFSe>
</NFSe>'''

    return xml


def save_reconstructed_xmls(notas, download_dir, federal_only=True):
    """
    Save reconstructed XMLs for notas with retention.
    
    notas: list of dicts from scrape_visualizar()
    download_dir: base output directory for this company/month
    federal_only: if True, only save federal retention notas
    
    Returns: list of saved XML paths
    """
    if federal_only:
        target = [n for n in notas if n.get('is_federal') and not n.get('is_cancelada')]
        xml_dir = os.path.join(download_dir, 'federal', 'xmls')
    else:
        target = [n for n in notas if not n.get('is_cancelada')]
        xml_dir = os.path.join(download_dir, 'all', 'xmls')

    os.makedirs(xml_dir, exist_ok=True)
    saved = []

    for nota in target:
        chave = nota.get('chave', nota.get('numero', 'unknown'))
        xml_str = reconstruct_xml(nota)
        out_path = os.path.join(xml_dir, f'{chave}.xml')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        saved.append(out_path)

    print(f'[OK] {len(saved)} XMLs reconstruidos em {xml_dir}', flush=True)
    return saved
