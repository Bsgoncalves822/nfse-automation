import os, sys, subprocess

install_dir = sys.argv[1]

desktop = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Desktop')
if not os.path.exists(desktop):
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')

lnk  = os.path.join(desktop, 'NFS-e Automation.lnk')
vbs  = os.path.join(install_dir, 'launch.vbs')
icon = os.path.join(install_dir, 'nfse_icon.ico')
png  = os.path.join(install_dir, 'nfse_icon.png')

# Prefer the .ico; fall back to .png if it's missing for any reason
icon_location = icon if os.path.exists(icon) else png

ps = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{lnk}')
$s.TargetPath = 'wscript.exe'
$s.Arguments = '"{vbs}"'
$s.WorkingDirectory = '{install_dir}'
$s.IconLocation = '{icon_location}'
$s.WindowStyle = 7
$s.Save()
"""

subprocess.run(['powershell', '-command', ps], capture_output=True)
print('[OK] Shortcut created')
