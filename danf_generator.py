"""
danf_generator.py — Generate DANFs from reconstructed NFS-e XMLs using Playwright.
XML structure from reconstruct_xml.py:
  NFSe > infNFSe > [nNFSe, cStat, xLocEmi, serie, dhEmi, chNFSe,
                    emit > [CNPJ, xNome, enderNac > [UF, cMun]],
                    toma > [CNPJ, xNome],
                    serv > [xTribNac, xDescServ],
                    valores > [vServ, vBC, pAliq, vISSQN, tpRetISSQN,
                               tpRetPisCofins, vPis, vCofins,
                               vRetIRRF, vRetCSLL, vRetINSS, vRetCP]]
"""
import os, sys, json, re
from pathlib import Path
import xml.etree.ElementTree as ET

NS = 'http://www.sped.fazenda.gov.br/nfse'

def tag(t): return f'{{{NS}}}{t}'

def parse_xml(path):
    try:
        raw = open(path, encoding='utf-8', errors='replace').read()
        raw = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', raw)
        r = ET.fromstring(raw)
    except Exception as e:
        print(f'  [WARN] parse error {Path(path).name}: {e}')
        return None

    def gt(*tags):
        """Find tag with or without namespace."""
        for t in tags:
            # try namespaced first
            el = r.find(f'.//{tag(t)}')
            if el is not None and el.text:
                return el.text.strip()
            # try plain (no namespace)
            el = r.find(f'.//{t}')
            if el is not None and el.text:
                return el.text.strip()
        return ''

    def gf(*tags):
        v = gt(*tags)
        try: return float(v)
        except: return 0.0

    def find_el(parent, t):
        """Find element with or without namespace."""
        el = parent.find(tag(t))
        if el is not None: return el
        return parent.find(t)

    def fmt_cnpj(s):
        s = re.sub(r'\D', '', s or '')
        if len(s) == 14:
            return f'{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}'
        return s

    # Get emit/toma elements
    emit_el = r.find(f'.//{tag("emit")}') or r.find('.//emit')
    toma_el = r.find(f'.//{tag("toma")}') or r.find('.//toma')

    emit_cnpj = emit_nome = emit_uf = ''
    if emit_el is not None:
        c = find_el(emit_el, 'CNPJ')
        emit_cnpj = fmt_cnpj(c.text if c is not None and c.text else '')
        n = find_el(emit_el, 'xNome')
        emit_nome = n.text.strip() if n is not None and n.text else ''
        u = emit_el.find(f'.//{tag("UF")}') or emit_el.find('.//UF')
        emit_uf = u.text.strip() if u is not None and u.text else ''

    toma_cnpj = toma_nome = ''
    if toma_el is not None:
        c = find_el(toma_el, 'CNPJ')
        toma_cnpj = fmt_cnpj(c.text if c is not None and c.text else '')
        n = find_el(toma_el, 'xNome')
        toma_nome = n.text.strip() if n is not None and n.text else ''

    tp_ret_pc = gt('tpRetPisCofins')

    return {
        'n_nfse':      gt('nNFSe'),
        'c_stat':      gt('cStat'),
        'x_loc_emi':   gt('xLocEmi'),
        'serie':       gt('serie'),
        'dh_emi':      gt('dhEmi'),
        'ch_nfse':     gt('chNFSe'),
        'emit_cnpj':   emit_cnpj,
        'emit_nome':   emit_nome,
        'emit_uf':     emit_uf,
        'toma_cnpj':   toma_cnpj,
        'toma_nome':   toma_nome,
        'x_trib_nac':  gt('xTribNac'),
        'x_desc_serv': gt('xDescServ'),
        'v_serv':      gf('vServ'),
        'v_bc':        gf('vBC'),
        'p_aliq':      gf('pAliq'),
        'v_issqn':     gf('vISSQN'),
        'tp_ret_iss':  gt('tpRetISSQN'),
        'v_irrf':      gf('vRetIRRF'),
        'v_csll':      gf('vRetCSLL'),
        'v_inss':      gf('vRetINSS'),
        'v_pis':       gf('vPis') if tp_ret_pc == '1' else 0.0,
        'v_cofins':    gf('vCofins') if tp_ret_pc == '1' else 0.0,
    }

def fmt_money(v):
    try:
        return f'R$ {float(v):,.2f}'.replace(',','X').replace('.', ',').replace('X','.')
    except: return 'R$ 0,00'

def pct(v):
    try: return f'{float(v):.2f}%'
    except: return '0,00%'

