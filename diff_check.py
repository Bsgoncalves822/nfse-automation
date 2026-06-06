import urllib.request
remote = urllib.request.urlopen("https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/master/generate_fiscal.py", timeout=10).read()
local = open(r"C:\nfse-automation\generate_fiscal.py", "rb").read()
if remote.startswith(b"\xef\xbb\xbf"): remote = remote[3:]
if local.startswith(b"\xef\xbb\xbf"): local = local[3:]
rl = remote.split(b"\n")
ll = local.split(b"\n")
for i, (r, l) in enumerate(zip(rl, ll)):
    if r.strip() != l.strip():
        print("Line", i+1)
        print("remote:", repr(r[:80]))
        print("local: ", repr(l[:80]))
