import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import os
import json
import argparse
import shutil
import tempfile
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.auth import create_browser_for_company, login
from src.navigation import navigate_to_recebidas, apply_filter
from src.downloader import generate_excel, get_download_urls, download_files, download_files_all
from src.parser import parse_impostos_retidos

def get_download_dir(base, accountant, name, month):
    safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    path = os.path.join(base, accountant, safe_name, month)
    os.makedirs(path, exist_ok=True)
    return path

def log(name, msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {name} | {msg}", flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        run_config = json.load(f)

    company      = run_config["companies"][0]
    custom_start = run_config.get("start")
    custom_end   = run_config.get("end")
    mode         = run_config.get("mode", "reinf")

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.json"), encoding="utf-8") as f:
        settings = json.load(f)

    base_dir = settings["downloads_path"]

    if custom_start:
        d = datetime.strptime(custom_start, "%d/%m/%Y")
        month = d.strftime("%m-%Y")
    else:
        today = date.today()
        first_day = (today - relativedelta(months=1)).replace(day=1)
        month = first_day.strftime("%m-%Y")

    cnpj       = company["cnpj"]
    name       = company["name"]
    password   = company["password"]
    accountant = company["accountant"]

    log(name, f"Iniciando processamento — {month}")

    download_dir = get_download_dir(base_dir, accountant, name, month)

    cleanup_folders = ['pdfs', 'xmls', 'temp', 'temp_all']
    if mode == 'reinf':
        cleanup_folders.append('notas')
    for old_folder in cleanup_folders:
        old_path = os.path.join(download_dir, old_folder)
        if os.path.exists(old_path):
            shutil.rmtree(old_path, ignore_errors=True)

    temp_dir = tempfile.mkdtemp(prefix="nfse_")

    try:
        with sync_playwright() as p:
            log(name, "Abrindo navegador...")
            context = create_browser_for_company(p, temp_dir)
            try:
                log(name, "Fazendo login...")
                page = login(context, cnpj, password, name)
                if not page:
                    log(name, "ERRO — Login falhou, encerrando")
                    sys.exit(1)

                log(name, "Login efetuado, navegando para notas recebidas...")
                navigate_to_recebidas(page)

                log(name, "Aplicando filtro de datas...")
                apply_filter(page, custom_start, custom_end)

                if mode == 'all':
                    log(name, "Baixando todas as notas (modo completo)...")
                    result_path = download_files_all(page, download_dir)
                    page.close()
                    context.close()
                    if result_path:
                        log(name, "Concluido — todas as notas baixadas com sucesso")
                        sys.exit(0)
                    else:
                        log(name, "ERRO — falha ao baixar notas")
                        sys.exit(1)

                else:
                    # reinf mode
                    # Try extension-based Excel first
                    log(name, "Tentando gerar planilha via extensao...")
                    excel_path = generate_excel(page, download_dir)

                    if excel_path:
                        # Extension is working — use Excel to filter notes
                        log(name, "Planilha gerada, verificando impostos retidos...")
                        impostos = parse_impostos_retidos(excel_path)
                        if not impostos:
                            log(name, "Nenhum imposto retido encontrado — sem notas para baixar")
                            page.close()
                            context.close()
                            sys.exit(0)
                        log(name, f"{len(impostos)} nota(s) com retencoes — mapeando URLs...")
                        urls = get_download_urls(page)
                        log(name, f"{len(urls)} URL(s) mapeadas — iniciando downloads...")
                        download_files(page, urls, impostos, download_dir)
                    else:
                        # No extension — scrape rows and classify XMLs locally
                        log(name, "Sem extensao — mapeando notas direto do portal...")
                        urls = get_download_urls(page)
                        if not urls:
                            log(name, "Nenhuma nota encontrada no periodo")
                            page.close()
                            context.close()
                            sys.exit(0)
                        log(name, f"{len(urls)} nota(s) encontradas — baixando e classificando XMLs...")
                        download_files(page, urls, None, download_dir)

                    page.close()
                    context.close()
                    log(name, "Concluido com sucesso")
                    sys.exit(0)

            except Exception as e:
                log(name, f"ERRO — {e}")
                try:
                    context.close()
                except:
                    pass
                sys.exit(1)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
