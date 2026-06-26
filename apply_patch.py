"""
NFS-e Automation - Patch Script
Runs after updater.py on every launch.
"""
import os, sys, urllib.request, hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GITHUB_BASE = "https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main"

def pull(rel):
    url = f"{GITHUB_BASE}/{rel}"
    dest = os.path.join(BASE_DIR, rel.replace("/", os.sep))
    try:
        remote = urllib.request.urlopen(url, timeout=10).read()
        current = open(dest, "rb").read() if os.path.exists(dest) else b""
        if hashlib.md5(remote).hexdigest() != hashlib.md5(current).hexdigest():
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(remote)
            print(f"[PATCH] {rel}", flush=True)
    except Exception as e:
        print(f"[PATCH SKIP] {rel}: {e}", flush=True)

# Always self-heal these critical files
pull("updater.py")
pull("setup_config.py")
pull("app.py")
pull("main.py")
pull("worker_visualizar.py")
pull("src/auth.py")
pull("src/navigation.py")
pull("src/scraper_visualizar.py")
pull("src/generate_visualizar_excel.py")
pull("templates/index.html")

print("[PATCH] Done", flush=True)
