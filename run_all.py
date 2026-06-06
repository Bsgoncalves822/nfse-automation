"""
NFS-e - Run all companies and build ZIP
Usage: python run_all.py --start 01/05/2026 --end 31/05/2026
"""
import os, sys, json, subprocess, zipfile, tempfile, shutil, argparse
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def get_downloads_path():
    with open(os.path.join(BASE_DIR, 'config', 'settings.json'), encoding='utf-8') as f:
        return json.load(f)['downloads_path']

def load_companies():
    try:
        import urllib.request, csv, io
        url = 'https://docs.google.com/spreadsheets/d/1MI4xI6rSWfYVYTtPfXOzNPon-AGq0KXh/export?format=csv'
        with urllib.request.urlopen(url, timeout=15) as r:
            content = r.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        companies = []
        for row in reader:
            if row.get('cnpj') and row.get('password'):
                companies.append({
                    'name':     row['name'].strip(),
                    'cnpj':     row['cnpj'].strip(),
                    'password': row['password'].strip(),
                })
        # Save to cache
        with open(os.path.join(BASE_DIR, 'config', 'companies.json'), 'w', encoding='utf-8') as f:
            json.dump(companies, f, indent=2, ensure_ascii=False)
        print(f'[OK] {len(companies)} empresas carregadas do Google Sheets')
        return companies
    except Exception as e:
        print(f'[AVISO] Google Sheets falhou: {e}, usando cache')
        with open(os.path.join(BASE_DIR, 'config', 'companies.json'), encoding='utf-8') as f:
            return json.load(f)

def build_zip(downloads_path, month, companies):
    zip_name = f'nfse_{month}.zip'
    zip_path = os.path.join(os.path.expanduser('~'), 'Downloads', zip_name)

    resumo_path = os.path.join(downloads_path, 'Empresas', 'resumo_nfse.xlsx')
    added = 0

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for company in companies:
            cnpj_clean  = company['cnpj'].replace('.','').replace('/','_').replace('-','').replace(' ','')
            folder_name = company['name'] + ' (' + cnpj_clean + ')'
            safe_name   = folder_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            company_dir = os.path.join(downloads_path, 'Empresas', safe_name, month)

            if not os.path.exists(company_dir):
                continue  # wrong password or no notes — skip silently

            file_count = 0
            for root, dirs, files in os.walk(company_dir):
                rel_root = os.path.relpath(root, company_dir)
                if rel_root.split(os.sep)[0] in ['pdfs', 'xmls']:
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname   = os.path.relpath(file_path, downloads_path)
                    zf.write(file_path, arcname)
                    file_count += 1

            if file_count > 0:
                print(f'[ZIP] {company["name"]}: {file_count} arquivos', flush=True)
                added += 1

        if os.path.exists(resumo_path):
            zf.write(resumo_path, os.path.join('Empresas', 'resumo_nfse.xlsx'))

    size_mb = os.path.getsize(zip_path) / 1024 / 1024
    print(f'\n[OK] ZIP salvo: {zip_path}')
    print(f'[OK] {added} empresas | {size_mb:.1f} MB')
    return zip_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default=None)
    parser.add_argument('--end',   default=None)
    args = parser.parse_args()

    if args.start:
        d = datetime.strptime(args.start, '%d/%m/%Y')
        month = d.strftime('%m-%Y')
        start = args.start
        end   = args.end or args.start
    else:
        today = date.today()
        first = (today - relativedelta(months=1)).replace(day=1)
        last  = first + relativedelta(months=1) - relativedelta(days=1)
        month = first.strftime('%m-%Y')
        start = first.strftime('%d/%m/%Y')
        end   = last.strftime('%d/%m/%Y')

    print(f'[OK] Periodo: {start} a {end} | Mes: {month}')

    companies     = load_companies()
    downloads_path = get_downloads_path()

    print(f'[OK] {len(companies)} empresas | downloads: {downloads_path}')

    # Write temp config
    temp_config = os.path.join(BASE_DIR, 'config', 'temp_run_all_companies.json')
    with open(temp_config, 'w', encoding='utf-8') as f:
        json.dump({'companies': companies, 'start': start, 'end': end, 'mode': 'reinf'}, f)

    print(f'\n[OK] Iniciando processamento...\n{"="*50}')

    proc = subprocess.run(
        [sys.executable, '-u', os.path.join(BASE_DIR, 'main.py'), '--config', temp_config],
        encoding='utf-8',
        errors='replace',
    )

    print(f'\n{"="*50}')
    print('[OK] Processamento concluido. Gerando ZIP...')

    # Generate summary and fiscal
    try:
        sys.path.insert(0, BASE_DIR)
        import generate_summary, importlib
        importlib.reload(generate_summary)
        generate_summary.generate_summary(filter_month=month)
    except Exception as e:
        print(f'[AVISO] Resumo: {e}')

    try:
        import generate_fiscal
        importlib.reload(generate_fiscal)
        generate_fiscal.generate_fiscal_all()
    except Exception as e:
        print(f'[AVISO] Fiscal: {e}')

    zip_path = build_zip(downloads_path, month, companies)
    print(f'\n[DONE] {zip_path}')

if __name__ == '__main__':
    main()
