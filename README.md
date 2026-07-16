# NFS-e Automation

Internal automation tool built for **ORPROCON** (Tubarão, SC, Brazil) to automate monthly retrieval, classification, and reporting of NFS-e (Notas Fiscais de Serviço Eletrônico) from the federal portal for approximately 624 client companies.

**Last updated:** June 2026 (V7 — self-updating)
**GitHub:** `https://github.com/Bsgoncalves822/nfse-automation` (public, `main` branch)
**Production path:** `C:\nfse-automation\` on Bryan's machine

---

## Overview

For each client company, the tool logs into [nfse.gov.br/EmissorNacional](https://www.nfse.gov.br/EmissorNacional) via Playwright, navigates to Notas Recebidas or Emitidas, scrapes all pages for chaves (50-digit note identifiers), visits each note's Visualizar page to extract data (no captcha required), reconstructs minimal valid XMLs, classifies retention as federal or municipal, generates Excel summaries, and packages results into a ZIP ready for import into the Batista/SCI fiscal system.

> ⚠️ **ModalCaptcha endpoints are dead** (hCaptcha added June 8, 2026). The current flow scrapes Visualizar pages instead of downloading XMLs/PDFs directly.

---

## Tech Stack

| Component | Detail |
|---|---|
| Backend | Python 3.11–3.13, Flask (port 5000) |
| Browser automation | Playwright (sync API), Chromium |
| Excel output | openpyxl |
| Config | JSON (`config/settings.json`) |
| Auto-update | `updater.py` + `apply_patch.py` via `launch.vbs` (V7+) |
| SCI import format | Layout 62 / SefinNacional v1.01 |

---

## File Structure

```
nfse-automation/
├── app.py                       # Flask server — all API routes, orchestration
├── main.py                      # CLI entry point, ThreadPoolExecutor (3 workers)
├── worker.py                    # Legacy per-company subprocess (ModalCaptcha flow)
├── worker_visualizar.py         # Current per-company subprocess (Visualizar scrape flow)
├── worker_certificado.py        # Headful browser worker for certificado digital companies
├── generate_fiscal.py           # XML parsing, fiscal XLSX + Batista TXT generation
├── generate_summary.py          # Builds resumo_nfse.xlsx across all companies
├── updater.py                   # Auto-updater: MD5 checks + pulls from GitHub main
├── apply_patch.py               # Secondary patcher (also pulls from GitHub main)
├── setup_config.py              # Patches settings.json + generates launch.vbs at install
├── setup_shortcut.py            # Creates desktop shortcut
├── activate_license.py          # Legacy — kept for compat (extension is dead)
├── dump-context.ps1             # Dumps all source to single MD for AI sessions
├── launch.vbs                   # Runs updater.py first, then silent Flask start
├── install.bat / install_part1.bat / install_part2.bat
├── requirements.txt             # playwright openpyxl python-dateutil schedule flask
│
├── config/
│   ├── settings.json            # All paths (auto-patched by setup_config.py, gitignored)
│   ├── companies.json           # Fallback company list (gitignored)
│   ├── groups.json              # Accountant-defined company groups by CNPJ
│   └── cidades_lookup.json      # IBGE city code lookup (generated per machine, gitignored)
│
├── src/
│   ├── auth.py                  # Browser context creation, login (10-retry loop)
│   ├── navigation.py            # navigate_to_recebidas/emitidas, apply_filter
│   ├── downloader.py            # Legacy download flow + wait_for_page_ready util
│   ├── parser.py                # Legacy — parse extension Excel for retention CNPJs
│   ├── scraper_visualizar.py    # Scrapes #nfse / #pessoas / #servicos / #tributacao panels
│   ├── reconstruct_xml.py       # Builds valid NFS-e XML from scraped Visualizar data
│   └── generate_visualizar_excel.py  # Generates 3-tab Excel from scraped nota dicts
│
├── templates/
│   └── index.html               # Single-page UI — RE-INF, Emitidas, Certificado Digital tabs
│
├── extension-src/               # Manifest V3 Chrome extension (for certificado companies)
│   ├── manifest.json
│   ├── src/content.js           # Main pipeline logic (injected into portal pages)
│   ├── src/parser.js            # XML parsing + classification (ported from Python)
│   ├── src/excel.js             # Excel generation via ExcelJS
│   ├── src/ui.js                # Injected progress panel + buttons
│   └── lib/                     # exceljs.min.js, jszip.min.js
│
└── chrome-profile/              # Persistent Chromium profile
```

---

## Download Flow (Current — June 2026)

### RE-INF / Recebidas (Visualizar flow):
```
login()
  → navigate_to_recebidas() → apply_filter(start, end)
  → scrape_all_pages()         ← collects permanent 50-digit chaves from Visualizar hrefs
  → for each chave:
      scrape_visualizar()      ← page.goto(/Notas/Visualizar/Index/{chave}), no captcha
                                  reads #nfse, #pessoas, #servicos, #tributacao panels
      reconstruct_xml()        ← builds SefinNacional v1.01 XML from scraped data
  → generate_visualizar_excel() ← 3-tab Excel (Todas, Federal, Municipal)
  → generate_fiscal.py         ← Batista TXT + fiscal XLSX from reconstructed XMLs
