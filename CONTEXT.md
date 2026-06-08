# NFS-e Automation - Project Context
Last updated: June 8, 2026

## What This Is
Internal automation for ORPROCON, Tubarao SC. Automates NFS-e downloads for ~624 clients.
Built by Bryan Goncalves. Production: C:\nfse-automation
GitHub: github.com/Bsgoncalves822/nfse-automation

## Tech Stack
- Python 3.11-3.13, Flask port 5000
- Playwright headless Chromium, 25 workers, 5 company retries, 10 nav retries
- Direct ModalCaptcha endpoint downloads (no browser extension)
- openpyxl for Excel, Google Sheets with companies.json fallback
- Auto-update via updater.py pulling from GitHub master on every launch

## Folder Structure Per Company

    COMPANY NAME (cnpj)/MM-YYYY/
      all/xmls + pdfs        <- EVERY note (master copy, never delete)
      federal/xmls + pdfs    <- Real federal retention only
      municipal/xmls + pdfs  <- ISS retention only (tpRetISSQN==1)
      canceladas/xmls + pdfs <- cStat != 100
      sem_retencao/          <- Zero retention of any kind
      Recebidas_NFS-e_...xlsx

CRITICAL: CNPJ always in folder name to prevent branch mixing.

## Classification Rules - CRITICAL (Hard Learned June 8, 2026)

Federal (any of these true):
  vRetIRRF > 0, vRetCSLL > 0, vRetCP > 0, vRetINSS > 0
  vCBS > 0, vIBSTot > 0 (new tax reform)
  vPis > 0 AND tpRetPisCofins == 1
  vCofins > 0 AND tpRetPisCofins == 1

WARNING: vPis/vCofins appear in XML even when NOT withheld.
MUST check tpRetPisCofins == 1. Bug caused ~209 misclassifications.

Municipal: tpRetISSQN == 1 AND no federal retention
Canceladas: cStat != 100 (includes 101 - not just 107-109!)
sem_retencao: all fields 0, not cancelled

## Spreadsheet (5 sheets)
1. NFS-e - all notes
2. Retencao Federal - real federal only
3. Retencao Municipal - ISS only
4. Resumo por Servico - grouped by tax code
5. Notas Canceladas

## TODO Priority Order

1. URGENT - Full parser audit
   tpRetPisCofins fix applied (commit b84da10) but need to audit ALL tpRet* flags.
   Are there tpRetIRRF, tpRetCSLL, tpRetINSS flags we are missing?
   Reparse all existing XMLs after fix.

2. URGENT - Unit test suite (ZERO TESTS EXIST)
   - Unit tests for parse_xml_full with real XML samples
   - Integration tests for folder classification logic
   - Regression tests: the 209 misclassified notes from June 8 should be test cases
   - Credential validation tests against portal
   - End-to-end smoke test: run 1 known company, assert output matches expected

3. Auto-updater hardening
   Current weaknesses: not atomic, no version pinning, no rollback, no migration
   Fix: semantic versioning + manifest file on GitHub + rollback mechanism

4. Windows 260-char path limit
   Very long company names fail to create Excel files (path too long).
   Fix: truncate folder names at ~100 chars, keep CNPJ suffix.

5. Error reporting
   Currently: console only, no persistence
   Need: error log per run, summary report, failed company list with reasons

6. Google Sheets fragility
   502s cause silent fallback to stale cache.
   ZIP builder fixed. run_stream still depends on Sheets.

## Validation Scripts (C:\Users\bryan\)
  triple_check.py      - full integrity check
  check_tpret2.py      - verify 0 wrong notes in federal
  check_stats.py       - cStat distribution
  check_int.py         - XML validity + PDF completeness
  fix_canceladas.py    - move cancelled out of federal/municipal
  fix_federal.py       - move misclassified out of federal

## Key Scripts (C:\nfse-automation\)
  run_all.py           - standalone full run bypassing Flask
  build_clean_zip.py   - CNPJ-only ZIP (excludes old folders)
  apply_patch.py       - deploy to new machine from GitHub
  validate_notas.py    - portal vs downloaded note count comparison

## Deployment

New machine:
  python apply_patch.py

Full overnight run:
  powercfg /change standby-timeout-ac 0
  python C:\nfse-automation\run_all.py --start 01/05/2026 --end 31/05/2026

After run - validate and ship:
  python C:\Users\bryan\triple_check.py
  python C:\nfse-automation\build_clean_zip.py

## GitHub State June 8 2026
Latest commits:
  b84da10 - tpRetPisCofins==1 for PIS/COFINS, cStat!=100 for canceladas
  Prior   - 25 workers, filesystem ZIP builder, CNPJ folders, pagination fix

## Accuracy Note
Per Anthropic research, providing full file context + chain-of-thought instructions
improves Claude accuracy from ~70% to 94%+ on complex tasks.
For this project:
  - Always provide full file contents not snippets
  - Request complete file replacements not diffs
  - Verify GitHub received changes before considering deployed
  - Use PowerShell here-strings for multi-line Python scripts
  - Strip BOM before git commits on Windows
