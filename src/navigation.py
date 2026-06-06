from datetime import date
from dateutil.relativedelta import relativedelta

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"

def get_previous_month_range():
    today = date.today()
    first_day = (today - relativedelta(months=1)).replace(day=1)
    last_day = today.replace(day=1) - relativedelta(days=1)
    return first_day.strftime("%d/%m/%Y"), last_day.strftime("%d/%m/%Y")

def navigate_to_recebidas(page):
    page.goto(f"{BASE_URL}/Notas/Recebidas")
    page.wait_for_selector("#datainicio", timeout=120000)
    print("[OK] Pagina Recebidas carregada")

def apply_filter(page, start=None, end=None):
    if not start or not end:
        start, end = get_previous_month_range()

    page.evaluate(f"""
        document.getElementById('datainicio').value = '{start}';
        document.getElementById('datainicio').dispatchEvent(new Event('change'));
        document.getElementById('datafim').value = '{end}';
        document.getElementById('datafim').dispatchEvent(new Event('change'));
    """)

    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    print(f"[OK] Filtro aplicado: {start} a {end}")