```

### Emitidas flow:
```
login() → navigate_to_emitidas() → apply_filter(start, end)
  → same Visualizar scrape flow as above
```

### Certificado Digital flow (manual login):
```
Open headful Chromium → user logs in with A1/A3 certificate
  → poll sessionStorage.accessToken JWT → decode to get CNPJ
  → lookup company in Google Sheet by CNPJ
  → navigate_to_recebidas() → apply_filter() → Visualizar scrape flow
```

### Chrome Extension flow (alternative for certificado):
```
User already logged into portal in real Chrome
  → extension injects buttons on Recebidas/Emitidas pages
  → scrapes .paginacao .descricao pagination, downloads XMLs+PDFs
  → classifies in JS (parser.js), generates Excel (ExcelJS) + ZIP (JSZip)
  → no Playwright, no Python, no license required
```

---

## Auto-Update Architecture (V7+)

Every launch via `launch.vbs`:
1. Runs `updater.py` **synchronously** (blocks until complete)
2. `updater.py` fetches tracked files from GitHub `main` with cache-busting (`?v={hash[:8]}`), compares MD5, overwrites if different, clears `__pycache__`
3. `updater.py` then `exec()`s `apply_patch.py` (also pulled from GitHub)
4. Flask starts, browser opens at `localhost:5000`

### Files tracked by `updater.py`:
`app.py`, `main.py`, `worker_visualizar.py`, `src/auth.py`, `src/navigation.py`, `src/downloader.py`, `src/scraper_visualizar.py`, `src/generate_visualizar_excel.py`, `templates/index.html`, `apply_patch.py`, `setup_config.py`, `setup_shortcut.py`, `nfse_icon.ico`, `nfse_icon.png`

### NOT auto-updated (add manually if changed):
`worker_certificado.py`, `generate_fiscal.py`, `generate_summary.py`, `reconstruct_xml.py`, `updater.py` itself

### Branch rules:
- Active development on `main`
- Always keep `master` in sync: `git push origin main:master --force`
- `apply_patch.py` pulls from `main` — local fixes will be overwritten if not pushed

---

## Classification Rules (CRITICAL — do not regress)

```python
# FEDERAL retention — is_federal = True when ANY of:
vRetIRRF > 0
vRetCSLL > 0
vRetINSS > 0
vRetCP   > 0
(tpRetPisCofins == '1' AND (vPis > 0 OR vCofins > 0))

# MUNICIPAL retention
tpRetISSQN == '1'  AND  NOT is_federal

# CANCELADA
cStat != '100'   # catches 101, 107, 108, 109, etc.

# CBS (vCBSTot/vCBS) and IBS (vIBSTot) = reforma tributária ISS replacements
# Present in XML — DO NOT count toward is_federal
# 765 notes were misclassified in 05-2026 due to flat FEDERAL_FIELDS check
```

---

## Output Structure

```
Desktop\NFESAUTOMATION\
└── Empresas\
    ├── resumo_nfse.xlsx
    └── {Company Name}\
        └── {MM-YYYY}\
            ├── all\
            │   ├── xmls\         ← every reconstructed XML
            │   └── pdfs\
            ├── federal\
            │   ├── xmls\
            │   └── pdfs\
            ├── municipal\
            │   ├── xmls\
            │   └── pdfs\
            ├── canceladas\
            │   └── xmls\
            └── Recebidas_NFS-e_{company}_{month}.xlsx
