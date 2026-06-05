import sys
import json
import os
import argparse
import subprocess
import shutil
import tempfile
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_month_label(start=None):
    if start:
        d = datetime.strptime(start, "%d/%m/%Y")
        return d.strftime("%m-%Y")
    today = date.today()
    first_day = (today - relativedelta(months=1)).replace(day=1)
    return first_day.strftime("%m-%Y")

def run_company_worker(company, base_dir, month, custom_start, custom_end, mode):
    temp_config = tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False, encoding='utf-8'
    )
    try:
        json.dump({
            "companies": [company],
            "start": custom_start,
            "end": custom_end,
            "mode": mode
        }, temp_config)
        temp_config.close()

        proc = subprocess.Popen(
            [sys.executable, '-u',
             os.path.join(os.path.dirname(os.path.abspath(__file__)), 'worker.py'),
             '--config', temp_config.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )

        for line in proc.stdout:
            line = line.rstrip()
            if line:
                print(line, flush=True)

        proc.wait()
        return "retidos" if proc.returncode == 0 else "error"

    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {company.get('name')}", flush=True)
        return "error"
    except Exception as e:
        print(f"[FATAL] {company.get('name')} | {e}", flush=True)
        return "error"
    finally:
        try:
            os.unlink(temp_config.name)
        except:
            pass

def main():
    license_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'activate_license.py')
    subprocess.run(['python', license_script], capture_output=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--group", default=None, nargs="?", const="__first__")
    parser.add_argument("--cnpjs", default=None)
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
                print(f"[OK] Usando grupo: {group['name']} ({len(companies)} empresas)", flush=True)
            else:
                companies = all_companies
                print("[INFO] Nenhum grupo encontrado, usando todas as empresas", flush=True)
        except Exception as e:
            print(f"[AVISO] Erro ao carregar grupos: {e}, usando companies.json", flush=True)
            with open(companies_path, encoding="utf-8") as f:
                companies = json.load(f)
        custom_start = None
        custom_end   = None

    elif args.cnpjs:
        cnpj_list = [c.strip() for c in args.cnpjs.split(",")]
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "companies.json"), encoding="utf-8") as f:
            all_companies = json.load(f)
        companies = [c for c in all_companies if c["cnpj"] in cnpj_list]
        print(f"[OK] Filtrando por CNPJs: {len(companies)} empresa(s) encontrada(s)", flush=True)
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
    month    = get_month_label(custom_start)

    stats = {"retidos": 0, "none": 0, "error": 0}

    print(f"[OK] {len(companies)} empresa(s) | 3 workers | Modo: {mode} | Mes: {month}", flush=True)

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(run_company_worker, company, base_dir, month, custom_start, custom_end, mode): company
            for company in companies
        }
        for future in as_completed(futures):
            company = futures[future]
            try:
                result = future.result()
            except Exception as e:
                print(f"[UNHANDLED] {company.get('name')} | {e}", flush=True)
                result = "error"
            stats[result] = stats.get(result, 0) + 1

    print(f"{'='*50}", flush=True)
    print(f"Concluido: {month} | Modo: {mode}", flush=True)
    print(f"Processadas: {stats['retidos']} | Sem notas: {stats['none']} | Erros: {stats['error']}", flush=True)

if __name__ == "__main__":
    main()

