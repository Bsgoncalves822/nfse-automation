import os
import re
import time
import shutil
from datetime import datetime
from collections import defaultdict
import xml.etree.ElementTree as ET
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"
NS = {"nfse": "http://www.sped.fazenda.gov.br/nfse"}

def get_text(root, path):
    el = root.find(path, NS)
    return el.text.strip() if el is not None and el.text else ""

def get_float(root, path):
    val = get_text(root, path)
    try:
        return float(val.replace(",", "."))
    except:
        return 0.0

def parse_xml_full(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        n_nfse       = get_text(root, ".//nfse:nNFSe")
        x_loc_emi    = get_text(root, ".//nfse:xLocEmi")
        x_loc_prest  = get_text(root, ".//nfse:xLocPrestacao") or x_loc_emi
        dh_emi       = get_text(root, ".//nfse:dhEmi")
        x_trib_nac   = get_text(root, ".//nfse:xTribNac")
        c_trib_nac   = get_text(root, ".//nfse:cTribNac")
        x_desc_serv  = get_text(root, ".//nfse:xDescServ")
        c_stat       = get_text(root, ".//nfse:cStat")
        cnpj_emit    = get_text(root, ".//nfse:emit/nfse:CNPJ") or get_text(root, ".//nfse:prest/nfse:CNPJ")
        nome_emit    = get_text(root, ".//nfse:emit/nfse:xNome") or get_text(root, ".//nfse:prest/nfse:xNome")
        cnpj_toma    = get_text(root, ".//nfse:toma/nfse:CNPJ")
        nome_toma    = get_text(root, ".//nfse:toma/nfse:xNome")
        cnpj_clean   = "".join(filter(str.isdigit, cnpj_emit))
        if len(cnpj_clean) == 14:
            cnpj_fmt = f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}.{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:]}"
        elif len(cnpj_clean) == 11:
            cnpj_fmt = f"{cnpj_clean[:3]}.{cnpj_clean[3:6]}.{cnpj_clean[6:9]}-{cnpj_clean[9:]}"
        else:
            cnpj_fmt = cnpj_emit
        cnpj_tc = "".join(filter(str.isdigit, cnpj_toma))
        cnpj_toma_fmt = f"{cnpj_tc[:2]}.{cnpj_tc[2:5]}.{cnpj_tc[5:8]}/{cnpj_tc[8:12]}-{cnpj_tc[12:]}" if len(cnpj_tc)==14 else cnpj_toma
        try:
            dt = datetime.fromisoformat(dh_emi[:19])
            data_fmt = dt.strftime("%d/%m/%Y")
        except:
            data_fmt = dh_emi[:10]
        v_serv     = get_float(root, ".//nfse:vServ") or get_float(root, ".//nfse:vLiq")
        v_ret_irrf = get_float(root, ".//nfse:vRetIRRF")
        v_ret_csll = get_float(root, ".//nfse:vRetCSLL")
        v_pis      = get_float(root, ".//nfse:vPis")
        v_cofins   = get_float(root, ".//nfse:vCofins")
        v_ret_inss = get_float(root, ".//nfse:vRetINSS")
        v_ret_cp   = get_float(root, ".//nfse:vRetCP")
        v_issqn    = get_float(root, ".//nfse:vISSQN")
        tp_ret_iss = get_text(root, ".//nfse:tpRetISSQN")
        iss_ret    = v_issqn if tp_ret_iss == "1" else 0.0
        inss_val   = v_ret_cp if v_ret_cp > 0 else v_ret_inss
        total_ret  = v_ret_irrf + v_ret_csll + v_pis + v_cofins + inss_val
        v_liq      = get_float(root, ".//nfse:vLiq") or v_serv
        cancelada  = c_stat in ("107","108","109")
        is_fed     = total_ret > 0
        is_mun     = (not is_fed) and (tp_ret_iss == "1")
        return {
            "numero": n_nfse, "local_prest": x_loc_prest, "emissao": data_fmt,
            "cnpj_emit": cnpj_fmt, "nome_emit": nome_emit,
            "cnpj_toma": cnpj_toma_fmt, "nome_toma": nome_toma,
            "nbs": "", "desc_nbs": "",
            "cod_trib": c_trib_nac, "desc_trib": x_trib_nac[:90] if x_trib_nac else "",
            "desc_serv": x_desc_serv[:200] if x_desc_serv else "",
            "v_serv": v_serv, "iss_aliq": "", "iss_val": v_issqn, "iss_ret": iss_ret,
            "pis_ret": v_pis, "cofins_ret": v_cofins, "ir_ret": v_ret_irrf,
            "csll_ret": v_ret_csll, "inss_ret": inss_val, "total_ret": total_ret,
            "v_liq": v_liq, "is_federal": is_fed, "is_municipal": is_mun,
            "cancelada": cancelada, "obs": "CANCELADA - NFS-e cancelada" if cancelada else "",
        }
    except Exception as e:
        print(f"[AVISO] Erro ao parsear {xml_path}: {e}", flush=True)
        return None

