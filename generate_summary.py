import sys
import json
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def get_empresas_dir():
    settings_path = Path(__file__).parent / "config" / "settings.json"
    if not settings_path.exists():
        print("settings.json nao encontrado.")
        sys.exit(1)
    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)
    downloads_path = settings.get("downloads_path")
    if not downloads_path:
        print("downloads_path nao definido em settings.json.")
        sys.exit(1)
    return Path(downloads_path) / "Empresas"

def generate_summary(filter_names=None):
    empresas_dir = get_empresas_dir()
    if not empresas_dir.exists():
        print(f"Pasta nao encontrada: {empresas_dir}")
        sys.exit(1)

    rows = []
    for company_dir in sorted(empresas_dir.iterdir()):
        if not company_dir.is_dir():
            continue
        if filter_names and company_dir.name not in filter_names:
            continue
        for month_dir in sorted([d for d in company_dir.iterdir() if d.is_dir()]):
            federal_xmls = month_dir / "federal" / "xmls"
            xml_count = len([f for f in federal_xmls.iterdir() if f.suffix.lower() == ".xml"]) if federal_xmls.exists() else 0
            rows.append((company_dir.name, month_dir.name, xml_count))

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo NFS-e"

    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill("solid", start_color="1F4E79")
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells("A1:C1")
    ws["A1"].value = f"Resumo NFS-e com Retencao Federal — gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws["A1"].font = Font(name="Arial", bold=True, size=12, color="1F4E79")
    ws["A1"].alignment = center
    ws.row_dimensions[1].height = 22

    for col, h in enumerate(["Nome da Empresa", "Periodo (MM-YYYY)", "Notas com Retencao Federal (XMLs)"], 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    for i, (name, period, count) in enumerate(rows, start=3):
        fill = PatternFill("solid", start_color="EBF3FB") if i % 2 == 0 else PatternFill("solid", start_color="FFFFFF")
        for col, val in enumerate([name, period, count], 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = Font(name="Arial", size=10)
            cell.fill = fill
            cell.border = border
            cell.alignment = center if col > 1 else left

    total_row = len(rows) + 3
    ws.cell(row=total_row, column=1, value="TOTAL").font = Font(name="Arial", bold=True, size=10)
    ws.cell(row=total_row, column=1).alignment = left
    ws.cell(row=total_row, column=1).border = border
    ws.cell(row=total_row, column=2, value="").border = border
    total_cell = ws.cell(row=total_row, column=3, value=f"=SUM(C3:C{total_row-1})")
    total_cell.font = Font(name="Arial", bold=True, size=10)
    total_cell.alignment = center
    total_cell.border = border
    for col in [1, 2, 3]:
        ws.cell(row=total_row, column=col).fill = PatternFill("solid", start_color="D6E4F0")
        ws.cell(row=total_row, column=col).border = border

    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 35

    output_path = empresas_dir / "resumo_nfse.xlsx"
    wb.save(output_path)
    print(f"Resumo salvo em: {output_path}")
    print(f"{len(rows)} linha(s) processada(s).")

if __name__ == "__main__":
    generate_summary()