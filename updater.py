import os, sys, shutil, urllib.request, hashlib

GITHUB_BASE = "https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/master"
FILES = [
    (GITHUB_BASE + "/src/auth.py",          "src/auth.py"),
    (GITHUB_BASE + "/src/navigation.py",    "src/navigation.py"),
    (GITHUB_BASE + "/src/downloader.py",    "src/downloader.py"),
    (GITHUB_BASE + "/worker.py",            "worker.py"),
    (GITHUB_BASE + "/app.py",               "app.py"),
    (GITHUB_BASE + "/main.py",              "main.py"),
    (GITHUB_BASE + "/templates/index.html", "templates/index.html"),
    (GITHUB_BASE + "/apply_patch.py",       "apply_patch.py"),
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

updated = 0
for url, rel in FILES:
    dest = os.path.join(BASE_DIR, rel.replace("/", os.sep))
    try:
        remote = urllib.request.urlopen(url, timeout=10).read()
        if hashlib.md5(remote).hexdigest() != file_hash(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(remote)
            print(f"[UPDATE] {rel}", flush=True)
            updated += 1
    except:
        pass

if updated:
    for d in [os.path.join(BASE_DIR, "src", "__pycache__"), os.path.join(BASE_DIR, "__pycache__")]:
        shutil.rmtree(d, ignore_errors=True)
    print(f"[UPDATE] {updated} arquivo(s) atualizados", flush=True)

# Always run apply_patch to ensure correct files regardless of CDN cache
patch_path = os.path.join(BASE_DIR, "apply_patch.py")
if os.path.exists(patch_path):
    exec(open(patch_path, encoding="utf-8").read())
