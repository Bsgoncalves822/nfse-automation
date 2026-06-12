import json
import os
import shutil
import tempfile
import time

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.json")
    with open(os.path.abspath(settings_path), encoding="utf-8") as f:
        return json.load(f)

def create_browser(playwright):
    settings = load_settings()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=settings["profile_path"],
        headless=False,
        args=[
            f"--disable-extensions-except={settings['extension_path']}",
            f"--load-extension={settings['extension_path']}",
        ]
    )
    return context

def create_browser_for_company(playwright, temp_dir):
    settings = load_settings()
    profile_copy = os.path.join(temp_dir, "profile")
    shutil.copytree(settings["profile_path"], profile_copy)
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=profile_copy,
        headless=False,
        args=[
            f"--disable-extensions-except={settings['extension_path']}",
            f"--load-extension={settings['extension_path']}",
        ]
    )
    return context

def is_portal_error(page):
    try:
        content = page.content()
        if any(x in content for x in [
            "The service is unavailable",
            "502 - Web server",
            "Server Error",
            "Bad Gateway",
            "Service Unavailable",
        ]):
            return True
        if "unavailable" in content.lower() and "service" in content.lower():
            return True
        return False
    except:
        return False

def login(context, cnpj, password, name="", max_retries=10, wait_seconds=5):
    for attempt in range(1, max_retries + 1):
        page = context.new_page()
        try:
            if attempt > 1:
                print(f"[AVISO] Tentando login novamente ({attempt}/{max_retries})...", flush=True)
                time.sleep(wait_seconds)

            page.goto(f"{BASE_URL}/Login", timeout=120000)
            try:
                page.wait_for_load_state("networkidle", timeout=120000)
            except:
                pass

            if is_portal_error(page):
                print(f"[AVISO] Portal indisponivel no login ({attempt}/{max_retries}), aguardando...", flush=True)
                page.close()
                time.sleep(wait_seconds)
                continue

            try:
                page.wait_for_selector("#Inscricao", timeout=120000)
            except:
                print(f"[AVISO] Pagina de login nao carregou ({attempt}/{max_retries}), tentando novamente...", flush=True)
                page.close()
                continue

            page.fill("#Inscricao", cnpj)
            page.fill("#Senha", password)
            page.click("button[type='submit']")

            try:
                page.wait_for_url(lambda url: "Login" not in url, timeout=120000)
            except:
                error_visible = page.locator("text=/usu.rio e\\/ou senha inv.lid/i").is_visible()
                if error_visible:
                    print(f"[SENHA ERRADA] {name} | CNPJ: {cnpj}", flush=True)
                    page.close()
                    return None
                print(f"[AVISO] Login nao redirecionou ({attempt}/{max_retries}), tentando novamente...", flush=True)
                page.close()
                continue

            if is_portal_error(page):
                print(f"[AVISO] Portal erro apos login ({attempt}/{max_retries}), tentando novamente...", flush=True)
                page.close()
                time.sleep(wait_seconds)
                continue

            print(f"[OK] Login: {name} ({cnpj})", flush=True)
            return page

        except Exception as e:
            print(f"[AVISO] Erro no login ({attempt}/{max_retries}): {str(e)[:80]}", flush=True)
            try:
                page.close()
            except:
                pass
            if attempt < max_retries:
                time.sleep(wait_seconds)
            continue

    print(f"[ERRO] Login falhou apos {max_retries} tentativas: {name}", flush=True)
    return None