def is_federal(xml_path):
    try:
        tree = ET.parse(xml_path); root = tree.getroot()
        for f in [".//nfse:vRetIRRF",".//nfse:vRetCSLL",".//nfse:vPis",".//nfse:vCofins",".//nfse:vRetINSS",".//nfse:vRetCP"]:
            el = root.find(f, NS)
            if el is not None and el.text:
                try:
                    if float(el.text) > 0: return True
                except: pass
        return False
    except: return False

def is_municipal(xml_path):
    try:
        tree = ET.parse(xml_path); root = tree.getroot()
        tp = root.find(".//nfse:tpRetISSQN", NS)
        return tp is not None and tp.text == "1"
    except: return False

def get_nnfse(xml_path):
    try:
        tree = ET.parse(xml_path); root = tree.getroot()
        el = root.find(".//nfse:nNFSe", NS)
        return str(el.text).strip() if el is not None and el.text else None
    except: return None

def generate_recebidas_excel(rows, company_name, month, download_dir):
    wb = Workbook()
    hdr_font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
    hdr_fill = PatternFill("solid", start_color="1A56A0")
    tot_font = Font(name="Arial", bold=True, size=10)
    tot_fill = PatternFill("solid", start_color="D6E4F7")
    nrm_font = Font(name="Arial", size=10)
    ttl_font = Font(name="Arial", bold=True, size=11, color="1A56A0")
    ctr = Alignment(horizontal="center", vertical="center")
    lft = Alignment(horizontal="left",   vertical="center")
    rgt = Alignment(horizontal="right",  vertical="center")
    thin = Side(style="thin", color="BFBFBF")
    bdr  = Border(left=thin, right=thin, top=thin, bottom=thin)
    money = "#,##0.00"
    ret_rows    = [r for r in rows if r["total_ret"] > 0 or r["iss_ret"] > 0]
    cancel_rows = [r for r in rows if r["cancelada"]]
    cols1 = ["Nr NFSe","Local Prest","Emissao","CNPJ/CPF Emitente","Razao Emitente",
             "CNPJ/CPF Tomador","Razao Tomador","NBS","Desc. NBS","Cod. Tributacao",
             "Descr. Tributacao","Descr. Servico","Vl. Servico","ISS","ISS Valor",
             "ISS Ret.","Pis Ret.","Cofins Ret.","IR Ret.","CSLL Ret.","INSS Retido",
             "Tipo Ret.","Vl. Liquido","Observacao"]
    money_cols = {13,15,16,17,18,19,20,21,23}
    ws1 = wb.active
    ws1.title = "NFS-e"
    ws1.merge_cells("A1:X1")
    ws1["A1"] = company_name
    ws1["A1"].font = ttl_font; ws1["A1"].alignment = lft
    ws1.merge_cells("A2:X2")
    ws1["A2"] = f"Relatorio de Notas Recebidas   Gerado em: {datetime.now().strftime('%d/%m/%Y as %H:%M:%S')}"
    ws1["A2"].font = Font(name="Arial", size=9, color="7F8C8D")
    for c, h in enumerate(cols1, 1):
        cell = ws1.cell(row=3, column=c, value=h)
        cell.font = hdr_font; cell.fill = hdr_fill; cell.alignment = ctr; cell.border = bdr
    for i, r in enumerate(rows, start=4):
        fill = PatternFill("solid", start_color="F0F5FC") if i%2==0 else PatternFill("solid", start_color="FFFFFF")
        vals = [r["numero"],r["local_prest"],r["emissao"],r["cnpj_emit"],r["nome_emit"],
                r["cnpj_toma"],r["nome_toma"],r["nbs"],r["desc_nbs"],r["cod_trib"],
                r["desc_trib"],r["desc_serv"],r["v_serv"],r["iss_aliq"],r["iss_val"],
                r["iss_ret"],r["pis_ret"],r["cofins_ret"],r["ir_ret"],r["csll_ret"],
                r["inss_ret"],"",r["v_liq"],r["obs"]]
        for c, v in enumerate(vals, 1):
            cell = ws1.cell(row=i, column=c, value=v)
            cell.font = nrm_font; cell.fill = fill; cell.border = bdr
            if c in money_cols: cell.number_format = money; cell.alignment = rgt
            elif c in {1,2,3}: cell.alignment = ctr
            else: cell.alignment = lft
    tr = len(rows)+4
    ws1.cell(row=tr, column=1, value="TOTAIS").font = tot_font
    ws1.cell(row=tr, column=1).fill = tot_fill
    ws1.cell(row=tr, column=1).alignment = lft
    ws1.cell(row=tr, column=1).border = bdr
    tot_map = {13:"v_serv",15:"iss_val",16:"iss_ret",17:"pis_ret",18:"cofins_ret",19:"ir_ret",20:"csll_ret",21:"inss_ret",23:"v_liq"}
    for c in range(2, len(cols1)+1):
        cell = ws1.cell(row=tr, column=c); cell.fill = tot_fill; cell.border = bdr
        if c in tot_map:
            cell.value = sum(r[tot_map[c]] for r in rows)
            cell.number_format = money; cell.alignment = rgt; cell.font = tot_font
    ws1.column_dimensions["A"].width = 15; ws1.column_dimensions["D"].width = 22
    ws1.column_dimensions["E"].width = 40; ws1.column_dimensions["K"].width = 50
    ws1.column_dimensions["L"].width = 50; ws1.freeze_panes = "A4"
    cols2 = ["Nr NFSe","Emissao","CNPJ/CPF Emitente","Razao Emitente",
             "Vl. Servico","ISS Ret.","Pis Ret.","Cofins Ret.",
             "IR Ret.","CSLL Ret.","INSS Ret.","Total Retido"]
    money_cols2 = {5,6,7,8,9,10,11,12}
    ws2 = wb.create_sheet("Impostos Retidos")
    for c, h in enumerate(cols2, 1):
        cell = ws2.cell(row=1, column=c, value=h)
        cell.font = hdr_font; cell.fill = hdr_fill; cell.alignment = ctr; cell.border = bdr
    for i, r in enumerate(ret_rows, start=2):
        fill = PatternFill("solid", start_color="F0F5FC") if i%2==0 else PatternFill("solid", start_color="FFFFFF")
        tot = r["total_ret"] + r["iss_ret"]
        vals = [r["numero"],r["emissao"],r["cnpj_emit"],r["nome_emit"],
                r["v_serv"],r["iss_ret"],r["pis_ret"],r["cofins_ret"],
                r["ir_ret"],r["csll_ret"],r["inss_ret"],tot]
        for c, v in enumerate(vals, 1):
            cell = ws2.cell(row=i, column=c, value=v)
            cell.font = nrm_font; cell.fill = fill; cell.border = bdr
            if c in money_cols2: cell.number_format = money; cell.alignment = rgt
            elif c in {1,2}: cell.alignment = ctr
            else: cell.alignment = lft
    tr2 = len(ret_rows)+2
    ws2.cell(row=tr2, column=1, value="TOTAIS").font = tot_font
    ws2.cell(row=tr2, column=1).fill = tot_fill
    ws2.cell(row=tr2, column=1).alignment = lft
    ws2.cell(row=tr2, column=1).border = bdr
    tot_map2 = {5:"v_serv",6:"iss_ret",7:"pis_ret",8:"cofins_ret",9:"ir_ret",10:"csll_ret",11:"inss_ret"}
    for c in range(2, len(cols2)+1):
        cell = ws2.cell(row=tr2, column=c); cell.fill = tot_fill; cell.border = bdr
        if c in tot_map2:
            cell.value = sum(r[tot_map2[c]] for r in ret_rows)
            cell.number_format = money; cell.alignment = rgt; cell.font = tot_font
        elif c == 12:
            cell.value = sum(r["total_ret"]+r["iss_ret"] for r in ret_rows)
            cell.number_format = money; cell.alignment = rgt; cell.font = tot_font
    ws2.column_dimensions["C"].width = 22; ws2.column_dimensions["D"].width = 40
    ws2.freeze_panes = "A2"
    ws3 = wb.create_sheet("Resumo por Servico")
    cols3 = ["Cod. Tributacao","Descr. Tributacao","Qtd. Notas","Vl. Total Servicos",
             "ISS Valor Total","ISS Ret. Total","Pis Ret. Total","Cofins Ret. Total",
             "IR Ret. Total","CSLL Ret. Total","INSS Ret. Total","Vl. Liquido Total"]
    for c, h in enumerate(cols3, 1):
        cell = ws3.cell(row=1, column=c, value=h)
        cell.font = hdr_font; cell.fill = hdr_fill; cell.alignment = ctr; cell.border = bdr
    groups = defaultdict(lambda: {"desc":"","count":0,"v_serv":0,"iss_val":0,"iss_ret":0,"pis":0,"cofins":0,"ir":0,"csll":0,"inss":0,"v_liq":0})
    for r in rows:
        k = r["cod_trib"] or "N/A"; g = groups[k]
        g["desc"] = r["desc_trib"]; g["count"] += 1; g["v_serv"] += r["v_serv"]
        g["iss_val"] += r["iss_val"]; g["iss_ret"] += r["iss_ret"]
        g["pis"] += r["pis_ret"]; g["cofins"] += r["cofins_ret"]
        g["ir"] += r["ir_ret"]; g["csll"] += r["csll_ret"]
        g["inss"] += r["inss_ret"]; g["v_liq"] += r["v_liq"]
    money_cols3 = {4,5,6,7,8,9,10,11,12}
    for i, (k, g) in enumerate(groups.items(), start=2):
        fill = PatternFill("solid", start_color="F0F5FC") if i%2==0 else PatternFill("solid", start_color="FFFFFF")
        vals = [k,g["desc"],g["count"],g["v_serv"],g["iss_val"],g["iss_ret"],g["pis"],g["cofins"],g["ir"],g["csll"],g["inss"],g["v_liq"]]
        for c, v in enumerate(vals, 1):
            cell = ws3.cell(row=i, column=c, value=v)
            cell.font = nrm_font; cell.fill = fill; cell.border = bdr
            if c in money_cols3: cell.number_format = money; cell.alignment = rgt
            else: cell.alignment = lft
    tr3 = len(groups)+2
    ws3.cell(row=tr3, column=1, value="TOTAIS GERAIS").font = tot_font
    ws3.cell(row=tr3, column=1).fill = tot_fill
    ws3.cell(row=tr3, column=1).alignment = lft
    ws3.cell(row=tr3, column=1).border = bdr
    for c in range(2, len(cols3)+1):
        cell = ws3.cell(row=tr3, column=c); cell.fill = tot_fill; cell.border = bdr
    ws3.column_dimensions["B"].width = 60; ws3.freeze_panes = "A2"
    ws4 = wb.create_sheet("Notas Canceladas")
    for c, h in enumerate(cols1, 1):
        cell = ws4.cell(row=1, column=c, value=h)
        cell.font = hdr_font; cell.fill = PatternFill("solid", start_color="C0392B")
        cell.alignment = ctr; cell.border = bdr
    for i, r in enumerate(cancel_rows, start=2):
        fill = PatternFill("solid", start_color="F0F5FC") if i%2==0 else PatternFill("solid", start_color="FFFFFF")
        vals = [r["numero"],r["local_prest"],r["emissao"],r["cnpj_emit"],r["nome_emit"],
                r["cnpj_toma"],r["nome_toma"],r["nbs"],r["desc_nbs"],r["cod_trib"],
                r["desc_trib"],r["desc_serv"],r["v_serv"],r["iss_aliq"],r["iss_val"],
                r["iss_ret"],r["pis_ret"],r["cofins_ret"],r["ir_ret"],r["csll_ret"],
                r["inss_ret"],"",r["v_liq"],r["obs"]]
        for c, v in enumerate(vals, 1):
            cell = ws4.cell(row=i, column=c, value=v)
            cell.font = nrm_font; cell.fill = fill; cell.border = bdr
            cell.alignment = ctr if c in {1,2,3} else lft
    ws4.freeze_panes = "A2"
    safe_name = company_name.replace("/","_").replace("\\","_").replace(":","_")
    out_path  = os.path.join(download_dir, f"Recebidas_NFS-e_{safe_name}_{month}.xlsx")
    wb.save(out_path)
    print(f"[OK] Planilha gerada: {out_path}", flush=True)
    return out_path

