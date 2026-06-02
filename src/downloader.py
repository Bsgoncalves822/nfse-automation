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
        print(f"[AVISO] Erro ao classificar XML {xml_path}: {e}", flush=True)
        return False

def get_nnfse(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        el = root.find('.//nfse:nNFSe', NS)
        if el is not None and el.text:
            return str(el.text).strip()
        return None
    except:
        return None

def wait_for_page_ready(page, retries=3, timeout=120000):
    """Wait for page to load, retrying on 502/gateway errors."""
    for attempt in range(retries):
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
            # Check for 502/server error
            content = page.content()
            if "502" in content or "Server Error" in content or "service is unavailable" in content.lower():
                print(f"[AVISO] Portal retornou erro de servidor (tentativa {attempt+1}/{retries}), aguardando...", flush=True)
                time.sleep(10)
                page.reload()
                continue
            return True
        except Exception as e:
            if attempt < retries - 1:
                print(f"[AVISO] Timeout ao carregar pagina (tentativa {attempt+1}/{retries}), tentando novamente...", flush=True)
                time.sleep(5)
                try:
                    page.reload()
                except:
                    pass
            else:
                raise e
    return False

def generate_excel(page, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    try:
        page.wait_for_selector("#generateExcelBtn", timeout=600000)
        page.wait_for_timeout(2000)
        with page.expect_download(timeout=600000) as download_info:
            page.wait_for_timeout(3000)
            page.evaluate("document.getElementById('generateExcelBtn').click()")
            # Handle "Verificar notas canceladas?" popup
            try:
                page.wait_for_selector("#btnVerificar", timeout=15000)
                print("[INFO] Verificando notas canceladas...", flush=True)
                page.evaluate("document.getElementById('btnVerificar').click()")
            except:
                # Popup didn't appear, download already started
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
        print(f"[OK] Excel salvo: {save_path}", flush=True)
        return save_path
    except Exception as e:
        print(f"[ERRO] Falha ao gerar Excel: {e}", flush=True)
        return None

def normalize_cnpj(cnpj):
    return re.sub(r'[^0-9]', '', str(cnpj))

def scrape_page_urls(page):
    results = []
    rows = page.query_selector_all("tr.nfse-row, tr[data-chave]")
    for row in rows:
        try:
            if "nfse-cancelada" in (row.get_attribute("class") or ""):
                continue
            xml_link = row.query_selector("a[href*='/Download/NFSe/']")
            pdf_link = row.query_selector("a[href*='/Download/DANFSe/']")
            if xml_link and pdf_link:
                results.append({
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
        print(f"[OK] Pagina {pg}: {len(page_urls)} linhas", flush=True)

        proxima = page.query_selector("a[data-original-title='Pr\u00f3xima']")
        ultima  = page.query_selector("a[data-original-title='\u00daltima']")
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

    print(f"[OK] {len(results)} URLs de download mapeadas em {pg} pagina(s)", flush=True)
    return results

def download_with_retry(page, url, save_path, retries=3, timeout=120000):
    """Download a file with retry on portal errors."""
    for attempt in range(retries):
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
            with page.expect_download(timeout=timeout) as dl:
                page.evaluate(f"window.location.href = '{url}'")
            f = dl.value
            f.save_as(save_path)
            time.sleep(0.5)
            return True
        except Exception as e:
            err_str = str(e)
            if attempt < retries - 1:
                print(f"[AVISO] Falha ao baixar (tentativa {attempt+1}/{retries}): {err_str[:80]}...", flush=True)
                time.sleep(8)
                # Navigate back to recebidas before retrying
                try:
                    page.goto("https://www.nfse.gov.br/EmissorNacional/Notas/Recebidas")
                    wait_for_page_ready(page, retries=2)
                except:
                    pass
            else:
                print(f"[ERRO] Falha ao baixar {url.split('/')[-1]}: {err_str}", flush=True)
                return False
    return False

def download_files(page, download_urls, impostos_retidos, download_dir):
    fed_xml_dir  = os.path.join(download_dir, "federal", "xmls")
    fed_pdf_dir  = os.path.join(download_dir, "federal", "pdfs")
    mun_xml_dir  = os.path.join(download_dir, "municipal", "xmls")
    mun_pdf_dir  = os.path.join(download_dir, "municipal", "pdfs")
    temp_dir     = os.path.join(download_dir, "temp")

    for d in [fed_xml_dir, fed_pdf_dir, mun_xml_dir, mun_pdf_dir, temp_dir]:
        os.makedirs(d, exist_ok=True)

    retido_numeros = set(str(n["numero"]).strip() for n in impostos_retidos)
    retido_cnpjs   = set(normalize_cnpj(n["cnpj_emitente"]) for n in impostos_retidos)

    print(f"[INFO] {len(retido_numeros)} notas com retencao | {len(retido_cnpjs)} CNPJs emitentes", flush=True)

    downloaded      = 0
    federal_count   = 0
    municipal_count = 0
    skipped         = 0
    failed          = 0

    for url_info in download_urls:
        chave    = url_info["xml_url"].split("/")[-1]
        temp_xml = os.path.join(temp_dir, f"{chave}.xml")

        try:
            # Download XML with retry
            success = download_with_retry(page, url_info["xml_url"], temp_xml)
            if not success:
                failed += 1
                continue

            nnfse = get_nnfse(temp_xml)

            if nnfse not in retido_numeros:
                os.remove(temp_xml)
                skipped += 1
                continue

            federal  = is_federal(temp_xml)
            xml_dir  = fed_xml_dir if federal else mun_xml_dir
            pdf_dir  = fed_pdf_dir if federal else mun_pdf_dir
            category = "federal" if federal else "municipal"

            final_xml = os.path.join(xml_dir, f"{chave}.xml")
            if os.path.exists(final_xml):
                os.remove(final_xml)
            os.rename(temp_xml, final_xml)

            # Navigate back before PDF download
            page.goto("https://www.nfse.gov.br/EmissorNacional/Notas/Recebidas")
            wait_for_page_ready(page, retries=3)

            # Download PDF with retry
            temp_pdf = os.path.join(temp_dir, f"{chave}.pdf")
            success = download_with_retry(page, url_info["pdf_url"], temp_pdf)
            if success:
                final_pdf = os.path.join(pdf_dir, os.path.basename(temp_pdf))
                if os.path.exists(final_pdf):
                    os.remove(final_pdf)
                os.rename(temp_pdf, final_pdf)
                downloaded += 1
                if federal:
                    federal_count += 1
                else:
                    municipal_count += 1
                print(f"[OK] {category.upper()} | Nota {nnfse}", flush=True)
            else:
                # XML downloaded but PDF failed — still count it
                downloaded += 1
                if federal:
                    federal_count += 1
                else:
                    municipal_count += 1
                failed += 1
                print(f"[OK] {category.upper()} | Nota {nnfse} (XML ok, PDF falhou)", flush=True)

        except Exception as e:
            print(f"[ERRO] Falha ao processar {chave}: {e}", flush=True)
            failed += 1
            if os.path.exists(temp_xml):
                try:
                    os.remove(temp_xml)
                except:
                    pass

    shutil.rmtree(temp_dir, ignore_errors=True)

    # Summary
    print(f"[OK] {downloaded} notas baixadas - {federal_count} federal, {municipal_count} municipal | {skipped} ignoradas", flush=True)
    if failed > 0:
        print(f"[AVISO] {failed} falha(s) — portal instavel. Recomenda-se reexecutar mais tarde.", flush=True)

def download_files_all(page, download_dir):
    notas_dir = os.path.join(download_dir, "notas")
    os.makedirs(notas_dir, exist_ok=True)
    for old in glob.glob(os.path.join(notas_dir, "NFS-e_Todas_*.zip")):
        try:
            os.remove(old)
        except:
            pass
    try:
        with page.expect_download(timeout=600000) as dl:
            page.click("a:has-text('Baixar Tudo'), button:has-text('Baixar Tudo')")
            try:
                page.wait_for_selector("#btnVerificar", timeout=15000)
                print("[INFO] Verificando notas canceladas...", flush=True)
                page.evaluate("document.getElementById('btnVerificar').click()")
            except:
                pass
        download = dl.value
        save_path = os.path.join(notas_dir, download.suggested_filename)
        download.save_as(save_path)
        print(f"[OK] Baixar Tudo salvo: {save_path}", flush=True)
        return save_path
    except Exception as e:
        print(f"[ERRO] Falha no Baixar Tudo: {e}", flush=True)
        return None
