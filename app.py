from flask import Flask, render_template, request, jsonify, send_file
import json
import subprocess
import os
import sys
import zipfile
import tempfile
import importlib
from datetime import datetime

app = Flask(__name__)

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
COMPANIES_FILE = os.path.join(BASE_DIR, 'config', 'companies.json')
GROUPS_FILE    = os.path.join(BASE_DIR, 'config', 'groups.json')
SETTINGS_FILE  = os.path.join(BASE_DIR, 'config', 'settings.json')

SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/1MI4xI6rSWfYVYTtPfXOzNPon-AGq0KXh/export?format=csv'

def load_companies():
    try:
        import urllib.request
        import csv
        import io
        with urllib.request.urlopen(SHEET_CSV_URL) as response:
            content = response.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        companies = []
        for row in reader:
            if row.get('cnpj') and row.get('password'):
                companies.append({
                    'name':       row.get('name', '').strip(),
                    'cnpj':       row.get('cnpj', '').strip(),
                    'password':   row.get('password', '').strip(),
                    'accountant': row.get('accountant', 'Empresas').strip(),
                    'email':      row.get('email', '').strip(),
                })
        return companies
    except Exception as e:
        print(f'[AVISO] Falha ao carregar Google Sheets: {e}, usando companies.json')
        with open(COMPANIES_FILE, encoding='utf-8') as f:
            return json.load(f)

def save_companies(companies):
    with open(COMPANIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)

def load_groups():
    with open(GROUPS_FILE, encoding='utf-8') as f:
        return json.load(f)

def save_groups(groups):
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)

def get_downloads_path():
    with open(SETTINGS_FILE, encoding='utf-8') as f:
        return json.load(f)['downloads_path']

@app.route('/health')
def health():
    return 'ok'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/companies', methods=['GET'])
def get_companies():
    return jsonify({'companies': load_companies(), 'groups': load_groups()})

@app.route('/api/companies', methods=['POST'])
def add_company():
    companies = load_companies()
    companies.append(request.json)
    save_companies(companies)
    return jsonify({'ok': True})

@app.route('/api/companies/<int:idx>', methods=['DELETE'])
def delete_company(idx):
    companies = load_companies()
    companies.pop(idx)
    save_companies(companies)
    return jsonify({'ok': True})

@app.route('/api/companies/<int:idx>', methods=['PUT'])
def update_company(idx):
    companies = load_companies()
    companies[idx] = request.json
    save_companies(companies)
    return jsonify({'ok': True})

@app.route('/api/groups', methods=['GET'])
def get_groups():
    return jsonify(load_groups())

@app.route('/api/groups', methods=['POST'])
def add_group():
    groups = load_groups()
    group  = request.json
    group['id'] = str(datetime.now().timestamp())
    if 'companies' in group and 'cnpjs' not in group:
        group['cnpjs'] = group.pop('companies')
    groups.append(group)
    save_groups(groups)
    return jsonify({'ok': True, 'id': group['id']})

@app.route('/api/groups/<group_id>', methods=['PUT'])
def update_group(group_id):
    groups = load_groups()
    data   = request.json
    if 'companies' in data and 'cnpjs' not in data:
        data['cnpjs'] = data.pop('companies')
    for i, g in enumerate(groups):
        if g['id'] == group_id:
            groups[i]       = data
            groups[i]['id'] = group_id
            break
    save_groups(groups)
    return jsonify({'ok': True})

@app.route('/api/groups/<group_id>', methods=['DELETE'])
def delete_group(group_id):
    groups = [g for g in load_groups() if g['id'] != group_id]
    save_groups(groups)
    return jsonify({'ok': True})

@app.route('/api/run', methods=['POST'])
def run():
    data     = request.json
    start    = data.get('start')
    end      = data.get('end')
    selected = data.get('companies', [])

    try:
        d1 = datetime.strptime(start, '%d/%m/%Y')
        d2 = datetime.strptime(end,   '%d/%m/%Y')
        if (d2 - d1).days > 31:
            return jsonify({'ok': False, 'error': 'Periodo nao pode exceder 31 dias'}), 400
        if d2 < d1:
            return jsonify({'ok': False, 'error': 'Data final deve ser maior que a inicial'}), 400
    except:
        return jsonify({'ok': False, 'error': 'Datas invalidas'}), 400

    all_companies      = load_companies()
    selected_companies = [c for c in all_companies if c['cnpj'] in selected]

    if not selected_companies:
        return jsonify({'ok': False, 'error': 'Nenhuma empresa selecionada'}), 400

    temp_file = os.path.join(BASE_DIR, 'config', 'temp_run.json')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump({'companies': selected_companies, 'start': start, 'end': end, 'mode': 'reinf'}, f)

    result = subprocess.run(
        ['python', os.path.join(BASE_DIR, 'main.py'), '--config', temp_file],
        capture_output=True, text=True
    )

    print("STDOUT:", result.stdout[-2000:])
    print("STDERR:", result.stderr[-2000:])
    print("RETURNCODE:", result.returncode)

    if result.returncode != 0:
        error_msg = result.stderr[-800:] if result.stderr else result.stdout[-800:] if result.stdout else 'Erro desconhecido'
        return jsonify({'ok': False, 'error': error_msg}), 500

    downloads_path = get_downloads_path()
    month          = d1.strftime('%m-%Y')
    selected_names = [c['name'] for c in selected_companies]

    try:
        _base = os.path.dirname(os.path.abspath(__file__))
        if _base not in sys.path:
            sys.path.insert(0, _base)
        import generate_summary
        importlib.reload(generate_summary)
        generate_summary.generate_summary(filter_names=selected_names)
    except Exception as e:
        import traceback
        with open(os.path.join(BASE_DIR, 'resumo_error.log'), 'w') as f:
            f.write(traceback.format_exc())

    try:
        import generate_fiscal
        importlib.reload(generate_fiscal)
        generate_fiscal.generate_fiscal_all(filter_names=selected_names)
    except Exception as e:
        import traceback
        with open(os.path.join(BASE_DIR, 'fiscal_error.log'), 'w') as f:
            f.write(traceback.format_exc())

    resumo_path = os.path.join(downloads_path, 'Empresas', 'resumo_nfse.xlsx')
    zip_path    = os.path.join(tempfile.gettempdir(), f'nfse_{month}_{datetime.now().strftime("%H%M%S")}.zip')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for company in selected_companies:
            safe_name   = company['name'].replace('/', '_').replace('\\', '_').replace(':', '_')
            company_dir = os.path.join(downloads_path, company['accountant'], safe_name, month)
            if os.path.exists(company_dir):
                for root, dirs, files in os.walk(company_dir):
                    rel_root = os.path.relpath(root, company_dir)
                    if rel_root.split(os.sep)[0] in ['pdfs', 'xmls']:
                        continue
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname   = os.path.relpath(file_path, downloads_path)
                        zf.write(file_path, arcname)
        if os.path.exists(resumo_path):
            zf.write(resumo_path, os.path.join('Empresas', 'resumo_nfse.xlsx'))

    return send_file(zip_path, as_attachment=True, download_name=f'nfse_{month}.zip', mimetype='application/zip')