def wait_for_page_ready(page, retries=3, timeout=120000):
    for attempt in range(retries):
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
            content = page.content()
            if "502" in content or "Server Error" in content or "service is unavailable" in content.lower():
                print(f"[AVISO] Portal erro servidor (tentativa {attempt+1}/{retries})", flush=True)
                time.sleep(10)
                page.reload()
                continue
            return True
        except Exception as e:
            if attempt < retries - 1:
                print(f"[AVISO] Timeout pagina (tentativa {attempt+1}/{retries})", flush=True)
                time.sleep(5)
                try:
                    page.reload()
                except:
                    pass
            else:
                raise e
    return False

def scrape_page_rows(page):
    results = []
    rows = page.query_selector_all("tr[data-chave]")
    for row in rows:
        try:
            if "nfse-cancelada" in (row.get_attribute("class") or ""):
                continue
            xml_link = row.query_selector("a[href*='/Download/NFSe/']")
            pdf_link = row.query_selector("a[href*='/Download/DANFSe/']")
            if xml_link and pdf_link:
                chave = xml_link.get_attribute("href").split("/")[-1]
                results.append({
                    "chave":   chave,
                    "xml_url": f"https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/NFSe/{chave}",
                    "pdf_url": f"https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/DANFSe/{chave}",
                })
        except:
            continue
    return results

