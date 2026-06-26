import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import json
import base64
import argparse
import shutil
import tempfile
import time
import urllib.request
import csv
import io
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.navigation import navigate_to_recebidas, apply_filter
from src.downloader import generate_excel, get_download_urls, download_files, download_files_all
from src.parser import parse_impostos_retidos

BASE_URL      = "https://www.nfse.gov.br/EmissorNacional"
SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/1MI4xI6rSWfYVYTtPfXOzNPon-AGq0KXh/export?format=csv'
LOGIN_TIMEOUT = 300  # seconds to wait for manual login

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def get_download_dir(base, accountant, name, month):
    safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    path = os.path.join(base, "Empresas", safe_name, month)
    os.makedirs(path, exist_ok=True)
    return path

def decode_jwt(token):
    """Decode JWT payload without verification."""
    try:
        parts   = token.split('.')
        payload = parts[1]
        # Add padding
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.b64decode(payload).decode('utf-8')
        return json.loads(decoded)
    except Exception as e:
        log(f"[AVISO] Falha ao decodificar JWT: {e}")
        return {}

def lookup_company_in_sheet(cnpj_digits):
    """Try to find company name and accountant in Google Sheet by CNPJ."""
    try:
        with urllib.request.urlopen(SHEET_CSV_URL, timeout=10) as response:
            content = response.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            sheet_cnpj = ''.join(filter(str.isdigit, row.get('cnpj', '')))
            if sheet_cnpj == cnpj_digits:
                return {
                    'name':       row.get('name', '').strip(),
                    'accountant': row.get('accountant', 'Certificado').strip(),
                }
    except Exception as e:
        log(f"[AVISO] Falha ao buscar empresa na planilha: {e}")
    return None

def wait_for_login(page):
    """
    Wait for the user to complete manual login.
    Detects login by polling sessionStorage for accessToken JWT.
    Returns JWT payload dict or None on timeout.
    """
    log("Aguardando login manual... (você tem 5 minutos)")
    log("Faça login com seu certificado digital no navegador aberto.")

    start = time.time()
    while time.time() - start < LOGIN_TIMEOUT:
        try:
            token = page.evaluate("window.sessionStorage.getItem('accessToken')")
            if token:
                log("[OK] Login detectado via accessToken")
                payload = decode_jwt(token)
                if payload:
                    return payload
        except:
            pass
        time.sleep(2)

    log("[ERRO] Timeout aguardando login manual")
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        run_config = json.load(f)

    custom_start = run_config.get("start")
    custom_end   = run_config.get("end")
    mode         = run_config.get("mode", "reinf")

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.json"), encoding="utf-8") as f:
        settings = json.load(f)

    base_dir = settings["downloads_path"]

    if custom_start:
        d     = datetime.strptime(custom_start, "%d/%m/%Y")
        month = d.strftime("%m-%Y")
    else:
        today     = date.today()
        first_day = (today - relativedelta(months=1)).replace(day=1)
        month     = first_day.strftime("%m-%Y")

    temp_dir = tempfile.mkdtemp(prefix="nfse_cert_")

    try:
        with sync_playwright() as p:
            log("Abrindo navegador para login manual...")

            # Launch visible browser — no extension, fresh temp profile
            context = p.chromium.launch_persistent_context(
                user_data_dir=os.path.join(temp_dir, "profile"),
                headless=False,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                ],
                no_viewport=True,
            )

            page = context.new_page()

            try:
                # Navigate to login page
                page.goto(f"{BASE_URL}/Login", timeout=60000)
                page.wait_for_load_state("domcontentloaded", timeout=60000)
            except Exception as e:
                log(f"[AVISO] Falha ao abrir portal: {e}")

            # Wait for user to log in manually
            jwt_payload = wait_for_login(page)
            if not jwt_payload:
                log("[ERRO] Login nao detectado. Encerrando.")
                context.close()
                sys.exit(1)

            # Extract identity from JWT
            cnpj_raw    = jwt_payload.get("inscricao", "")
            cnpj_digits = ''.join(filter(str.isdigit, cnpj_raw))
            nome_jwt    = jwt_payload.get("nome", "").strip()

            log(f"[OK] Empresa identificada: CNPJ {cnpj_digits}")

            # Try to get name/accountant from Google Sheet
            sheet_data = lookup_company_in_sheet(cnpj_digits)

            if sheet_data and sheet_data.get("name"):
                name       = sheet_data["name"]
                accountant = sheet_data["accountant"]
                log(f"[OK] Empresa encontrada na planilha: {name} ({accountant})")
            elif nome_jwt:
                name       = nome_jwt
                accountant = "Certificado"
                log(f"[OK] Usando nome do JWT: {name}")
            else:
                # Fallback: use formatted CNPJ as name
                if len(cnpj_digits) == 14:
                    name = f"{cnpj_digits[:2]}.{cnpj_digits[2:5]}.{cnpj_digits[5:8]}/{cnpj_digits[8:12]}-{cnpj_digits[12:]}"
                else:
                    name = cnpj_digits
                accountant = "Certificado"
                log(f"[OK] Usando CNPJ como nome: {name}")

            download_dir = get_download_dir(base_dir, accountant, name, month)
            log(f"[OK] Pasta de destino: {download_dir}")

            try:
                log("Navegando para Notas Recebidas...")
                ok = navigate_to_recebidas(page)
                if not ok:
                    log("[ERRO] Nao foi possivel acessar Notas Recebidas")
                    page.close()
                    context.close()
                    sys.exit(1)

                log("Aplicando filtro de datas...")
                ok = apply_filter(page, custom_start, custom_end)
                if not ok:
                    log("[ERRO] Nao foi possivel aplicar filtro de datas")
                    page.close()
                    context.close()
                    sys.exit(1)

                log("Gerando planilha de notas recebidas...")
                excel_path = generate_excel(page, download_dir)
                if not excel_path:
                    log("[ERRO] Falha ao gerar planilha")
                    page.close()
                    context.close()
                    sys.exit(1)

                log("Verificando impostos retidos...")
                impostos = parse_impostos_retidos(excel_path)
                if not impostos:
                    log("Nenhum imposto retido encontrado — sem notas para baixar")
                    page.close()
                    context.close()
                    sys.exit(0)

                log(f"{len(impostos)} nota(s) com retencoes encontradas — mapeando URLs...")
                urls = get_download_urls(page)

                log(f"{len(urls)} URL(s) mapeadas — iniciando downloads...")
                download_files(page, urls, impostos, download_dir)

                page.close()
                context.close()
                log("[OK] Concluido com sucesso")
                sys.exit(0)

            except Exception as e:
                log(f"[ERRO] {e}")
                try:
                    context.close()
                except:
                    pass
                sys.exit(1)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
