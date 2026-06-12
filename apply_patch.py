"""
NFS-e Automation - Patch Script
Run this on any machine to apply all no-extension changes.
Usage: python apply_patch.py
"""
import os, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# worker.py
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
WORKER = '''import sys
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
from src.downloader import get_download_urls, download_files, download_files_all, generate_recebidas_excel

def get_download_dir(base, name, month):
    safe_name = name.replace("/", "_").replace("\\\\", "_").replace(":", "_")
    path = os.path.join(base, "Empresas", safe_name, month)
    os.makedirs(path, exist_ok=True)
    return path

def log(name, msg):
    print(f\'[{datetime.now().strftime("%H:%M:%S")}] {name} | {msg}\', flush=True)

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

    cnpj     = company["cnpj"]
    name     = company["name"]
    password = company["password"]

    log(name, f"Iniciando processamento - {month}")
    download_dir = get_download_dir(base_dir, name, month)

    cleanup_folders = ["pdfs", "xmls", "temp", "temp_all"]
    if mode == "reinf":
        cleanup_folders.append("notas")
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
                    log(name, "ERRO - Login falhou, encerrando")
                    sys.exit(1)

                log(name, "Login efetuado, navegando para notas recebidas...")
                navigate_to_recebidas(page)
                log(name, "Aplicando filtro de datas...")
                apply_filter(page, custom_start, custom_end)

                if mode == "all":
                    log(name, "Baixando todas as notas (modo completo)...")
                    result_path = download_files_all(page, download_dir)
                    page.close(); context.close()
                    log(name, "Concluido" if result_path else "ERRO - falha ao baixar notas")
                    sys.exit(0 if result_path else 1)
                else:
                    log(name, "Mapeando notas no portal...")
                    urls = get_download_urls(page)
                    if not urls:
                        log(name, "Nenhuma nota encontrada no periodo")
                        try:
                            generate_recebidas_excel([], name, month, download_dir)
                        except Exception as e:
                            log(name, f"Aviso ao gerar planilha vazia: {e}")
                        page.close(); context.close()
                        sys.exit(0)

                    log(name, f"{len(urls)} nota(s) encontradas - baixando e classificando XMLs...")
                    download_files(page, urls, None, download_dir, company_name=name, month=month)
                    page.close(); context.close()
                    log(name, "Concluido com sucesso")
                    sys.exit(0)

            except Exception as e:
                log(name, f"ERRO - {e}")
                try: context.close()
                except: pass
                sys.exit(1)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
'''

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# src/auth.py
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
AUTH = '''import json
import os
import shutil
import time

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.json")
    with open(os.path.abspath(settings_path), encoding="utf-8") as f:
        return json.load(f)

def create_browser(playwright):
    settings = load_settings()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=settings["profile_path"],
        headless=False,
        args=["--disable-extensions"],
    )
    return context

def create_browser_for_company(playwright, temp_dir):
    settings = load_settings()
    profile_copy = os.path.join(temp_dir, "profile")
    shutil.copytree(settings["profile_path"], profile_copy)
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=profile_copy,
        headless=False,
        args=["--disable-extensions"],
    )
    return context

def is_portal_error(page):
    try:
        content = page.content()
        if any(x in content for x in ["The service is unavailable","502 - Web server","Server Error","Bad Gateway","Service Unavailable"]):
            return True
        if "unavailable" in content.lower() and "service" in content.lower():
            return True
        return False
    except:
        return False

def login(context, cnpj, password, name="", max_retries=10, wait_seconds=5):
    for attempt in range(1, max_retries + 1):
        page = context.new_page()
        try:
            if attempt > 1:
                print(f"[AVISO] Tentando login novamente ({attempt}/{max_retries})...", flush=True)
                time.sleep(wait_seconds)
            page.goto(f"{BASE_URL}/Login", timeout=120000)
            try:
                page.wait_for_load_state("networkidle", timeout=120000)
            except:
                pass
            if is_portal_error(page):
                print(f"[AVISO] Portal indisponivel ({attempt}/{max_retries})", flush=True)
                page.close(); time.sleep(wait_seconds); continue
            try:
                page.wait_for_selector("#Inscricao", timeout=120000)
            except:
                print(f"[AVISO] Login nao carregou ({attempt}/{max_retries})", flush=True)
                page.close(); continue
            page.fill("#Inscricao", cnpj)
            page.fill("#Senha", password)
            page.click("button[type=\'submit\']")
            try:
                page.wait_for_url(lambda url: "Login" not in url, timeout=120000)
            except:
                if page.locator("text=Usuario e/ou senha invalidos").is_visible():
                    print(f"[SENHA ERRADA] {name} | CNPJ: {cnpj}", flush=True)
                    page.close(); return None
                print(f"[AVISO] Login nao redirecionou ({attempt}/{max_retries})", flush=True)
                page.close(); continue
            if is_portal_error(page):
                print(f"[AVISO] Portal erro apos login ({attempt}/{max_retries})", flush=True)
                page.close(); time.sleep(wait_seconds); continue
            print(f"[OK] Login: {name} ({cnpj})", flush=True)
            return page
        except Exception as e:
            print(f"[AVISO] Erro login ({attempt}/{max_retries}): {str(e)[:80]}", flush=True)
            try: page.close()
            except: pass
            if attempt < max_retries:
                time.sleep(wait_seconds)
    print(f"[ERRO] Login falhou apos {max_retries} tentativas: {name}", flush=True)
    return None
'''

files = {
    'worker.py': WORKER,
    os.path.join('src', 'auth.py'): AUTH,
}

print("Applying patches...")
for rel_path, content in files.items():
    full_path = os.path.join(BASE_DIR, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[OK] {rel_path}")

# Clear pycache
import shutil
for d in [os.path.join(BASE_DIR, '__pycache__'), os.path.join(BASE_DIR, 'src', '__pycache__')]:
    shutil.rmtree(d, ignore_errors=True)

print("\nAll patches applied. Run worker.py to test.")
