import os
import re
import time
import shutil
import xml.etree.ElementTree as ET

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"
NS = {"nfse": "http://www.sped.fazenda.gov.br/nfse"}

def is_federal(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for field in [".//nfse:vRetIRRF",".//nfse:vRetCSLL",".//nfse:vPis",".//nfse:vCofins",".//nfse:vRetINSS",".//nfse:vRetCP"]:
            el = root.find(field, NS)
            if el is not None and el.text:
                try:
                    if float(el.text) > 0:
                        return True
                except:
                    pass
        return False
    except Exception as e:
        print(f"[AVISO] Erro ao classificar XML {xml_path}: {e}", flush=True)
        return False

def get_nnfse(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        el = root.find(".//nfse:nNFSe", NS)
        if el is not None and el.text:
            return str(el.text).strip()
        return None
    except:
        return None

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
                xml_href = xml_link.get_attribute("href")
                pdf_href = pdf_link.get_attribute("href")
                chave = xml_href.split("/")[-1]
                results.append({
                    "chave": chave,
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

def download_files(page, download_urls, impostos_retidos, download_dir):
    fed_xml_dir = os.path.join(download_dir, "federal", "xmls")
    fed_pdf_dir = os.path.join(download_dir, "federal", "pdfs")
    mun_xml_dir = os.path.join(download_dir, "municipal", "xmls")
    mun_pdf_dir = os.path.join(download_dir, "municipal", "pdfs")
    temp_dir    = os.path.join(download_dir, "temp")
    for d in [fed_xml_dir, fed_pdf_dir, mun_xml_dir, mun_pdf_dir, temp_dir]:
        os.makedirs(d, exist_ok=True)

    referer = page.url
    downloaded = federal_count = municipal_count = skipped = failed = 0
    total = len(download_urls)

    for i, url_info in enumerate(download_urls, 1):
        chave    = url_info["chave"]
        temp_xml = os.path.join(temp_dir, f"{chave}.xml")
        print(f"[{i}/{total}] XML {chave[:20]}...", flush=True)

        if not request_download(page, url_info["xml_url"], temp_xml, referer):
            failed += 1
            continue

        federal = is_federal(temp_xml)
        nnfse   = get_nnfse(temp_xml) or chave[:10]

        if not federal:
            os.remove(temp_xml)
            skipped += 1
            continue

        xml_dir  = fed_xml_dir
        pdf_dir  = fed_pdf_dir
        category = "federal"

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
            print(f"[OK] {category.upper()} | Nota {nnfse}", flush=True)
        else:
            print(f"[OK] {category.upper()} | Nota {nnfse} (XML ok, PDF falhou)", flush=True)
            failed += 1

        downloaded += 1
        federal_count += 1
        time.sleep(0.3)

    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"[OK] {downloaded} notas baixadas — {federal_count} federal | {skipped} sem retencao ignoradas", flush=True)
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
    referer = page.url
    downloaded = failed = 0
    total = len(all_urls)
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

