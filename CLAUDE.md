# CLAUDE.md - Behavioral Instructions for Claude Code
# Based on Andrej Karpathy / Forrest Chang pattern

## Project
NFS-e automation for ORPROCON accounting firm, Brazil.
Python/Flask/Playwright. Production: C:\nfse-automation

## Core Rules

NEVER make partial fixes. Always provide complete file contents.
NEVER assume a push succeeded. Always verify GitHub received the change.
NEVER use snippets or diffs. Full file replacements only.
NEVER skip BOM stripping before git commits on Windows.
NEVER use PowerShell inline -c for multi-line Python. Use here-strings (@'...'@) or script files.
NEVER assume the portal is down without checking retries. It is frequently slow.

ALWAYS verify the exact string before attempting str.replace(). Print context first.
ALWAYS check tpRetPisCofins == 1 before counting vPis/vCofins as retention.
ALWAYS check cStat != 100 for canceladas (not just 107-109).
ALWAYS include CNPJ in folder names to prevent branch mixing.
ALWAYS keep all/ folder as master copy. Never delete from all/.

## Classification Logic (CRITICAL)

Federal retention = vRetIRRF > 0 OR vRetCSLL > 0 OR vRetCP > 0 OR vRetINSS > 0
                  OR vCBS > 0 OR vIBSTot > 0
                  OR (vPis > 0 AND tpRetPisCofins == 1)
                  OR (vCofins > 0 AND tpRetPisCofins == 1)

Municipal = tpRetISSQN == 1 AND federal == 0
Cancelada = cStat != 100
sem_retencao = all retention == 0 AND not cancelled

## Folder Structure
all/ = everything (master)
federal/ = real federal retention only
municipal/ = ISS only
canceladas/ = cStat != 100
sem_retencao/ = zero retention

## Before Every Code Change
1. Read the current file content first
2. Verify the exact string you plan to replace
3. Make the change
4. Verify the change took effect
5. Push to GitHub
6. Verify GitHub received it via urllib.request

## Testing
Run these after any change to downloader.py or classification logic:
  python C:\Users\bryan\check_tpret2.py   (should show 0 wrong)
  python C:\Users\bryan\check_stats.py    (should show only cStat 100)
  python C:\Users\bryan\check_int.py      (should show 0 corrupted, 0 missing PDFs)
