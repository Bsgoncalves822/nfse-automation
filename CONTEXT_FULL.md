# NFS-e Automation — Full Architecture & Session Context
*Last updated: June 9, 2026 — for use with Deepseek or other AI assistants*

---

## What This Is

Internal automation tool for ORPROCON, an accounting firm in Tubarão, SC, Brazil.
Built by Bryan Gonçalves (junior developer placed at ORPROCON via outsourcing).

**Purpose:** Automate monthly retrieval of NFS-e (Notas Fiscais de Serviço Eletrônico) from the federal portal (`nfse.gov.br/EmissorNacional`) for ~624 accounting clients. For each company: login via Playwright, navigate to Notas Recebidas or Emitidas, scrape all pages, download XMLs+PDFs via ModalCaptcha endpoints, classify notes (federal/municipal/canceladas), generate Excel summaries, output organized ZIPs.

**GitHub:** `https://github.com/Bsgoncalves822/nfse-automation` (public, main branch)
**Production path:** `C:\nfse-automation\` on Bryan's machine
**Output:** `Desktop\NFESAUTOMATION\Empresas\{company}\{MM-YYYY}\`
**Deployed on:** 5 machines at ORPROCON

---

## Tech Stack

| Component | Detail |
|---|---|
| Backend | Python 3.11–3.13, Flask (port 5000) |
| Browser automation | Playwright (sync API), Chromium |
| Excel output | openpyxl |
| Config | JSON (`config/settings.json`) |
| Company list | Google Sheet ID `1MI4xI6rSWfYVYTtPfXOzNPon-AGq0KXh` (CSV export) |
| Auto-update | `updater.py` + `apply_patch.py` via `launch.vbs` |

---

## File Structure

```
C:\nfse-automation\
├── app.py                    # Flask server, all API routes
├── main.py                   # CLI orchestrator, ThreadPoolExecutor (3 workers)
├── worker.py                 # Per-company Playwright subprocess
├── worker_certificado.py     # Headful manual login for certificado digital companies
├── generate_fiscal.py        # XML parsing + fiscal xlsx + Batista TXT
├── generate_summary.py       # resumo_nfse.xlsx across all companies
├── updater.py                # Auto-updater (pulls from GitHub main, cache-busting)
├── apply_patch.py            # Secondary patcher (also pulls from GitHub main)
├── setup_config.py           # Patches settings.json + generates launch.vbs at install
├── setup_shortcut.py         # Creates desktop shortcut
├── activate_license.py       # Legacy — extension license (extension is dead, kept for compat)
├── dump-context.ps1          # Dumps all source files to single MD for AI sessions
├── launch.vbs                # Silent Flask start + runs updater first
├── install.bat / install_part1.bat / install_part2.bat
├── requirements.txt          # playwright openpyxl python-dateutil schedule flask
│
├── config\
│   ├── settings.json         # Paths (auto-patched by setup_config.py)
│   ├── companies.json        # Fallback if Google Sheets unavailable
│   ├── groups.json           # Accountant-defined company groups
│   └── cidades_lookup.json   # IBGE city code lookup
│
├── src\
│   ├── auth.py               # Browser context creation, login with 10-retry loop
│   ├── navigation.py         # navigate_to_recebidas, navigate_to_emitidas, apply_filter
│   ├── downloader.py         # XML/PDF downloads, classification, Excel generation
│   └── parser.py             # Legacy — parse Recebidas Excel (no longer used in main flow)
│
├── templates\
│   └── index.html            # Full UI — RE-INF, Emitidas, Certificado Digital tabs
│
├── extension\
│   └── 2.0.5_0\              # Dead Chrome extension (kept for profile loading compat)
│
└── chrome-profile\           # Persistent Chromium profile
```

---

## Auto-Update Architecture

### How it works on each launch:
1. `launch.vbs` runs `updater.py` **synchronously** (waits for it to finish) — **KNOWN SINGLE POINT OF FAILURE**: if GitHub is down, Flask never starts. Fix needed: wrap with `On Error Resume Next` in VBS.
2. `updater.py` fetches tracked files from GitHub `main` branch with cache-busting (`?v={timestamp}`) to bypass CDN, compares MD5, overwrites if different, then runs `apply_patch.py`
3. `apply_patch.py` also fetches from GitHub `main` (BOM is stripped before exec)
4. Flask starts
5. Browser opens at `localhost:5000`

### Files tracked by updater.py:
- `src/auth.py`, `src/navigation.py`, `src/downloader.py`
- `worker.py`, `app.py`, `main.py`
- `templates/index.html`
- `apply_patch.py`

### Files tracked by apply_patch.py:
- `worker.py`, `src/auth.py`, `src/downloader.py`, `src/navigation.py`
- `app.py`, `main.py`, `generate_summary.py`, `generate_fiscal.py`

### NOT auto-updated (manual deploy required):
- `worker_certificado.py` — needs to be added to FILES list in both updater.py and apply_patch.py
- `updater.py` itself — only updated if `master` branch is kept in sync with `main`
- `setup_config.py`, `launch.vbs` — install-time only

### Branch situation:
- Active development: `main`
- Old deploy target: `master` (now force-pushed to match `main` — `git push origin main:master --force`)
- Dead branch: `feature/emitidas` (merged into main June 2026)

---

## Download Flow

### Recebidas (RE-INF mode):
```
login() → navigate_to_recebidas() → apply_filter(start, end)
→ get_download_urls()     ← scrapes all pages via .paginacao .descricao + tr[data-chave]
→ download_files()        ← hits ModalCaptcha endpoints, classifies, generates Excel
```

### Emitidas mode:
```
login() → navigate_to_emitidas() → apply_filter(start, end)
→ download_files_emitidas()  ← same ModalCaptcha flow, different Excel format
```

### Certificado Digital (manual login):
```
Open headful Chromium → user logs in with A1/A3 certificate manually
→ poll sessionStorage.accessToken JWT → decode to get CNPJ
→ lookup company in Google Sheet by CNPJ
→ navigate_to_recebidas() → apply_filter() → get_download_urls() → download_files()
```

### Download endpoints (ModalCaptcha):
- XML: `GET https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/NFSe/{chave}`
- PDF: `GET https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/DANFSe/{chave}`
- These work via Playwright's `page.request.get()` with `Referer` header
- **Do NOT work via browser fetch() / extension context** — portal blocks XHR/fetch (Sec-Fetch-Mode check server-side). This is why the Chrome extension approach was abandoned.

### Pagination:
- Portal has fixed ~15 rows per page, no pageSize override
- `.paginacao .descricao` contains "X de Y registros" → calculate total pages
- `tr[data-chave]` selector gets note rows
- All pages fetched sequentially (parallel fetching causes portal rate limiting)
- Internal SERPRO REST API (`window.UrlRest`) is on private network — not accessible

---

## Classification Rules (CRITICAL — do not change without full audit)

```python
# FEDERAL retention — TRUE when ANY of:
vRetIRRF > 0
vRetCSLL > 0
vRetINSS > 0
vRetCP   > 0
(tpRetPisCofins == '1' AND (vPis > 0 OR vCofins > 0))