```

---

## UI Tabs

| Tab | Mode | Description |
|---|---|---|
| RE-INF | `reinf` | Scrapes recebidas via Visualizar, classifies federal/municipal, generates Excel |
| Emitidas | `emitidas` | Scrapes emitidas via Visualizar, generates tomador Excel |
| Certificado Digital | — | Opens headful browser for manual A1/A3 certificate login |

---

## API Routes (Flask)

| Method | Route | Description |
|---|---|---|
| GET | `/` | Serves `index.html` |
| GET | `/health` | Health check — used by `launch.vbs` poll |
| GET | `/api/companies` | Loads from Google Sheets (falls back to `companies.json`) |
| POST | `/api/run/stream` | SSE streaming run (reinf or emitidas mode) |
| POST | `/api/run/zip` | Run + returns ZIP download |
| POST | `/api/run/certificado` | Triggers headful certificado worker |
| POST/PUT/DELETE | `/api/groups/*` | Group CRUD |

---

## generate_fiscal.py — Batista TXT Format

Produces one line per note with 242 comma-separated fields for Batista/SCI import. Key field positions:

| Field | Content |
|---|---|
| 0 | Line number |
| 1 | CNPJ emitente |
| 2 | Cidade/IBGE code |
| 3 | UF |
| 4 | Data (YYYYMMDD) |
| 5–6 | Número nota |
| 7 | `NFSE` |
| 9 | Valor serviço |
| 14–16 | Base IR, alíquota (1.5), valor IR |
| 41 | INSS retido |
| 44 | Tipo `R` |
| 98 | Conta contábil (1933000 SC / 2933001 outros) |
| 99–101 | PIS, COFINS, CSLL |
| 222–225 | REINF flags |

---

## Portal Quirks & Gotchas

- **Permanent chave** = 50-digit numeric from `a[href*='/Visualizar/Index/']` — NOT the session-scoped base64 `data-chave` attribute
- **All tab panels** (`#nfse`, `#pessoas`, `#servicos`, `#tributacao`) are in DOM simultaneously — use `span.form-control-static` selectors
- **BOM on login responses** — strip `\xef\xbb\xbf` before HTML content checks
- **`fill()` doesn't fire `keyup`** for MD5 password hashing — use `page.evaluate()` to set the hidden field directly
- **`apply_filter`** uses `click(click_count=3)` not `triple_click` (not available in installed Playwright version)
- **`glob.glob()` fails silently** on paths with `[ ]` — always use `glob.escape()`
- **Portal rate-limits parallel fetching** — scrape pages sequentially
- **Portal much more stable overnight** than during business hours
- **US VPN IPs** trigger Cloudflare bans — always run from Brazilian IP
- **Session expiry mid-run** — keepalive every 15 notes recommended for large companies

---

## Known Issues & SPOFs

| Issue | Status | Fix |
|---|---|---|
| `launch.vbs` updater call is blocking — if GitHub down, Flask never starts | Open | Add `On Error Resume Next` in `setup_config.py` VBS template |
| `worker_certificado.py` not in auto-updater FILES lists | Open | Add to both `updater.py` and `apply_patch.py` |
| `generate_fiscal_all()` path iteration bug | Open | Verify directory structure match |
| `temp_run.json` race condition on concurrent UI runs | Open | Use UUID temp filenames in `app.py` |
| `brazilfiscalreport` PDF generation fails | Open | Reconstructed XMLs missing address/CNAE/IBGE — scrape from Visualizar panels and add to `reconstruct_xml.py` |
| `load_companies()` hits Google Sheets on every API call | Open | Add TTL cache |
| Windows 260-char path limit | Open | Long company names crash Excel creation — `safe_name()` truncation needed |

---

## Deployment

### New machine (V7+):
1. Extract `nfse-automation-deployV7.zip` to `Downloads\`
2. Run `install.bat` (not as Administrator)
3. If Python installer opens: check **"Add Python to PATH"**
4. Wait for Chromium install (~5 minutes)
5. App opens at `http://localhost:5000`
6. All future updates are automatic via GitHub on each restart

### Installer flow:
```
install.bat
  └── install_part1.bat    ← checks .installed sentinel; installs Python if missing
        └── install_part2.bat ← pip install, playwright install chromium,
                                 setup_config.py, setup_shortcut.py,
                                 creates .installed, launches app
```

### Push workflow:
```powershell
git add .
git commit -m "your message"
git push origin main
git push origin main:master --force   # keep master in sync for old installs
```

### Configuration (`config/settings.json`):
```json
{
  "extension_path": "...\\extension\\2.0.5_0",
  "profile_path":   "...\\chrome-profile",
  "python_exe":     "...\\python.exe",
  "downloads_path": "...\\Desktop\\NFESAUTOMATION"
}
```
Auto-patched by `setup_config.py`. Never hardcode paths. Never commit this file.

---

## Deployment History

| Version | Key change | Auto-updates? |
|---|---|---|
| V4 | First working version | ❌ |
| V5 | Encoding fixes | ❌ |
| V6 | Has `updater.py` but `launch.vbs` never calls it | ❌ |
| V7 | `launch.vbs` calls `updater.py` first — first truly self-updating version | ✅ |

---

## Related Projects

- **Prefeitura Moderna App** — `github.com/Bsgoncalves822/prefeitura_moderna_app` (port 5001) — ISS Substituto, NFS-e PM, Guias/Boletos scraper for `tubarao-sc.prefeituramoderna.com.br`
- **nfse_retencao.py** — standalone parser for local XML/PDF dumps → retention reports + XLSX
- **ADN API pipeline** — `MAIN.py` + `pynfse_nacional`, mTLS `.pfx` against `adn.nfse.gov.br` for certificado companies