@app.route('/api/run-all', methods=['POST'])
def run_all():
    data     = request.json
    start    = data.get('start')
    end      = data.get('end')
    selected = data.get('companies', [])

    try:
        d1 = datetime.strptime(start, '%d/%m/%Y')
        d2 = datetime.strptime(end,   '%d/%m/%Y')
        if (d2 - d1).days > 31:
            return jsonify({'ok': False, 'error': 'Periodo nao pode exceder 31 dias'}), 400
        if d2 < d1:
            return jsonify({'ok': False, 'error': 'Data final deve ser maior que a inicial'}), 400
    except:
        return jsonify({'ok': False, 'error': 'Datas invalidas'}), 400

    all_companies      = load_companies()
    selected_companies = [c for c in all_companies if c['cnpj'] in selected]

    if not selected_companies:
        return jsonify({'ok': False, 'error': 'Nenhuma empresa selecionada'}), 400

    temp_file = os.path.join(BASE_DIR, 'config', 'temp_run_all.json')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump({'companies': selected_companies, 'start': start, 'end': end, 'mode': 'all'}, f)

    result = subprocess.run(
        ['python', os.path.join(BASE_DIR, 'main.py'), '--config', temp_file],
        capture_output=True, text=True
    )

    print("STDOUT:", result.stdout[-2000:])
    print("STDERR:", result.stderr[-2000:])
    print("RETURNCODE:", result.returncode)

    if result.returncode != 0:
        error_msg = result.stderr[-800:] if result.stderr else result.stdout[-800:] if result.stdout else 'Erro desconhecido'
        return jsonify({'ok': False, 'error': error_msg}), 500

    downloads_path = get_downloads_path()
    month          = d1.strftime('%m-%Y')

    zip_path = os.path.join(tempfile.gettempdir(), f'nfse_geral_{month}_{datetime.now().strftime("%H%M%S")}.zip')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for company in selected_companies:
            safe_name   = company['name'].replace('/', '_').replace('\\', '_').replace(':', '_')
            company_dir = os.path.join(downloads_path, company['accountant'], safe_name, month)
            notas_dir   = os.path.join(company_dir, 'notas')
            if os.path.exists(notas_dir):
                for root, dirs, files in os.walk(notas_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname   = os.path.relpath(file_path, downloads_path)
                        zf.write(file_path, arcname)

    return send_file(zip_path, as_attachment=True, download_name=f'nfse_geral_{month}.zip', mimetype='application/zip')

@app.route('/api/integrate', methods=['POST'])
def integrate():
    month       = request.form.get('month')
    resumo_file = request.files.get('resumo')

    if not month:
        return jsonify({'ok': False, 'error': 'Mes nao informado'}), 400
    if not resumo_file:
        return jsonify({'ok': False, 'error': 'Arquivo resumo nao enviado'}), 400

    temp_resumo = os.path.join(BASE_DIR, 'config', 'temp_resumo.xlsx')
    resumo_file.save(temp_resumo)

    result = subprocess.run(
        ['python', os.path.join(BASE_DIR, 'integracao.py'), temp_resumo, month],
        capture_output=True, text=True
    )

    print("STDOUT:", result.stdout[-2000:])
    print("STDERR:", result.stderr[-2000:])
    print("RETURNCODE:", result.returncode)

    if result.returncode != 0:
        error_msg = result.stderr[-800:] if result.stderr else result.stdout[-800:] if result.stdout else 'Erro desconhecido'
        return jsonify({'ok': False, 'error': error_msg}), 500

    return jsonify({'ok': True, 'output': result.stdout[-2000:]})

if __name__ == '__main__':
    app.run(debug=False, port=5000)