content = open(r'C:\nfse-automation\app.py', encoding='utf-8').read()
print('has ZIP print:', '[ZIP] selected=' in content)
idx = content.find('def run_zip')
chunk = content[idx:idx+400]
print(chunk)
