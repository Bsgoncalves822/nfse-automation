import urllib.request, csv, io, json, os, sys, subprocess, tempfile
from datetime import date
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

SHEET_URL = 'https://docs.google.com/spreadsheets/d/1MI4xI6rSWfYVYTtPfXOzNPon-AGq0KXh/export?format=csv'

TARGETS = [
    'camilo & ghisi', 'camilo holding', 'centro medico de diagnostico',
    'clinica de diagnosticos imbituba', 'clinica radiologica dr eneas',
    'cordis clinica', 'eco clinica', 'fema hotel', 'fernandes adm de imoveis',
    'hotel san silvestri', 'laboratorio bioclinico santa catarina',
    'lg clinica medica', 'narco clinica medica', 'obra de arte engenharia',
    'vitoria calegari',
    'delpizzo', 'clinica medica dl', 'gc castro althoff', 'herz clinica',
    'imobiliaria jeferson', 'julia soares', 'laboratorio de analises clinicas capivari',
    'machado servicos medicos', 'mater clinica medica', 'mfw participacoes',
    'otoclin', 'otovision', 'phl adm imoveis', 'tatiana meneghel',
    'thtm', 'uro essence', 'brunato & medeiros',
]

def load_companies():
    with urllib.request.urlopen(SHEET_URL) as r:
        content = r.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    return [row for row in reader if row.get('cnpj') and row.get('password')]

def matches(name):
    n = name.lower()
    return any(t in n for t in TARGETS)

def get_month():
    today = date.today()
    first_day = (today - relativedelta(months=1)).replace(day=1)
    last_day = today.replace(day=1) - relativedelta(days=1)
    return first_day.strftime('%d/%m/%Y'), last_day.strftime('%d/%m/%Y')

def run_company(c, start, end, base_dir):
    config = {
        'companies': [c],
        'start': start,
        'end': end,
        'mode': 'emitidas'
    }
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    json.dump(config, tmp)
    tmp.close()
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(base_dir, 'worker.py'), '--config', tmp.name],
            text=True, encoding='utf-8', errors='replace'
        )
        return c['name'], c['cnpj'], result.returncode == 0
    finally:
        try:
            os.unlink(tmp.name)
        except:
            pass

# disable sleep
subprocess.run(['powercfg', '/change', 'standby-timeout-ac', '0'], capture_output=True)
subprocess.run(['powercfg', '/change', 'monitor-timeout-ac', '0'], capture_output=True)

all_companies = load_companies()
selected = [c for c in all_companies if matches(c['name'])]
selected.sort(key=lambda x: x['name'])

start, end = get_month()
print(f'Empresas selecionadas: {len(selected)}')
print(f'Periodo: {start} a {end}')
print(f'Workers: 8')
print(f'Sleep: desativado')
print()
for c in selected:
    print(f"  {c['name']:<60} {c['cnpj']}")
print()
print('Iniciando...')
print('='*60)

base_dir = os.path.dirname(os.path.abspath(__file__))
ok = err = 0
errors = []

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {
        executor.submit(run_company, c, start, end, base_dir): c
        for c in selected
    }
    for future in as_completed(futures):
        name, cnpj, success = future.result()
        if success:
            ok += 1
            print(f'[OK] {name} | {cnpj}', flush=True)
        else:
            err += 1
            errors.append(f'{name} | {cnpj}')
            print(f'[ERRO] {name} | {cnpj}', flush=True)

print('='*60)
print(f'Concluido: {ok} ok | {err} erros')
if errors:
    print()
    print('Empresas com erro:')
    for e in errors:
        print(f'  - {e}')

# re-enable sleep
subprocess.run(['powercfg', '/change', 'standby-timeout-ac', '30'], capture_output=True)
