import sys
import json
import os
import argparse
import subprocess
import shutil
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.auth import create_browser, login
from src.navigation import navigate_to_recebidas, apply_filter
from src.downloader import generate_excel, get_download_urls, download_files, download_files_all
from src.parser import parse_impostos_retidos

def get_month_label(start=None):
    if start:
        d = datetime.strptime(start, "%d/%m/%Y")
        return d.strftime("%m-%Y")
    today = date.today()
    first_day = (today - relativedelta(months=1)).replace(day=1)
    return first_day.strftime("%m-%Y")

def get_download_dir(base, accountant, name, month):
    safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    path = os.path.join(base, accountant, safe_name, month)
    os.makedirs(path, exist_ok=True)
    return path

def process_company(context, company, base_dir, month, custom_start=None, custom_end=None, mode='reinf'):
    cnpj       = company["cnpj"]
    name       = company["name"]
    password   = company["password"]
    accountant = company["accountant"]

    print(f"\n{'='*50}")
    print(f"Empresa: {name} | Contador: {accountant} | Modo: {mode}")

    download_dir = get_download_dir(base_dir, accountant, name, month)

    for old_folder in ['pdfs', 'xmls', 'temp']:
        old_path = os.path.join(download_dir, old_folder)
        if os.path.exists(old_path):
            shutil.rmtree(old_path, ignore_errors=True)

    page = login(context, cnpj, password)
    if not page:
        return "error"

    try:
        navigate_to_recebidas(page)
        apply_filter(page, custom_start, custom_end)

        if mode == 'all':
            result_path = download_files_all(page, download_dir)
            page.close()
            return "retidos" if result_path else "error"

        else:
            excel_path = generate_excel(page, download_dir)
            if not excel_path:
                page.close()
                return "error"

            impostos = parse_impostos_retidos(excel_path)

            if not impostos:
                print(f"[INFO] Sem retencoes em {month}")
                page.close()
                return "none"

            urls = get_download_urls(page)
            download_files(page, urls, impostos, download_dir)
            page.close()
            return "retidos"

    except Exception as e:
        print(f"[ERRO] {cnpj}: {e}")
        page.close()
        return "error"

def main():
    license_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'activate_license.py')
    subprocess.run(['python', license_script], capture_output=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--group", default=None, nargs="?", const="__first__")
    args = parser.parse_args()

    mode = 'reinf'

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            run_config = json.load(f)
        companies    = run_config["companies"]
        custom_start = run_config.get("start")
        custom_end   = run_config.get("end")
        mode         = run_config.get("mode", "reinf")

    elif args.group is not None:
        groups_path    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "groups.json")
        companies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "companies.json")
        try:
            with open(groups_path, encoding="utf-8") as f:
                groups = json.load(f)
            with open(companies_path, encoding="utf-8") as f:
                all_companies = json.load(f)
            group = None
            if args.group != "__first__":
                group = next((g for g in groups if g["name"] == args.group), None)
            if not group and groups:
                group = groups[0]
            if group:
                group_cnpjs = set(group.get("cnpjs", []))
                companies = [c for c in all_companies if c["cnpj"] in group_cnpjs]
                print(f"[OK] Usando grupo: {group['name']} ({len(companies)} empresas)")
            else:
                companies = all_companies
                print("[INFO] Nenhum grupo encontrado, usando todas as empresas")
        except Exception as e:
            print(f"[AVISO] Erro ao carregar grupos: {e}, usando companies.json")
            with open(companies_path, encoding="utf-8") as f:
                companies = json.load(f)
        custom_start = None
        custom_end   = None

    else:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "companies.json"), encoding="utf-8") as f:
            companies = json.load(f)
        custom_start = None
        custom_end   = None

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.json"), encoding="utf-8") as f:
        settings = json.load(f)

    base_dir = settings["downloads_path"]

    if custom_start:
        d = datetime.strptime(custom_start, "%d/%m/%Y")
        month = d.strftime("%m-%Y")
    else:
        month = get_month_label()

    stats = {"retidos": 0, "none": 0, "error": 0}

    with sync_playwright() as p:
        context = create_browser(p)
        for company in companies:
            result = process_company(context, company, base_dir, month, custom_start, custom_end, mode=mode)
            stats[result] = stats.get(result, 0) + 1
        context.close()

    print(f"\n{'='*50}")
    print(f"Concluido: {month} | Modo: {mode}")
    print(f"  Processadas: {stats['retidos']}")
    print(f"  Sem notas:   {stats['none']}")
    print(f"  Erros:       {stats['error']}")

if __name__ == "__main__":
    main()