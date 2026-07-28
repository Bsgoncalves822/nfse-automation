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
import shutil
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
    s = s.strip()
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})\s+[Ã a]s\s+(\d{2}:\d{2}:\d{2})([\-+]\d{2}:\d{2})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}{m.group(5)}"
    m2 = re.match(r'(\d{2})/(\d{2})/(\d{4})', s)
    if m2:
        return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}T00:00:00-03:00"
    return s


def _nota_filename(nota):
    """Return a clean filename for the nota using its number."""
    chave = nota.get('chave', '')
    if len(chave) == 50 and chave[28:36].isdigit():
        n_nfse = str(int(chave[28:36]))
    else:
        n_nfse = str(nota.get('numero', chave or 'unknown'))
    # include emitente CNPJ digits to avoid collisions across prestadores
    cnpj = re.sub(r'\D', '', nota.get('emit_cnpj', ''))
    return f'NFSe_{n_nfse}_{cnpj}.xml' if cnpj else f'NFSe_{n_nfse}.xml'


def reconstruct_xml(nota):
    cnpj_emit = _clean_cnpj(nota.get('emit_cnpj', ''))
    cnpj_toma = _clean_cnpj(nota.get('toma_cnpj', ''))

    mun = nota.get('mun_incidencia', 'Tubarao/SC')
    uf = mun.split('/')[-1].strip() if '/' in mun else 'SC'
    cidade = mun.split('/')[0].strip() if '/' in mun else mun

    dh_emi = _parse_date(nota.get('data_emissao', ''))

    v_inss = nota.get('v_inss', 0.0)
    v_ret_inss = _fmt_float(v_inss)
    v_ret_cp   = '0.00'

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
    if federal_only:
        target  = [n for n in notas if n.get('is_federal') and not n.get('is_cancelada')]
        xml_dir = os.path.join(download_dir, 'federal', 'xmls')
    else:
        target  = [n for n in notas if not n.get('is_cancelada')]
        xml_dir = os.path.join(download_dir, 'all', 'xmls')

    # wipe old XMLs from previous runs before writing
    if os.path.exists(xml_dir):
        shutil.rmtree(xml_dir)
    os.makedirs(xml_dir, exist_ok=True)

    saved = []
    for nota in target:
        filename = _nota_filename(nota)
        out_path = os.path.join(xml_dir, filename)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(reconstruct_xml(nota))
        saved.append(out_path)

    print(f'[OK] {len(saved)} XMLs reconstruidos em {xml_dir}', flush=True)
    return saved