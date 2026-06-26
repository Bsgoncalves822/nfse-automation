import json, os, sys

install_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
python_exe = sys.executable

config_dir = os.path.join(install_dir, 'config')
os.makedirs(config_dir, exist_ok=True)

path = os.path.join(config_dir, 'settings.json')

# Seed defaults if file doesn't exist
if not os.path.exists(path):
    desktop = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Desktop')
    if not os.path.exists(desktop):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    defaults = {
        'extension_path': '',
        'profile_path': '',
        'python_exe': python_exe,
        'downloads_path': os.path.join(desktop, 'NFESAUTOMATION'),
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(defaults, f, indent=2)

with open(path, encoding='utf-8') as f:
    s = json.load(f)

ext_base = os.path.join(install_dir, 'extension')
ext_versioned = os.path.join(ext_base, '2.0.5_0')
s['extension_path'] = ext_versioned if os.path.exists(ext_versioned) else ext_base
s['profile_path'] = os.path.join(install_dir, 'chrome-profile')
s['python_exe'] = python_exe

desktop = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Desktop')
if not os.path.exists(desktop):
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
s['downloads_path'] = os.path.join(desktop, 'NFESAUTOMATION')

with open(path, 'w', encoding='utf-8') as f:
    json.dump(s, f, indent=2)

# Seed companies and groups if missing
for fname, default in [('companies.json', '[]'), ('groups.json', '[]')]:
    fpath = os.path.join(config_dir, fname)
    if not os.path.exists(fpath):
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(default)

vbs = f'''Set WShell = CreateObject("WScript.Shell")
Set http = CreateObject("MSXML2.XMLHTTP")

Dim alreadyRunning
alreadyRunning = False
On Error Resume Next
http.Open "GET", "http://127.0.0.1:5000/health", False
http.Send
If http.Status = 200 Then
    alreadyRunning = True
End If
On Error GoTo 0

If Not alreadyRunning Then
    Set cmdShell = WShell.Exec("""{python_exe}" "{install_dir}\\updater.py""")
    startTime = Timer
    Do
        WScript.Sleep 500
        If cmdShell.Status = 1 Then
            Exit Do
        End If
        If Timer - startTime > 45 Then
            On Error Resume Next
            cmdShell.Terminate
            On Error GoTo 0
            Exit Do
        End If
    Loop

    WShell.Run """{python_exe}" "{install_dir}\\app.py""", 0, False
    WScript.Sleep 1000

    Do
        WScript.Sleep 2000
        On Error Resume Next
        Set http = CreateObject("MSXML2.XMLHTTP")
        http.Open "GET", "http://127.0.0.1:5000/health", False
        http.Send
        If http.Status = 200 Then
            Exit Do
        End If
        On Error GoTo 0
    Loop
End If

WShell.Run "http://127.0.0.1:5000", 1, False
'''

with open(os.path.join(install_dir, 'launch.vbs'), 'w', encoding='utf-8') as f:
    f.write(vbs)

print(f'[OK] Config updated, Python: {python_exe}')
