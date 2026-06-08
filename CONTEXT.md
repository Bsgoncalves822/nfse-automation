# NFS-e Automation — Project Context
*Last updated: June 2026*

---

## Current State

### Working Features

#### RE-INF Mode (`mode: reinf`)
- Logs into nfse.gov.br for each company
- Navigates to Notas Recebidas, applies date filter
- Paginates through all notes, maps download URLs
- Downloads XMLs + PDFs for every note into `all/`
- Classifies into `federal/`, `municipal/`, `canceladas/`, `sem_retencao/`
- Classification rules:
  - **Federal** = vRetIRRF > 0 OR vRetCSLL > 0 OR vRetCP > 0 OR vRetINSS > 0 OR vCBS > 0 OR vIBSTot > 0 OR (vPis > 0 AND tpRetPisCofins == 1) OR (vCofins > 0 AND tpRetPisCofins == 1)
  - **Municipal** = tpRetISSQN == 1 AND not federal
  - **Cancelada** = cStat != 100
  - **Sem retencao** = everything else
- Generates per-company Excel report (4 sheets: NFS-e, Retencao Federal, Retencao Municipal, Resumo por Servico + Notas Canceladas)
- 25 headless workers, 5 company retries, 10 nav retries
- CNPJ in folder name to prevent branch mixing

#### Extração Geral Mode (`mode: all`)
- Same as RE-INF but downloads ALL notes with no retention filter
- Output goes to `notas/` folder

#### Extração Emitidas Mode (`mode: emitidas`) ← NEW, on feature/emitidas branch
- Navigates to Notas Emitidas instead of Recebidas
- Same pagination + download flow
- Output goes to `emitidas/xmls` + `emitidas/pdfs`
- Generates Excel report with: Nr NFSe, Emissao, CNPJ/CPF Tomador, Razao Tomador, Cod. Tributacao, Descr. Tributacao, Descr. Servico, Vl. Servico, ISS, retencoes, Vl. Liquido, Situacao
- Notas Canceladas on separate sheet
- Use case: fiscal department (not accounting)

---

## Emitidas — Target Companies

These companies have been confirmed in the master spreadsheet and are being run for emitidas extraction:

### First Batch (original list)
| Company | Branches |
|---|---|
| CAMILO & GHISI LTDA. | 4 branches (0001-97, 0002-78, 0003-59, 0004-30) |
| CAMILO HOLDING LTDA | 1 |
| CENTRO MEDICO DE DIAGNOSTICO ANATOMOPATOLOGICO E CITOPATOLOGICO GONCALVES LTDA | 1 |
| CLINICA DE DIAGNOSTICOS IMBITUBA | 1 |
| CLINICA RADIOLOGICA DR ENEAS PAULO A DA ROCHA LTDA | 1 |
| CORDIS CLINICA CARDIOLOGICA LTDA | 1 |
| ECO CLINICA LTDA | 3 branches (0001-01, 0002-92, 0004-54) |
| FEMA HOTEL LTDA | 1 |
| FERNANDES ADM DE IMOVEIS LTDA | 1 |
| HOTEL SAN SILVESTRI LTDA | 1 |
| LABORATORIO BIOCLINICO SANTA CATARINA LTDA | 1 |
| LG CLINICA MEDICA LTDA | 1 |
| NARCO CLINICA MEDICA LTDA | 1 |
| OBRA DE ARTE ENGENHARIA LTDA | 1 |

### Second Batch
| Company | CNPJ |
|---|---|
| CLINICA MEDICA DELPIZZO SS | 18.330.624/0001-32 |
| CLINICA MEDICA DL SS LTDA | 08.911.743/0001-25 + 0002-06 |
| GC CASTRO ALTHOFF LTDA | 60.916.173/0001-86 |
| HERZ CLINICA CARDIOLOGICA LTDA | 34.462.153/0001-72 |
| IMOBILIARIA JEFERSON & ALBA LTDA | 18.254.319/0001-09 |
| JULIA SOARES CIRURGIA PLASTICA INTEGRADA LTDA | 15.429.165/0001-50 |
| LABORATORIO DE ANALISES CLINICAS CAPIVARI LTDA | 05.047.398/0001-35 |
| MACHADO SERVICOS MEDICOS LTDA | 53.919.501/0001-32 |
| MATER CLINICA MEDICA LTDA | 79.404.612/0001-08 |
| MFW PARTICIPACOES DE BENS LTDA | 50.164.739/0001-07 |
| OTOCLIN CLINICA DE OTORRINOLARINGOLOGIA LTDA | 29.783.512/0001-53 |
| OTOVISION CLINICA MEDICA SS | 80.489.503/0001-01 |
| PHL ADM IMOVEIS | 00.832.602/0001-05 + 0002-96 |
| TATIANA MENEGHEL & CIA LTDA | 05.571.735/0001-99 |
| THTM | 17.011.497/0001-46 |
| URO ESSENCE LTDA | 65.678.457/0001-03 |
| BRUNATO & MEDEIROS ADVOGADOS ASSOCIADOS | 20.953.541/0001-41 |

### Still Missing (need CNPJ + password from accountant)
- VITORIA CALEGARI CLINICA
- SUSTAIN
- Confirm: MEDEIROS ADV = BRUNATO & MEDEIROS?

---

## Folder Structure

```
Desktop\NFESAUTOMATION\
└── Empresas\
    ├── resumo_nfse.xlsx
    └── {Company Name} ({CNPJ_clean})\
        └── {MM-YYYY}\
            ├── all\xmls + pdfs        ← master copy, never delete
            ├── federal\xmls + pdfs    ← RE-INF federal retention
            ├── municipal\xmls + pdfs  ← ISS only
            ├── canceladas\            ← cStat != 100
            ├── sem_retencao\          ← zero retention
            ├── notas\                 ← extração geral (all mode)
            ├── emitidas\xmls + pdfs   ← extração emitidas (new)
            ├── fiscal\                ← fiscal xlsx + Batista TXT
            └── Recebidas_NFS-e_{name}_{month}.xlsx
            └── Emitidas_NFS-e_{name}_{month}.xlsx  ← new
```

---

## Known Issues

- Portal frequently slow/flaky — retries handle most cases
- Session expiry under high concurrency can cause login page to be saved as XML
  - Fix: rerun affected companies individually
- `triple_click` not available in installed Playwright version — use `click(click_count=3)` instead
- BOM issues when writing JSON from PowerShell — use `[System.IO.File]::WriteAllText()` instead of `Set-Content`

---

## Branches

| Branch | Status |
|---|---|
| `master` | Stable — RE-INF + extração geral working |
| `feature/emitidas` | In progress — emitidas mode tested and working |

---

## Next Steps

- [ ] Merge `feature/emitidas` into master after full batch run confirms clean
- [ ] Add Emitidas tab to Flask UI (index.html)
- [ ] Add VITORIA CALEGARI + SUSTAIN to master spreadsheet
- [ ] Confirm MEDEIROS ADV mapping with accountant
