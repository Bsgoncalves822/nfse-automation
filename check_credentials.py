import csv
import io
import requests
from playwright.sync_api import sync_playwright
from src.auth import create_browser, login

SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/1MI4xI6rSWfYVYTtPfXOzNPon-AGq0KXh/export?format=csv'

def load_companies():
    r = requests.get(SHEET_CSV_URL)
    reader = csv.DictReader(io.StringIO(r.text))
    companies = []
    for row in reader:
        if row.get("cnpj") and row.get("password"):
            companies.append({
                "name":      row["name"],
                "cnpj":      row["cnpj"],
                "password":  row["password"],
                "accountant": row.get("accountant", "")
            })
    return companies

def main():
    companies = load_companies()
    print(f"\nVerificando credenciais para {len(companies)} empresa(s)...\n")
    print("=" * 50)

    results = {"ok": [], "erro": []}

    with sync_playwright() as p:
        context = create_browser(p)
        for company in companies:
            name     = company["name"]
            cnpj     = company["cnpj"]
            password = company["password"]
            try:
                page = login(context, cnpj, password, name)
                if page:
                    results["ok"].append(name)
                    page.close()
                else:
                    results["erro"].append((name, cnpj))
            except Exception as e:
                print(f"[CRASH] {name} | {cnpj} | {e}")
                results["erro"].append((name, cnpj))
                try:
                    context.close()
                except:
                    pass
                context = create_browser(p)
        context.close()

    print(f"\n{'='*50}")
    print(f"RESULTADO FINAL")
    print(f"  OK:    {len(results['ok'])}")
    print(f"  ERRO:  {len(results['erro'])}")

    if results["erro"]:
        print(f"\nEmpresas com problema:")
        for name, cnpj in results["erro"]:
            print(f"  - {name} | CNPJ: {cnpj}")

if __name__ == "__main__":
    main()