# NFS-e Automation

Internal automation tool built for **ORPROCON** (Tubarão, SC, Brazil) to automate monthly retrieval, classification, and reporting of NFS-e (Notas Fiscais de Serviço Eletrônico) from the federal portal for approximately 624 client companies.

---

## Overview

Each month, the tool logs into [nfse.gov.br/EmissorNacional](https://www.nfse.gov.br/EmissorNacional) for each client company, generates a spreadsheet of received invoices via the NFS-e Download Helper Chrome extension, identifies notes with tax withholding, downloads their XMLs and PDFs, classifies them as **federal** or **municipal** retention, organizes them into a structured folder hierarchy, and produces a summary Excel workbook. Accountants receive a ZIP package ready for import into the Batista/SCI fiscal system.

---

## Tech Stack

| Component | Detail |
|---|---|
| Backend | Python 3.11–3.13, Flask (port 5000) |
| Browser automation | Playwright (sync API), Chromium |
| NFS-e extension | Chrome extension v2.0.5, ID `ajkbjdkeaacaaaagmpnocomjeoeidagp` |
| Excel output | openpyxl |
| Config | JSON (`config/settings.json`) |
| Company list | Google Sheet ID `1MI4xI6rSWfYVYTtPfXOzNPon-AGq0KXh` (CSV export) |
| SCI import format | Layout 62 / SefinNacional v1.01 |

---

## File Structure

```
nfse-automation/
├── app.py                    # Flask server — all API routes, orchestration
├── main.py                   # CLI entry point, ThreadPoolExecutor (3 workers)
├── worker.py                 # Per-company Playwright subprocess
├── generate_fiscal.py        # XML parsing, fiscal XLSX + Batista TXT generation
├── generate_summary.py       # Builds resumo_nfse.xlsx across all companies
├── activate_license.py       # Activates/checks NFS-e extension license
├── setup_config.py           # Patches settings.json + launch.vbs at install time
├── setup_shortcut.py         # Creates desktop shortcut
├── scheduler.py              # Runs automation on day 1 of month at 06:00
├── fix_encoding.py           # One-shot UTF-8 patcher (run if charmap errors appear)
├── write_index.py            # Rewrites templates/index.html from Python
├── launch.vbs                # Silent Flask start, health poll, opens browser
├── install.bat               # Installer entry point
├── install_part1.bat         # Python check/install
├── install_part2.bat         # pip + playwright + chromium + setup
├── restart.bat               # Kills python.exe, relaunches
├── start.bat                 # Direct Flask start (debug)
├── requirements.txt
│
├── config/
│   ├── settings.json         # All paths (auto-patched at install)
│   ├── companies.json        # Fallback company list
│   ├── groups.json           # Accountant-defined company groups (by CNPJ)
│   └── cidades_lookup.json   # IBGE city codes (generated per machine, gitignored)
│
├── src/
│   ├── auth.py               # Browser context creation, login
│   ├── navigation.py         # Navigate to Recebidas, apply date filter
│   ├── downloader.py         # Excel generation, URL scraping, XML/PDF download, classification
│   └── parser.py             # Parse extension Excel to find retention CNPJs
│
└── templates/
    └── index.html            # Single-page UI (vanilla JS, no framework)
```

---

## Output Structure

```
Desktop\NFESAUTOMATION\
└── Empresas\
    ├── resumo_nfse.xlsx
    └── {Company Name}\
        └── {MM-YYYY}\
            ├── federal\
            │   ├── xmls\
            │   └── pdfs\
            └── municipal\
                ├── xmls\
                └── pdfs\
```

---

## Run Modes

| Mode | Trigger | Description |
|---|---|---|
| `reinf` | Default | Downloads only notes with federal or municipal retention |
| `all` | "Extração Geral" tab | Downloads all received notes, no retention filter |

---

## Classification Rules

**Federal retention** (`is_federal = True`) when any of the following > 0:
- `vRetIRRF`, `vRetCSLL`, `vRetINSS`, `vRetCP`
- `vPis` or `vCofins` when `tpRetPisCofins == "1"`

**Municipal retention** (`is_municipal = True`) when:
- `tpRetISSQN == "1"`

**Cancelled notes:** `cStat != "100"` (catches 101, 107, 108, 109, etc.)

> ⚠️ CBS (`vCBSTot`/`vCBS`) and IBS (`vIBSTot`) are reforma tributária fields — **not** federal retention. Do not classify them as federal.

---

## Installation (New Machine)

1. Extract `nfse-automation-deployV5.zip` to `Downloads\`
2. Run `install.bat` (not as Administrator)
3. If Python installer opens: check **"Add Python to PATH"** before installing
4. Wait for Part 2 — Chromium download can take 5+ minutes
5. App opens automatically at `http://localhost:5000`
6. If you see charmap/encoding errors: run `python fix_encoding.py`

### What the installer does

```
install.bat
  └── install_part1.bat       ← checks .installed sentinel; installs Python if missing
        └── install_part2.bat ← pip install, playwright install chromium,
                                 setup_config.py, setup_shortcut.py,
                                 activate_license.py, creates .installed, launches app
```

---

## Configuration (`config/settings.json`)

```json
{
  "extension_path": "...\\extension\\2.0.5_0",
  "profile_path":   "...\\chrome-profile",
  "python_exe":     "...\\python.exe",
  "downloads_path": "...\\Desktop\\NFESAUTOMATION"
}
```

All paths are auto-patched by `setup_config.py` at install time. Never hardcode paths.

---

## API Routes (Flask)

| Method | Route | Description |
|---|---|---|
| GET | `/` | Serves `index.html` |
| GET | `/health` | Health check (`ok`) |
| GET | `/api/companies` | Returns company list + groups |
| POST | `/api/run/stream` | Runs automation, streams logs via SSE |
| POST | `/api/run/zip` | Runs automation, returns ZIP download |
| POST/PUT/DELETE | `/api/groups/*` | Group CRUD |

---

## generate_fiscal.py — Batista TXT Format

Produces one line per note with 242 comma-separated fields for Batista/SCI system import. Key field positions:

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

## Known Issues & Fixes

### charmap encoding errors
**Run:** `python fix_encoding.py` — patches `main.py`, `worker.py`, `app.py`, `src/auth.py`, `setup_config.py` with UTF-8 reconfigure.

### Multiple Flask instances (port 5000 conflict)
Run `restart.bat` or kill all `python.exe` in Task Manager.

### Extension inactive / login fails
Check `settings.json` → `extension_path` must point to `extension\2.0.5_0`, not `extension\`.

### `glob.glob()` fails on paths with `[ ]`
Use `glob.escape()` — brackets in company names break glob silently.

### BOM on HTML responses
Strip `\xef\xbb\xbf` before checking response content type.

### Playwright `fill()` doesn't fire `keyup` for MD5 password hashing
Use `page.evaluate()` to set the hidden field directly.

---

## Git / Deployment Notes

- **Always push to both branches:** `git push origin master:main --force`
- `updater.py` FILES list and `apply_patch.py` pull list must stay in sync when new files are added
- Gitignored: `config/settings.json`, `config/companies_cache.json`, `config/cidades_lookup.json`, `output/`, `__pycache__/`, `chrome-profile/`, `downloads/`, `*.log`
- On fresh machines, seed `settings.json` from `setup_config.py` — do not commit it

---

## Deployed Machines

| Machine | Status |
|---|---|
| Bryan's laptop (`C:\nfse-automation`) | Production |
| Accounting machine 1 | V5 deployed May 2026 |
| Mario's machine | Pending |

---

## Related Projects

- **Prefeitura Moderna App** — `github.com/Bsgoncalves822/prefeitura_moderna_app` (port 5001) — ISS Substituto, NFS-e PM, and Guias/Boletos scraper for `tubarao-sc.prefeituramoderna.com.br`
- **nfse_retencao.py** — standalone tool for parsing local XML/PDF dumps into retention reports
- **Chrome extension (Manifest V3)** — browser-side pipeline for certificado companies (no license required)
- **ADN API pipeline** — `MAIN.py` + `pynfse_nacional`, mTLS with `.pfx` against `adn.nfse.gov.br`