def get_download_urls(page):
    results = []
    base_url = page.url
    pg = 1
    while True:
        page_rows = scrape_page_rows(page)
        results.extend(page_rows)
        print(f"[OK] Pagina {pg}: {len(page_rows)} notas", flush=True)
        proxima = page.query_selector("a[data-original-title='Proxima']")
        ultima  = page.query_selector("a[data-original-title='Ultima']")
        if not proxima and not ultima:
            break
        pg += 1
        if "pg=" in base_url:
            next_url = re.sub(r"pg=\d+", f"pg={pg}", base_url)
        else:
            sep = "&" if "?" in base_url else "?"
            next_url = base_url + f"{sep}pg={pg}"
        page.goto(next_url)
        wait_for_page_ready(page)
        if pg > 50:
            print("[AVISO] Safety stop at page 50", flush=True)
            break
    print(f"[OK] {len(results)} notas mapeadas em {pg} pagina(s)", flush=True)
    return results

def request_download(page, url, save_path, referer, retries=5):
    headers = {
        "Referer": referer,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    }
    chave = url.split("/")[-1]
    for attempt in range(retries):
        try:
            response = page.request.get(url, headers=headers, timeout=120000)
            if response.status == 200:
                content = response.body()
                if len(content) < 100:
                    raise Exception(f"Resposta muito pequena ({len(content)} bytes)")
                if content[:5] in (b"<!DOC", b"<html", b"<HTML"):
                    raise Exception("Portal retornou HTML em vez do arquivo")
                with open(save_path, "wb") as f:
                    f.write(content)
                return True
            elif response.status == 403:
                print(f"[AVISO] 403 em {chave[:20]} (tentativa {attempt+1}/{retries})", flush=True)
                time.sleep(5)
            elif response.status == 429:
                print(f"[AVISO] Rate limit 429, aguardando 30s...", flush=True)
                time.sleep(30)
            else:
                print(f"[AVISO] HTTP {response.status} (tentativa {attempt+1}/{retries})", flush=True)
                time.sleep(5)
        except Exception as e:
            if attempt < retries - 1:
                print(f"[AVISO] Falha download (tentativa {attempt+1}/{retries}): {str(e)[:80]}", flush=True)
                time.sleep(8)
            else:
                print(f"[ERRO] Falha ao baixar {chave[:20]}: {e}", flush=True)
                return False
    return False