# MUNICIPAL retention
tpRetISSQN == '1'  AND  NOT is_federal

# CANCELADA
cStat != '100'  (includes 101, not just 107-109)

# CBS (vCBSTot/vCBS) and IBS (vIBSTot) = reforma tributária
# These are ISS replacements — present in Excel data but DO NOT count toward is_federal
# 765 notes were misclassified in 05-2026 due to flat FEDERAL_FIELDS check — fixed June 2026
```

### Output folder structure per company/month:
```
{Empresas}/{Company}/{MM-YYYY}/
├── all/xmls/          ← every XML regardless of classification
├── all/pdfs/          ← every PDF
├── federal/xmls/      ← federal retention only
├── federal/pdfs/
├── municipal/xmls/    ← ISS retention only
├── municipal/pdfs/
├── canceladas/xmls/   ← cStat != '100'
└── Recebidas_NFS-e_{company}_{month}.xlsx
```

---

## UI Tabs (index.html)

| Tab | Mode | Description |
|---|---|---|
| RE-INF | `reinf` | Downloads recebidas, classifies federal/municipal, generates Excel |
| Emitidas | `emitidas` | Downloads emitidas, generates tomador Excel |
| Certificado Digital | N/A | Opens headful browser for manual certificado login |

Left panel (company selector) hides automatically on Certificado Digital tab.

### Flask API endpoints:
- `GET /` — serves index.html
- `GET /health` — returns "ok" (used by launch.vbs health check)
- `GET /api/companies` — loads from Google Sheets (falls back to companies.json)
- `POST /api/run/stream` — SSE streaming run (reinf or emitidas mode)
- `POST /api/run/zip` — generates and downloads ZIP after run
- `POST /api/run/certificado` — triggers headful certificado worker

---

## Known Issues & Single Points of Failure

### Critical SPOFs:
1. **`launch.vbs` updater call is blocking** — if GitHub unreachable, Flask never starts. Fix: `On Error Resume Next` around updater call in `launch.vbs` template in `setup_config.py`
2. **Google Sheets company list** — if sheet unavailable (502/quota), falls back to stale `companies.json`
3. **Port 5000 conflict** — if anything else uses 5000, `launch.vbs` polls health forever
4. **`temp_run.json` race condition** — concurrent UI runs overwrite each other. Fix: use UUID temp filenames

### Security issues (known, not yet fixed):
- Passwords in plaintext in Google Sheet (public CSV URL)
- Flask has no authentication — any process on the machine can trigger runs
- `updater.py` executes arbitrary code from GitHub via `exec()` — if repo compromised, all machines execute attacker code
- `config/companies.json` should never be in deploy zip (fixed in V7)

### Architecture issues (known, not yet fixed):
- `worker_certificado.py` not in auto-updater FILES lists
- `generate_fiscal_all()` path bug — iterates wrong directory structure
- `load_companies()` hits Google Sheets on every API call — no caching
- `chrome-profile/` copied per worker (25x) — slow and disk-intensive
- No keepalive for long runs — sessions expire mid-run on large companies

---

## Deployment History

| Version | Key change | Auto-updates? |
|---|---|---|
| V4 | First working version | ❌ |
| V5 | Encoding fixes, patched on User's machine | ❌ |
| V6 | Has `updater.py` but `launch.vbs` never calls it | ❌ |
| V7 | `launch.vbs` calls `updater.py` first — **first truly self-updating version** | ✅ |

### Deploy workflow going forward:
1. Edit files in `C:\nfse-automation\`
2. Copy to `C:\Users\bryan\Downloads\nfse-automation-setup\nfse-automation\`
3. `git add / commit / push` to `main`
4. `git push origin main:master --force` (keeps master in sync for old installs)
5. All machines auto-update on next restart

### To deploy V7 to a new machine:
1. Extract `nfse-automation-deployV7.zip` to Downloads
2. Run `install.bat` (not as admin)
3. Wait for Chromium install (~5 mins)
4. App opens at `localhost:5000`
5. All future updates automatic via GitHub

---

## Pending Tasks (priority order)

1. **Fix `launch.vbs` SPOF** — add `On Error Resume Next` around updater call in `setup_config.py`
2. **Add `worker_certificado.py` to auto-updater FILES lists** in both `updater.py` and `apply_patch.py`
3. **Fix `temp_run.json` race condition** — use UUID temp filenames in `app.py`
4. **Cache `load_companies()`** — TTL cache, don't hit Google Sheets on every request
5. **Test suite UI tab** — offline tests (classification, folder structure, file integrity, Excel output, updater health) + online tests (portal health, login, ModalCaptcha reachability)
6. **Session keepalive** — portal sessions expire mid-run on large companies (especially emitidas). Keepalive every 15 notes.
7. **Fix `generate_fiscal_all()` path** — verify it finds company dirs correctly
8. **`apply_patch.py` MD5 check** — currently re-downloads all files unconditionally, should check before overwriting
9. **Flask basic auth** — even a simple hardcoded password prevents unauthorized access on office network
10. **`worker_certificado.py` emitidas mode** — currently only handles recebidas

---

## Key Technical Facts for AI Assistants

- **Portal selectors:** `.paginacao .descricao` (total count), `tr[data-chave]` (note rows), `#datainicio` / `#datafim` (filter inputs), `button[type='submit']` (filter button)
- **Pagination URL:** `?pg=N` query param on current URL
- **JWT location:** `window.sessionStorage.getItem('accessToken')` — contains `inscricao` (CNPJ) and `nome`
- **BOM issue:** Portal login responses sometimes prepend UTF-8 BOM (`\xef\xbb\xbf`) — always strip before HTML content checks
- **Playwright version constraint:** Use `click(click_count=3)` not `triple_click()`
- **Encoding:** All files must be UTF-8 no-BOM. Windows Git adds BOM on CRLF conversion — `open(path, 'rb').read().lstrip(b'\xef\xbb\xbf').decode('utf-8')` pattern used throughout
- **Worker count:** `main.py` uses `max_workers=3` (conservative for portal stability during business hours). Overnight runs more reliable.
- **Company credentials:** CNPJ = username field `#Inscricao`, password field `#Senha`
- **Login success detection:** `page.wait_for_url(lambda url: "Login" not in url)`
- **Portal error detection:** Check for "The service is unavailable", "502", "Server Error" in page content

---

## Raw GitHub URLs (for fetching latest files)

```
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/app.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/worker.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/worker_certificado.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/main.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/updater.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/apply_patch.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/generate_fiscal.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/generate_summary.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/setup_config.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/src/auth.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/src/navigation.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/src/downloader.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/src/parser.py
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/templates/index.html
https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/nfse-extension-blueprint.md
```
