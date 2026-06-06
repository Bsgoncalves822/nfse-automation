import urllib.request, os

base = r'C:\nfse-automation'
github = 'https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/master'
files = ['worker.py', 'src/downloader.py', 'src/auth.py', 'main.py', 'app.py', 'generate_summary.py', 'generate_fiscal.py']

for f in files:
    local = open(os.path.join(base, f.replace('/', os.sep)), 'rb').read()
    if local.startswith(b'\xef\xbb\xbf'): local = local[3:]
    remote = urllib.request.urlopen(github + '/' + f, timeout=10).read()
    status = 'OK' if local.strip() == remote.strip() else 'MISMATCH'
    print(f + ': ' + status + ' (' + str(len(local)) + ' local, ' + str(len(remote)) + ' remote)')
