"""
NFS-e Automation - Patch Script
Downloads and applies all critical files from GitHub main.
Run: python apply_patch.py
"""
import os, sys, urllib.request, shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GITHUB = "https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main"

def download(url, dest):
    try:
        data = urllib.request.urlopen(url, timeout=15).read()
        # Strip BOM if present
        if data.startswith(b'\xef\xbb\xbf'):
            data = data[3:]
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        print(f'[WARN] Could not download {url}: {e}')
        return False

FILES = [
    ('worker_visualizar.py',              'worker_visualizar.py'),
    ('src/auth.py',                       'src/auth.py'),
    ('src/downloader.py',                 'src/downloader.py'),
    ('src/navigation.py',                 'src/navigation.py'),
    ('src/scraper_visualizar.py',         'src/scraper_visualizar.py'),
    ('src/generate_visualizar_excel.py',  'src/generate_visualizar_excel.py'),
    ('app.py',                            'app.py'),
    ('main.py',                           'main.py'),
    # NOTE: templates/index.html intentionally NOT included here.
    # updater.py handles it with cache-busting query params; apply_patch.py's
    # plain urlopen can serve a stale CDN-cached copy and overwrite the correct
    # version updater.py just fetched.
]

print('Applying patches...')
for rel, dest_rel in FILES:
    url  = f'{GITHUB}/{rel}'
    dest = os.path.join(BASE_DIR, dest_rel.replace('/', os.sep))
    if download(url, dest):
        print(f'[OK] {dest_rel}')
    else:
        print(f'[FAIL] {dest_rel}')

# Clear pycache
for d in [os.path.join(BASE_DIR, '__pycache__'), os.path.join(BASE_DIR, 'src', '__pycache__')]:
    shutil.rmtree(d, ignore_errors=True)

print('\nAll patches applied.')
