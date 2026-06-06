content = open(r'C:\nfse-automation\app.py', encoding='utf-8').read()
idx = content.find('generate_fiscal.generate_fiscal_all')
print(content[idx-50:idx+400])
