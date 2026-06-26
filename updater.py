import os, sys, shutil, urllib.request, hashlib

GITHUB_BASE = "https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main"
FILES = [
    "app.py",
    "main.py",
    "worker_visualizar.py",
    "src/auth.py",
    "src/navigation.py",
    "src/downloader.py",
    "src/scraper_visualizar.py",
    "src/generate_visualizar_excel.py",
    "templates/index.html",
    "apply_patch.py",
    "setup_config.py",
    "setup_shortcut.py",
    "nfse_icon.ico",
    "nfse_icon.png",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

updated = 0
for rel in FILES:
    url = f"{GITHUB_BASE}/{rel}?v={hashlib.md5(rel.encode()).hexdigest()[:8]}"
    dest = os.path.join(BASE_DIR, rel.replace("/", os.sep))
    try:
        remote = urllib.request.urlopen(url, timeout=10).read()
        if hashlib.md5(remote).hexdigest() != file_hash(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(remote)
            print(f"[UPDATE] {rel}", flush=True)
            updated += 1
    except Exception as e:
        print(f"[SKIP] {rel}: {e}", flush=True)

if updated:
    for d in [os.path.join(BASE_DIR, "src", "__pycache__"), os.path.join(BASE_DIR, "__pycache__")]:
        shutil.rmtree(d, ignore_errors=True)
    print(f"[UPDATE] {updated} arquivo(s) atualizados", flush=True)
else:
    print("[UPDATE] Nenhuma atualizacao necessaria", flush=True)

patch_path = os.path.join(BASE_DIR, "apply_patch.py")
if os.path.exists(patch_path):
    exec(open(patch_path, encoding="utf-8").read())
