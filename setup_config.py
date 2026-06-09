import json, os, sys

install_dir = sys.argv[1]
python_exe = sys.executable

path = os.path.join(install_dir, 'config', 'settings.json')
with open(path, encoding='utf-8') as f:
    s = json.load(f)

# point to the versioned extension folder if it exists
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

vbs = f'''Set WShell = CreateObject("WScript.Shell")
Set http = CreateObject("MSXML2.XMLHTTP")

' Check if Flask is already running
Dim alreadyRunning
alreadyRunning = False
On Error Resume Next
http.Open "GET", "http://localhost:5000/health", False
http.Send
If http.Status = 200 Then
    alreadyRunning = True
End If
On Error GoTo 0

If Not alreadyRunning Then
    ' Run updater first (silently)
    WShell.Run "{python_exe} {install_dir}\\updater.py", 0, True

    ' Start Flask
    WShell.Run "{python_exe} {install_dir}\\app.py", 0, False
    WScript.Sleep 1000

    ' Wait until Flask is ready
    Do
        WScript.Sleep 2000
        On Error Resume Next
        Set http = CreateObject("MSXML2.XMLHTTP")
        http.Open "GET", "http://localhost:5000/health", False
        http.Send
        If http.Status = 200 Then
            Exit Do
        End If
        On Error GoTo 0
    Loop
End If

' Open browser
WShell.Run "http://localhost:5000", 1, False
'''

with open(os.path.join(install_dir, 'launch.vbs'), 'w', encoding='utf-8') as f:
    f.write(vbs)

print(f'[OK] Config updated, Python: {python_exe}')

