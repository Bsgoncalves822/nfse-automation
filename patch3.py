content = open(r'C:\nfse-automation\app.py', encoding='utf-8').read()
# Find run_zip and add debug after selected line
old = "    selected = data.get('companies', [])\n    mode     = data.get('mode', 'reinf')\n\n    try:\n        d1"
new = "    selected = data.get('companies', [])\n    mode     = data.get('mode', 'reinf')\n    print('[ZIP] selected=' + str(selected[:2]) + ' total=' + str(len(selected)), flush=True)\n\n    try:\n        d1"
if old in content:
    open(r'C:\nfse-automation\app.py', 'w', encoding='utf-8').write(content.replace(old, new))
    print('patched')
else:
    print('NOT FOUND')
    # show what IS around that area
    idx = content.find("selected = data.get('companies'")
    print(repr(content[idx:idx+200]))
