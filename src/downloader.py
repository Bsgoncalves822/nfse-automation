import os
import re
import time

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"

def generate_excel(page, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    try:
        with page.expect_download(timeout=600000) as download_info:
            page.click("#generateExcelBtn")
            try:
                page.wait_for_selector("#btnVerificar", timeout=10000)
                page.click("#btnVerificar")
            except:
                pass
        download = download_info.value
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
    xml_dir = os.path.join(download_dir, "xmls")
    pdf_dir = os.path.join(download_dir, "pdfs")
    os.makedirs(xml_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    retido_cnpjs = set(n["cnpj_emitente"] for n in impostos_retidos)
    downloaded = 0
    for url_info in download_urls:
        if url_info["cnpj"] not in retido_cnpjs:
            continue
        try:
            with page.expect_download(timeout=60000) as dl:
                page.evaluate(f"window.location.href = '{url_info['xml_url']}'")
            f = dl.value
            f.save_as(os.path.join(xml_dir, f.suggested_filename))
            time.sleep(2)
            page.goto("https://www.nfse.gov.br/EmissorNacional/Notas/Recebidas")
            page.wait_for_load_state("networkidle", timeout=60000)
            with page.expect_download(timeout=60000) as dl:
                page.evaluate(f"window.location.href = '{url_info['pdf_url']}'")
            f = dl.value
            f.save_as(os.path.join(pdf_dir, f.suggested_filename))
            time.sleep(2)
            downloaded += 1
            print(f"[OK] Baixado: {url_info['cnpj']}")
        except Exception as e:
            print(f"[ERRO] Falha ao baixar {url_info['cnpj']}: {e}")
    print(f"[OK] {downloaded} notas baixadas")
