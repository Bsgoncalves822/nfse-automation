import re

with open(r"C:\nfse-automation\app.py", encoding="utf-8") as f:
    content = f.read()

old = '''    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for company in selected_companies:
            safe_name = company['name'].replace('/', '_').replace('\\\\', '_').replace(':', '_')
            company_dir = os.path.join(downloads_path, company['accountant'], safe_name, month)
            if os.path.exists(company_dir):
                for root, dirs, files in os.walk(company_dir):
                    # skip old pdfs/xmls folders at root level
                    rel_root = os.path.relpath(root, company_dir)
                    if rel_root.split(os.sep)[0] in ['pdfs', 'xmls']:
                        continue
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, downloads_path)
                        zf.write(file_path, arcname)
    return send_file(zip_path'''

new = '''    sys.path.insert(0, BASE_DIR)
    try:
        import generate_summary
        generate_summary.generate_summary()
    except Exception as e:
        print(f"[AVISO] Erro ao gerar resumo: {e}")
    resumo_path = os.path.join(downloads_path, 'Empresas', 'resumo_nfse.xlsx')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for company in selected_companies:
            safe_name = company['name'].replace('/', '_').replace('\\\\', '_').replace(':', '_')
            company_dir = os.path.join(downloads_path, company['accountant'], safe_name, month)
            if os.path.exists(company_dir):
                for root, dirs, files in os.walk(company_dir):
                    # skip old pdfs/xmls folders at root level
                    rel_root = os.path.relpath(root, company_dir)
                    if rel_root.split(os.sep)[0] in ['pdfs', 'xmls']:
                        continue
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, downloads_path)
                        zf.write(file_path, arcname)
        if os.path.exists(resumo_path):
            zf.write(resumo_path, os.path.join('Empresas', 'resumo_nfse.xlsx'))
    return send_file(zip_path'''

if old in content:
    content = content.replace(old, new)
    with open(r"C:\nfse-automation\app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Done")
else:
    print("MATCH NOT FOUND - no changes made")