def gerar_html(d):
    ret_rows = ''
    if d['v_irrf']:   ret_rows += f'<div class="total-item"><span class="label">IRRF Retido:</span><span class="value">{fmt_money(d["v_irrf"])}</span></div>'
    if d['v_csll']:   ret_rows += f'<div class="total-item"><span class="label">CSLL Retido:</span><span class="value">{fmt_money(d["v_csll"])}</span></div>'
    if d['v_inss']:   ret_rows += f'<div class="total-item"><span class="label">INSS Retido:</span><span class="value">{fmt_money(d["v_inss"])}</span></div>'
    if d['v_pis']:    ret_rows += f'<div class="total-item"><span class="label">PIS Retido:</span><span class="value">{fmt_money(d["v_pis"])}</span></div>'
    if d['v_cofins']: ret_rows += f'<div class="total-item"><span class="label">COFINS Retido:</span><span class="value">{fmt_money(d["v_cofins"])}</span></div>'

    iss_ret = 'Sim' if d['tp_ret_iss'] == '1' else 'Não'
    dh = d['dh_emi'][:10] if d['dh_emi'] else ''

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>DANF-e {d["n_nfse"]}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f0f0;padding:15px}}
.container{{max-width:1050px;margin:0 auto;background:white;padding:25px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,.1)}}
.header{{border-bottom:3px solid #003366;padding-bottom:12px;margin-bottom:15px;display:flex;justify-content:space-between;align-items:flex-start}}
.header h1{{color:#003366;font-size:22px}}
.header-sub{{font-size:11px;color:#666;margin-top:3px}}
.header-info{{text-align:right;font-size:11px;line-height:1.9}}
.section{{background:#f8f9fa;padding:12px;border-radius:4px;margin-bottom:12px;border-left:4px solid #003366}}
.section-tomador{{border-left-color:#28a745}}
.section-servico{{border-left-color:#17a2b8}}
.section-title{{font-weight:bold;color:#333;margin-bottom:8px;font-size:12px;text-transform:uppercase;letter-spacing:.5px}}
.row{{display:flex;margin-bottom:3px;font-size:11px}}
.label{{font-weight:bold;min-width:150px;color:#555}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
table{{width:100%;border-collapse:collapse;margin:10px 0;font-size:11px}}
th{{background:#003366;color:white;padding:7px;text-align:left}}
td{{padding:6px 8px;border-bottom:1px solid #dee2e6}}
tr:nth-child(even){{background:#f8f9fa}}
.totals{{display:grid;grid-template-columns:1fr 1fr;gap:15px;padding:12px;background:#f8f9fa;border-radius:4px;margin:12px 0}}
.total-item{{display:flex;justify-content:space-between;padding:3px 0;font-size:11px;border-bottom:1px solid #eee}}
.total-item .value{{color:#003366;font-weight:bold}}
.total-final{{grid-column:span 2;border-top:2px solid #003366;padding-top:10px;margin-top:8px;display:flex;justify-content:space-between;font-size:15px}}
.total-final .value{{color:#003366;font-weight:bold;font-size:17px}}
.chave{{font-size:9px;word-break:break-all;color:#666;margin-top:4px}}
.footer{{margin-top:20px;padding-top:12px;border-top:1px solid #dee2e6;font-size:10px;color:#6c757d;text-align:center}}
@media print{{body{{background:white}}.container{{box-shadow:none;padding:10px}}}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>DANF-e</h1>
      <div class="header-sub">Documento Auxiliar da Nota Fiscal de Serviços Eletrônica</div>
      <div class="header-sub">NFS-e Nacional — Receita Federal do Brasil</div>
    </div>
    <div class="header-info">
      <p><strong>NFS-e Nº:</strong> {d["n_nfse"]}</p>
      <p><strong>Série:</strong> {d["serie"]}</p>
      <p><strong>Data Emissão:</strong> {dh}</p>
      <p><strong>Status:</strong> {d["c_stat"]}</p>
      <div class="chave"><strong>Chave:</strong> {d["ch_nfse"]}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Prestador de Serviços</div>
    <div class="grid-2">
      <div>
        <div class="row"><span class="label">Razão Social:</span><span>{d["emit_nome"]}</span></div>
        <div class="row"><span class="label">CNPJ:</span><span>{d["emit_cnpj"]}</span></div>
      </div>
      <div>
        <div class="row"><span class="label">UF:</span><span>{d["emit_uf"]}</span></div>
        <div class="row"><span class="label">Município:</span><span>{d["x_loc_emi"]}</span></div>
      </div>
    </div>
  </div>

  <div class="section section-tomador">
    <div class="section-title">Tomador de Serviços</div>
    <div class="row"><span class="label">Nome/Razão Social:</span><span>{d["toma_nome"]}</span></div>
    <div class="row"><span class="label">CNPJ/CPF:</span><span>{d["toma_cnpj"]}</span></div>
  </div>

  <div class="section section-servico">
    <div class="section-title">Serviços Prestados</div>
    <div class="row"><span class="label">Natureza Trib.:</span><span style="font-size:10px">{d["x_trib_nac"][:100]}</span></div>
    <div class="row" style="margin-top:6px"><span class="label">Descrição:</span><span style="font-size:10px;white-space:pre-wrap">{d["x_desc_serv"]}</span></div>
  </div>

  <div class="totals">
    <div>
      <div class="total-item"><span class="label">Valor dos Serviços:</span><span class="value">{fmt_money(d["v_serv"])}</span></div>
      <div class="total-item"><span class="label">Base de Cálculo ISS:</span><span class="value">{fmt_money(d["v_bc"])}</span></div>
      <div class="total-item"><span class="label">Alíquota ISS:</span><span class="value">{pct(d["p_aliq"])}</span></div>
      <div class="total-item"><span class="label">Valor ISS:</span><span class="value">{fmt_money(d["v_issqn"])}</span></div>
      <div class="total-item"><span class="label">ISS Retido:</span><span class="value">{iss_ret}</span></div>
    </div>
    <div>
      {ret_rows if ret_rows else '<div class="total-item"><span class="label">Retenções Federais:</span><span class="value">Nenhuma</span></div>'}
    </div>
    <div class="total-final">
      <span class="label">VALOR LÍQUIDO:</span>
      <span class="value">{fmt_money(d["v_serv"] - d["v_issqn"] if d["tp_ret_iss"] == "1" else d["v_serv"])}</span>
    </div>
  </div>

  <div class="footer">
    Gerado automaticamente — ORPROCON Sistema de Automação NFS-e | NFS-e Nacional (nfse.gov.br)
  </div>
</div>
</body>
</html>'''

def generate_danf_all(downloads_path=None, month=None, filter_names=None):
    if downloads_path is None:
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'settings.json')
        with open(settings_path, encoding='utf-8') as f:
            downloads_path = json.load(f)['downloads_path']

    empresas_dir = Path(downloads_path) / 'Empresas'
    generated = 0
    errors = 0

    # Collect all jobs first
    jobs = []
    for company_dir in sorted(empresas_dir.iterdir()):
        if not company_dir.is_dir(): continue
        if filter_names and not any(n in company_dir.name for n in filter_names): continue
        month_dirs = [md for md in sorted(company_dir.iterdir())
                      if md.is_dir() and (month is None or md.name == month)]
        for month_dir in month_dirs:
            for subfolder in ['federal', 'all']:
                xml_dir  = month_dir / subfolder / 'xmls'
                danf_dir = month_dir / subfolder / 'danf'
                if not xml_dir.exists(): continue
                xml_files = list(xml_dir.glob('*.xml'))
                if not xml_files: continue
                danf_dir.mkdir(exist_ok=True)
                for xml_path in xml_files:
                    out_pdf = danf_dir / (xml_path.stem + '.pdf')
                    if not out_pdf.exists():
                        jobs.append((xml_path, out_pdf))

    print(f'[DANF] {len(jobs)} PDFs para gerar...', flush=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for xml_path, out_pdf in jobs:
            data = parse_xml(xml_path)
            if data:
                try:
                    html = gerar_html(data)
                    page.set_content(html, wait_until='domcontentloaded')
                    page.pdf(path=str(out_pdf), format='A4',
                             margin={'top':'10mm','bottom':'10mm','left':'10mm','right':'10mm'})
                    generated += 1
                    if generated % 50 == 0:
                        print(f'  {generated}/{len(jobs)} gerados...', flush=True)
                except Exception as e:
                    print(f'  [ERRO] {xml_path.name}: {e}')
                    errors += 1
        browser.close()

    print(f'[DANF] {generated} PDFs gerados | {errors} erros')
    return generated

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--downloads-path', default=None)
    ap.add_argument('--month', default=None)
    args = ap.parse_args()
    generate_danf_all(downloads_path=args.downloads_path, month=args.month)
