content = open(r'C:\nfse-automation\app.py', encoding='utf-8').read()
idx = content.find('current_dl = s')
print(content[idx:idx+400])
