import json
import os
from playwright.sync_api import sync_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(SCRIPT_DIR, "config", "settings.json")

with open(settings_path, encoding="utf-8") as f:
    settings = json.load(f)

EXTENSION_PATH = settings["extension_path"]
PROFILE_PATH = settings["profile_path"]
EMAIL = "ezequielorproconfiscal@gmail.com"
EXTENSION_ID = "ajkbjdkeaacaaaagmpnocomjeoeidagp"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_PATH,
        headless=False,
        args=[
            f"--disable-extensions-except={EXTENSION_PATH}",
            f"--load-extension={EXTENSION_PATH}",
        ]
    )
    page = context.new_page()
    page.goto(f"chrome-extension://{EXTENSION_ID}/popup.html")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)

    try:
        # check if already active
        status = page.query_selector("text=ACTIVE")
        if status:
            print("[OK] Licenca ja ativa")
            context.close()
            exit(0)

        # try to activate
        email_input = page.query_selector("input[placeholder*='email']")
        if email_input:
            page.fill("input[placeholder*='email']", EMAIL)
            page.wait_for_timeout(500)
            page.click("button:has-text('Validar')")
            page.wait_for_timeout(4000)
            print("[OK] Licenca ativada com sucesso")
        else:
            print("[OK] Licenca ja configurada")
    except Exception as e:
        print(f"[AVISO] {e}")

    context.close()