def download_files(page, download_urls, impostos_retidos, download_dir, company_name="", month=""):
    fed_xml_dir = os.path.join(download_dir, "federal", "xmls")
    fed_pdf_dir = os.path.join(download_dir, "federal", "pdfs")
    mun_xml_dir = os.path.join(download_dir, "municipal", "xmls")
    mun_pdf_dir = os.path.join(download_dir, "municipal", "pdfs")
    temp_dir    = os.path.join(download_dir, "temp")
    for d in [fed_xml_dir, fed_pdf_dir, mun_xml_dir, mun_pdf_dir, temp_dir]:
        os.makedirs(d, exist_ok=True)

    referer    = page.url
    all_parsed = []
    downloaded = federal_count = municipal_count = skipped = failed = 0
    total      = len(download_urls)

    for i, url_info in enumerate(download_urls, 1):
        chave    = url_info["chave"]
        temp_xml = os.path.join(temp_dir, f"{chave}.xml")
        print(f"[{i}/{total}] XML {chave[:20]}...", flush=True)

        if not request_download(page, url_info["xml_url"], temp_xml, referer):
            failed += 1
            continue

        data = parse_xml_full(temp_xml)
        if not data:
            failed += 1
            os.remove(temp_xml)
            continue

        all_parsed.append(data)

        if data["is_federal"]:
            xml_dir = fed_xml_dir; pdf_dir = fed_pdf_dir; category = "federal"
        elif data["is_municipal"]:
            xml_dir = mun_xml_dir; pdf_dir = mun_pdf_dir; category = "municipal"
        else:
            os.remove(temp_xml)
            skipped += 1
            continue

        final_xml = os.path.join(xml_dir, f"{chave}.xml")
        if os.path.exists(final_xml):
            os.remove(final_xml)
        os.rename(temp_xml, final_xml)

        temp_pdf = os.path.join(temp_dir, f"{chave}.pdf")
        pdf_ok   = request_download(page, url_info["pdf_url"], temp_pdf, referer)
        if pdf_ok:
            final_pdf = os.path.join(pdf_dir, f"{chave}.pdf")
            if os.path.exists(final_pdf):
                os.remove(final_pdf)
            os.rename(temp_pdf, final_pdf)
            print(f"[OK] {category.upper()} | Nota {data['numero']}", flush=True)
        else:
            print(f"[OK] {category.upper()} | Nota {data['numero']} (XML ok, PDF falhou)", flush=True)
            failed += 1

        downloaded += 1
        if data["is_federal"]:
            federal_count += 1
        else:
            municipal_count += 1
        time.sleep(0.3)

    shutil.rmtree(temp_dir, ignore_errors=True)

    if all_parsed and company_name and month:
        try:
            generate_recebidas_excel(all_parsed, company_name, month, download_dir)
        except Exception as e:
            print(f"[AVISO] Erro ao gerar planilha: {e}", flush=True)

    print(f"[OK] {downloaded} notas baixadas — {federal_count} federal, {municipal_count} municipal | {skipped} sem retencao ignoradas", flush=True)
    if failed > 0:
        print(f"[AVISO] {failed} falha(s)", flush=True)

def download_files_all(page, download_dir):
    notas_dir = os.path.join(download_dir, "notas")
    os.makedirs(notas_dir, exist_ok=True)
    print("[INFO] Modo completo — baixando todas as notas", flush=True)
    all_urls = get_download_urls(page)
    if not all_urls:
        print("[AVISO] Nenhuma nota encontrada", flush=True)
        return None
    referer    = page.url
    downloaded = failed = 0
    total      = len(all_urls)
    for i, url_info in enumerate(all_urls, 1):
        chave = url_info["chave"]
        print(f"[{i}/{total}] Nota {chave[:20]}...", flush=True)
        xml_ok = request_download(page, url_info["xml_url"], os.path.join(notas_dir, f"{chave}.xml"), referer)
        pdf_ok = request_download(page, url_info["pdf_url"], os.path.join(notas_dir, f"{chave}.pdf"), referer)
        if xml_ok or pdf_ok:
            downloaded += 1
        else:
            failed += 1
        time.sleep(0.3)
    print(f"[OK] {downloaded} notas baixadas | {failed} falha(s)", flush=True)
    return notas_dir if downloaded > 0 else None
