import json
import os
import shutil
import tempfile

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.json")
    with open(os.path.abspath(settings_path)) as f:
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

def login(context, cnpj, password, name=""):
    page = context.new_page()
    page.goto(f"{BASE_URL}/Login")
    page.wait_for_selector("#Inscricao")
    page.fill("#Inscricao", cnpj)
    page.fill("#Senha", password)
    page.click("button[type='submit']")
    try:
        page.wait_for_url(lambda url: "Login" not in url, timeout=10000)
        print(f"[OK] Login: {name} ({cnpj})", flush=True)
        return page
    except:
        error_visible = page.locator("text=Usuário e/ou senha inválidos").is_visible()
        if error_visible:
            print(f"[SENHA ERRADA] {name} | CNPJ: {cnpj}", flush=True)
        else:
            print(f"[ERRO] Login falhou: {name} | CNPJ: {cnpj}", flush=True)
        page.close()
        return None