content = open(r'C:\nfse-automation\app.py', encoding='utf-8').read()
idx = content.find('def auto_patch_settings')
print(content[idx:idx+600])
