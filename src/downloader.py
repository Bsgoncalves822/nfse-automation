import os
import re
import time
import glob
import shutil
import xml.etree.ElementTree as ET

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"
NS = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}

def is_federal(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        federal_fields = [
            './/nfse:vRetIRRF',
            './/nfse:vRetCSLL',
            './/nfse:vPis',
            './/nfse:vCofins',
            './/nfse:vRetINSS',
            './/nfse:vRetCP',
        ]
        for field in federal_fields:
            el = root.find(field, NS)
            if el is not None and el.text:
                try:
                    if float(el.text) > 0:
                        return True
                except:
                    pass
        return False
    except Exception as e:
        print(f"[AVISO] Erro ao classificar XML {xml_path}: {e}")
        return False

def generate_excel(page, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    try:
        page.wait_for_selector("#generateExcelBtn", timeout=30000)
        page.wait_for_timeout(2000)
        with page.expect_download(timeout=600000) as download_info:
            page.click("#generateExcelBtn")
            try:
                page.wait_for_selector("#btnVerificar", timeout=10000)
                page.click("#btnVerificar")
            except:
                pass
        download = download_info.value
        for old in glob.glob(os.path.join(download_dir, "Recebidas_NFS-e_*.xlsx")):
            for _ in range(5):
                try:
                    os.remove(old)
                    break
                except:
                    time.sleep(1)
        save_path = os.path.join(download_dir, download.suggested_filename)
        download.save_as(save_path)
        print(f"[OK] Excel salvo: {save_path}")
        return save_path
    except Exception as e:
        print(f"[ERRO] Falha ao gerar Excel: {e}")
        return None

def scrape_page_urls(page):
    results = []
    rows = page.query_selector_all("tr.nfse-row, tr[data-chave]")
    for row in rows:
        try:
            if "nfse-cancelada" in (row.get_attribute("class") or ""):
                continue
            cnpj_el = row.query_selector(".cnpj")
            cnpj = cnpj_el.inner_text().strip() if cnpj_el else ""
            date_el = row.query_selector(".td-datahora")
            date_str = date_el.inner_text().strip()[:8] if date_el else ""
            xml_link = row.query_selector("a[href*='/Download/NFSe/']")
            pdf_link = row.query_selector("a[href*='/Download/DANFSe/']")
            if xml_link and pdf_link:
                results.append({
                    "cnpj": cnpj,
                    "date": date_str,
                    "xml_url": "https://www.nfse.gov.br" + xml_link.get_attribute("href"),
                    "pdf_url": "https://www.nfse.gov.br" + pdf_link.get_attribute("href"),
                })
        except:
            continue
    return results

def get_download_urls(page):
    results = []
    base_url = page.url
    pg = 1

    while True:
        page_urls = scrape_page_urls(page)
        results.extend(page_urls)
        print(f"[OK] Pagina {pg}: {len(page_urls)} linhas")

        proxima = page.query_selector("a[data-original-title='Pr\u00f3xima']")
        ultima = page.query_selector("a[data-original-title='\u00daltima']")
        if not proxima and not ultima:
            break

        pg += 1
        if "pg=" in base_url:
            next_url = re.sub(r"pg=\d+", f"pg={pg}", base_url)
        else:
            sep = "&" if "?" in base_url else "?"
            next_url = base_url + f"{sep}pg={pg}"

        page.goto(next_url)
        page.wait_for_load_state("networkidle", timeout=30000)

        if pg > 50:
            print("[AVISO] Safety stop at page 50")
            break

    print(f"[OK] {len(results)} URLs de download mapeadas em {pg} pagina(s)")
    return results

def download_files(page, download_urls, impostos_retidos, download_dir):
    fed_xml_dir = os.path.join(download_dir, "federal", "xmls")
    fed_pdf_dir = os.path.join(download_dir, "federal", "pdfs")
    mun_xml_dir = os.path.join(download_dir, "municipal", "xmls")
    mun_pdf_dir = os.path.join(download_dir, "municipal", "pdfs")
    temp_dir    = os.path.join(download_dir, "temp")

    for d in [fed_xml_dir, fed_pdf_dir, mun_xml_dir, mun_pdf_dir, temp_dir]:
        os.makedirs(d, exist_ok=True)

    retido_cnpjs = set(n["cnpj_emitente"] for n in impostos_retidos)
    downloaded = 0
    federal_count = 0
    municipal_count = 0

    for url_info in download_urls:
        if url_info["cnpj"] not in retido_cnpjs:
            continue

        chave = url_info["xml_url"].split("/")[-1]
        temp_xml = os.path.join(temp_dir, f"{chave}.xml")

        try:
            if os.path.exists(temp_xml):
                os.remove(temp_xml)

            with page.expect_download(timeout=60000) as dl:
                page.evaluate(f"window.location.href = '{url_info['xml_url']}'")
            f = dl.value
            f.save_as(temp_xml)
            time.sleep(1)

            federal = is_federal(temp_xml)
            xml_dir = fed_xml_dir if federal else mun_xml_dir
            pdf_dir = fed_pdf_dir if federal else mun_pdf_dir
            category = "federal" if federal else "municipal"

            final_xml = os.path.join(xml_dir, f"{chave}.xml")
            if os.path.exists(final_xml):
                os.remove(final_xml)
            os.rename(temp_xml, final_xml)

            page.goto("https://www.nfse.gov.br/EmissorNacional/Notas/Recebidas")
            page.wait_for_load_state("networkidle", timeout=60000)

            with page.expect_download(timeout=60000) as dl:
                page.evaluate(f"window.location.href = '{url_info['pdf_url']}'")
            f = dl.value
            final_pdf = os.path.join(pdf_dir, f.suggested_filename)
            if os.path.exists(final_pdf):
                os.remove(final_pdf)
            f.save_as(final_pdf)
            time.sleep(1)

            downloaded += 1
            if federal:
                federal_count += 1
            else:
                municipal_count += 1

            print(f"[OK] {category.upper()} | {url_info['cnpj']}")

        except Exception as e:
            print(f"[ERRO] Falha ao baixar {url_info['cnpj']}: {e}")
            if os.path.exists(temp_xml):
                os.remove(temp_xml)

    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"[OK] {downloaded} notas baixadas - {federal_count} federal, {municipal_count} municipal")

def download_files_all(page, download_dir):
    notas_dir = os.path.join(download_dir, "notas")
    os.makedirs(notas_dir, exist_ok=True)
    # remove old ZIPs from previous runs
    for old in glob.glob(os.path.join(notas_dir, "NFS-e_Todas_*.zip")):
        try:
            os.remove(old)
        except:
            pass
    try:
        with page.expect_download(timeout=600000) as dl:
            page.click("a:has-text('Baixar Tudo'), button:has-text('Baixar Tudo')")
            try:
                page.wait_for_selector("#btnVerificar", timeout=10000)
                page.click("#btnVerificar")
            except:
                pass
        download = dl.value
        save_path = os.path.join(notas_dir, download.suggested_filename)
        download.save_as(save_path)
        print(f"[OK] Baixar Tudo salvo: {save_path}")
        return save_path
    except Exception as e:
        print(f"[ERRO] Falha no Baixar Tudo: {e}")
        return None