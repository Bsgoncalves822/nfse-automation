import time
from datetime import date
from dateutil.relativedelta import relativedelta

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"

def get_previous_month_range():
    today = date.today()
    first_day = (today - relativedelta(months=1)).replace(day=1)
    last_day = today.replace(day=1) - relativedelta(days=1)
    return first_day.strftime("%d/%m/%Y"), last_day.strftime("%d/%m/%Y")

def is_portal_error(page):
    """Check if the current page is showing a portal error."""
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

def navigate_to_recebidas(page, max_retries=10, wait_seconds=5):
    """Navigate to Notas Recebidas with retry on portal errors."""
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"[AVISO] Portal indisponivel, tentando novamente ({attempt}/{max_retries})...", flush=True)
                time.sleep(wait_seconds)
                page.reload()
            else:
                page.goto(f"{BASE_URL}/Notas/Recebidas", timeout=120000)

            try:
                page.wait_for_load_state("networkidle", timeout=120000)
            except:
                pass

            if is_portal_error(page):
                continue

            # Wait for the date input which confirms page loaded correctly
            try:
                page.wait_for_selector("#datainicio", timeout=120000)
                print("[OK] Pagina Recebidas carregada", flush=True)
                return True
            except:
                if attempt < max_retries:
                    print(f"[AVISO] Pagina Recebidas nao carregou completamente (tentativa {attempt}/{max_retries}), recarregando...", flush=True)
                    continue

        except Exception as e:
            print(f"[AVISO] Erro ao navegar para Recebidas (tentativa {attempt}/{max_retries}): {str(e)[:80]}", flush=True)
            if attempt < max_retries:
                time.sleep(wait_seconds)
            continue

    print("[ERRO] Nao foi possivel acessar Notas Recebidas apos todas as tentativas.", flush=True)
    return False

def apply_filter(page, start=None, end=None, max_retries=10, wait_seconds=5):
    """Apply date filter with retry on portal errors."""
    if not start or not end:
        start, end = get_previous_month_range()

    for attempt in range(1, max_retries + 1):
        try:
            page.evaluate(f"""
                document.getElementById('datainicio').value = '{start}';
                document.getElementById('datainicio').dispatchEvent(new Event('change'));
                document.getElementById('datafim').value = '{end}';
                document.getElementById('datafim').dispatchEvent(new Event('change'));
            """)
            page.click("button[type='submit']")

            try:
                page.wait_for_load_state("networkidle", timeout=120000)
            except:
                pass

            if is_portal_error(page):
                print(f"[AVISO] Portal mostrou erro apos filtro (tentativa {attempt}/{max_retries}), recarregando...", flush=True)
                time.sleep(wait_seconds)
                # Navigate back to recebidas and try again
                try:
                    page.goto(f"{BASE_URL}/Notas/Recebidas", timeout=120000)
                    page.wait_for_selector("#datainicio", timeout=120000)
                except:
                    pass
                continue

            print(f"[OK] Filtro aplicado: {start} a {end}", flush=True)
            return True

        except Exception as e:
            print(f"[AVISO] Erro ao aplicar filtro (tentativa {attempt}/{max_retries}): {str(e)[:80]}", flush=True)
            if attempt < max_retries:
                time.sleep(wait_seconds)
                try:
                    page.goto(f"{BASE_URL}/Notas/Recebidas", timeout=120000)
                    page.wait_for_selector("#datainicio", timeout=120000)
                except:
                    pass
            continue

    print(f"[ERRO] Nao foi possivel aplicar filtro apos todas as tentativas.", flush=True)
    return False
