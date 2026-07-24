import re, os
from datetime import datetime

def _fmt_float(v): return f"{v:.2f}"
def _clean_cnpj(s): return re.sub(r'\D', '', s or '')

def _parse_date(s):
    if not s: return datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
    s = s.strip()
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})\s+.{1,3}\s+(\d{2}:\d{2}:\d{2})([\-+]\d{2}:\d{2})', s)
    if m: return f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}{m.group(5)}"
    m2 = re.match(r'(\d{2})/(\d{2})/(\d{4})', s)
    if m2: return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}T00:00:00-03:00"
    return s

def _parse_mun(mun_str):
    if not mun_str: return '', 'SC'
    if '/' in mun_str:
        parts = mun_str.rsplit('/', 1)
        return parts[0].strip(), parts[1].strip()
    return mun_str.strip(), 'SC'

def reconstruct_xml(nota):
    cnpj_emit = _clean_cnpj(nota.get('emit_cnpj', ''))
    cnpj_toma = _clean_cnpj(nota.get('toma_cnpj', ''))
    cidade, uf = _parse_mun(nota.get('mun_incidencia', ''))
    if not cidade: cidade = nota.get('municipio_servico', 'Tubarao')
    dh_emi = _parse_date(nota.get('data_emissao', ''))
    v_inss = nota.get('v_inss', 0.0)
    situacao = nota.get('situacao', '100 - NFS-e Gerada')
    c_stat   = situacao.split(' - ')[0].strip() if ' - ' in situacao else '100'
    v_pis    = nota.get('v_pis', 0.0)
    v_cofins = nota.get('v_cofins', 0.0)
    tp_ret_pis = '1' if (v_pis > 0 or v_cofins > 0) and nota.get('is_federal') else '0'
    tp_ret_iss = '1' if nota.get('is_municipal') else '0'
    chave = nota.get('chave', '')
    if len(chave) == 50 and chave[28:36].isdigit():
        n_nfse = str(int(chave[28:36]))
    else:
        n_nfse = nota.get('numero', '')
    ns = 'http://www.sped.fazenda.gov.br/nfse'
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<NFSe xmlns="{ns}">
  <infNFSe>
    <nNFSe>{n_nfse}</nNFSe>
    <cStat>{c_stat}</cStat>
    <xLocEmi>{cidade}</xLocEmi>
    <serie>{nota.get('serie', '1')}</serie>
    <dhEmi>{dh_emi}</dhEmi>
    <chNFSe>{chave}</chNFSe>
    <emit>
      <CNPJ>{cnpj_emit}</CNPJ>
      <xNome>{nota.get('emit_nome', '')}</xNome>
      <enderNac><UF>{uf}</UF><cMun></cMun></enderNac>
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
      <tpRetISSQN>{tp_ret_iss}</tpRetISSQN>
    </valores>
    <tribFed>
      <vRetIRRF>{_fmt_float(nota.get('v_irrf', 0.0))}</vRetIRRF>
      <vRetCSLL>{_fmt_float(nota.get('v_csll', 0.0))}</vRetCSLL>
      <vRetINSS>{_fmt_float(v_inss)}</vRetINSS>
      <vRetCP>0.00</vRetCP>
      <pisCofins>
        <tpRetPisCofins>{tp_ret_pis}</tpRetPisCofins>
        <vPis>{_fmt_float(v_pis)}</vPis>
        <vCofins>{_fmt_float(v_cofins)}</vCofins>
      </pisCofins>
    </tribFed>
  </infNFSe>
</NFSe>'''

def save_reconstructed_xmls(notas, download_dir, federal_only=True):
    if federal_only:
        target  = [n for n in notas if n.get('is_federal') and not n.get('is_cancelada')]
        xml_dir = os.path.join(download_dir, 'federal', 'xmls')
    else:
        target  = [n for n in notas if not n.get('is_cancelada')]
        xml_dir = os.path.join(download_dir, 'all', 'xmls')
    os.makedirs(xml_dir, exist_ok=True)
    saved = []
    for nota in target:
        chave    = nota.get('chave', nota.get('numero', 'unknown'))
        out_path = os.path.join(xml_dir, f'{chave}.xml')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(reconstruct_xml(nota))
        saved.append(out_path)
    print(f'[OK] {len(saved)} XMLs reconstruidos em {xml_dir}', flush=True)
    return saved