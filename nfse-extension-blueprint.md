# NFS-e Chrome Extension — Full Technical Blueprint
*Authored by Bryan Gonçalves / ORPROCON — June 2026*

---

## 1. Purpose & Context

The existing Python/Playwright automation at `C:\nfse-automation` cannot handle companies that log in via **certificado digital** (A1/A3 certificate) because Playwright cannot drive the OS-level certificate picker. This extension solves that by running the entire pipeline **inside the user's real Chrome session** — the user logs in manually, the extension takes over from there.

This extension is a **ground-up rebuild**, not a patch of the old NFS-e Download Helper. The old extension is dead (license server offline). This one has no license system.

---

## 2. Scope

| Feature | Recebidas | Emitidas |
|---|---|---|
| Inject download button | ✅ | ✅ |
| Scrape all pages | ✅ | ✅ |
| Download XMLs + PDFs | ✅ | ✅ |
| Classify federal/municipal | ✅ | N/A |
| Generate Excel summary | ✅ | ✅ |
| Output ZIP | ✅ | ✅ |
| Progress UI panel | ✅ | ✅ |

---

## 3. File Structure

```
nfse-ext/
├── manifest.json
├── content.js          ← injected into portal pages (main logic)
├── parser.js           ← XML parsing + classification (ported from Python)
├── excel.js            ← Excel generation using ExcelJS
├── ui.js               ← injected progress panel + buttons
├── lib/
│   ├── exceljs.min.js  ← copy from old extension
│   └── jszip.min.js    ← copy from old extension
└── icons/
    ├── 16.png
    ├── 48.png
    └── 128.png
```

No background service worker needed. No popup. Pure content script.

---

## 4. manifest.json

```json
{
  "manifest_version": 3,
  "name": "NFS-e ORPROCON",
  "version": "1.0.0",
  "description": "Download e classificacao automatica de NFS-e",
  "content_scripts": [
    {
      "matches": [
        "https://www.nfse.gov.br/EmissorNacional/Notas/Recebidas*",
        "https://www.nfse.gov.br/EmissorNacional/Notas/Emitidas*"
      ],
      "js": [
        "lib/jszip.min.js",
        "lib/exceljs.min.js",
        "parser.js",
        "excel.js",
        "ui.js",
        "content.js"
      ],
      "run_at": "document_idle"
    }
  ],
  "web_accessible_resources": [
    {
      "resources": ["lib/*"],
      "matches": ["https://www.nfse.gov.br/*"]
    }
  ]
}
```

---

## 5. Module Specs

### 5.1 `ui.js` — Injected UI

**Responsibilities:**
- Inject a floating panel into the page (fixed position, top-right)
- Render buttons: "Baixar Recebidas" / "Baixar Emitidas" depending on current page
- Show progress bar + live log lines during run
- Show final summary (X federal, Y municipal, Z sem retencao)
- Download trigger (creates blob URL, clicks anchor)

**Panel HTML structure:**
```
┌─────────────────────────────┐
│ NFS-e ORPROCON          [X] │
│ ─────────────────────────── │
│ Período: [de] até [até]     │  ← date inputs, pre-filled from page
│ [Baixar Recebidas]          │
│ ─────────────────────────── │
│ ▓▓▓▓▓▓░░░░ 45/120 notas    │  ← progress bar
│ [OK] FEDERAL | Nota 1234   │  ← scrollable log
│ [OK] MUNICIPAL | Nota 1235 │
└─────────────────────────────┘
```

**Key functions:**
- `injectPanel()` — creates and appends panel to `document.body`
- `updateProgress(current, total, msg)` — updates bar + log
- `showSummary(stats)` — final counts
- `triggerDownload(blob, filename)` — creates object URL, clicks

**Date pre-fill:** Read `datainicio`/`datafim` values from the page's existing filter form inputs and pre-populate the panel inputs. User can override before clicking.

---

### 5.2 `parser.js` — XML Classification

**Direct port of Python `downloader.py` classification logic.**

```javascript
function parseXml(xmlText) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlText, 'application/xml');
    
    // helpers
    function getText(tag) { ... }
    function getFloat(tag) { ... }
    
    const nNFSe      = getText('nNFSe');
    const dhEmi      = getText('dhEmi');
    const cStat      = getText('cStat');
    const cnpjEmit   = getText('CNPJ');       // first CNPJ = emitente
    const nomeEmit   = getText('xNome');
    const xLocEmi    = getText('xLocEmi');
    const xTribNac   = getText('xTribNac');
    
    const vRetIRRF   = getFloat('vRetIRRF');
    const vRetCSLL   = getFloat('vRetCSLL');
    const vRetINSS   = getFloat('vRetINSS');
    const vRetCP     = getFloat('vRetCP');
    const vPis       = getFloat('vPis');
    const vCofins    = getFloat('vCofins');
    const tpRetPis   = getText('tpRetPisCofins');
    const vISSQN     = getFloat('vISSQN');
    const tpRetISS   = getText('tpRetISSQN');
    // CBS/IBS: present in data but NOT federal retention
    const vCBS       = getFloat('vCBSTot') || getFloat('vCBS');
    const vIBS       = getFloat('vIBSTot');
    
    // Classification (CRITICAL RULES — do not change without full audit)
    const pisCofinsRetidos = tpRetPis === '1' 
        ? (vPis + vCofins) 
        : 0;
    const inssVal    = vRetCP > 0 ? vRetCP : vRetINSS;
    const totalRet   = vRetIRRF + vRetCSLL + pisCofinsRetidos + inssVal;
    const issRet     = tpRetISS === '1' ? vISSQN : 0;
    const cancelada  = cStat !== '100' && cStat !== '';
    
    const isFederal   = totalRet > 0;
    const isMunicipal = !isFederal && tpRetISS === '1';
    
    return {
        numero: nNFSe, emissao: dhEmi, cnpjEmit, nomeEmit,
        xLocEmi, xTribNac, cStat, cancelada,
        vServ: getFloat('vServ') || getFloat('vLiq'),
        vISSQN, issRet, pisCofinsRetidos,
        vPis, vCofins, tpRetPis,
        vRetIRRF, vRetCSLL, inssVal,
        vCBS, vIBS,     // kept for reporting, not for classification
        totalRet, issRet,
        isFederal, isMunicipal,
    };
}
```

**Also needed for Emitidas:**
```javascript
function parseXmlEmitidas(xmlText) {
    // Same as above but extracts tomador (toma element) instead of emitente
    // Returns: numero, emissao, cnpjToma, nomeToma, vServ, vISSQN, etc.
}
```

---

### 5.3 `excel.js` — Excel Generation

**Uses ExcelJS (already available as `lib/exceljs.min.js`).**

#### For Recebidas:

`generateRecebidas(rows, companyName, month)` → returns `ArrayBuffer`

Sheets:
1. **NFS-e** — all notes, all fields
2. **Retencao Federal** — only `isFederal == true` notes
3. **Retencao Municipal** — only `isMunicipal == true` notes  
4. **Notas Canceladas** — only `cancelada == true` notes
5. **Resumo por Servico** — grouped by `xTribNac`

Column spec (matches Python `generate_recebidas_excel`):
```
Nr NFSe | Local Prest | Emissao | CNPJ Emit | Razao Emit |
CNPJ Toma | Razao Toma | Cod Trib | Desc Trib |
Vl Servico | ISS | ISS Ret | Pis Ret | Cofins Ret |
IR Ret | CSLL Ret | INSS Ret | CBS | IBS | Total Ret | Vl Liq | Obs
```

Styling: match Python output exactly (blue headers `#1A56A0`, alternating row fills, money format `#,##0.00`, freeze panes).

#### For Emitidas:

`generateEmitidas(rows, companyName, month)` → returns `ArrayBuffer`

Columns: `Nr NFSe | Emissao | CNPJ Tomador | Razao Tomador | Vl Servico | ISS | Obs`

---

### 5.4 `content.js` — Orchestration

This is the main entry point. Runs after `document_idle`.

#### Initialization:
```javascript
const isRecebidas = window.location.href.includes('/Notas/Recebidas');
const isEmitidas  = window.location.href.includes('/Notas/Emitidas');
if (!isRecebidas && !isEmitidas) return;

injectPanel();  // from ui.js
```

#### Core flow when button clicked:

```
1. getTotalPages()
   └── read '.paginacao .descricao' → "X de Y registros"
   └── rowsOnPage = document.querySelectorAll('tbody tr[data-chave]').length
   └── totalPages = Math.ceil(Y / rowsOnPage)

2. collectAllChaves(totalPages)
   └── for page 1..N:
       └── html = await fetchPage(page)   ← fetch(currentUrl + pg=N)
       └── chaves = parseChavesFromHtml(html)
       └── allChaves.push(...chaves)

3. downloadAll(allChaves)
   └── for each chave:
       └── xmlText = await fetchXml(chave)
           URL: https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/NFSe/{chave}
       └── pdfBlob = await fetchPdf(chave)
           URL: https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/DANFSe/{chave}
       └── parsed = parseXml(xmlText)
       └── classify → add to federal/municipal/sem_retencao/canceladas bucket
       └── add XML + PDF to JSZip under correct folder
       └── updateProgress(i, total, ...)

4. generateExcel(allParsed)
   └── workbook = generateRecebidas(allParsed, name, month)
   └── add to ZIP as 'Recebidas_NFS-e_{name}_{month}.xlsx'

5. zip.generateAsync({type:'blob'})
   └── triggerDownload(blob, 'reinf_{month}.zip')
```

#### ZIP folder structure (mirrors Python output):
```
reinf_MM-YYYY.zip
├── all/
│   ├── xmls/  ← every XML
│   └── pdfs/  ← every PDF
├── federal/
│   ├── xmls/
│   └── pdfs/
├── municipal/
│   ├── xmls/
│   └── pdfs/
├── canceladas/
│   └── xmls/
└── Recebidas_NFS-e_{company}_{month}.xlsx
```

#### Key helper functions:

```javascript
async function fetchPage(pageNum) {
    const url = new URL(window.location.href);
    url.searchParams.set('pg', pageNum);
    const res = await fetch(url.toString());
    return res.text();
}

function parseChavesFromHtml(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return [...doc.querySelectorAll('tr[data-chave]')]
        .map(tr => tr.getAttribute('data-chave'))
        .filter(Boolean);
}

async function fetchXml(chave) {
    const url = `https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/NFSe/${chave}`;
    const res = await fetch(url);  // session cookies automatic
    if (!res.ok) throw new Error(`XML fetch failed: ${res.status}`);
    return res.text();
}

async function fetchPdf(chave) {
    const url = `https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/DANFSe/${chave}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`PDF fetch failed: ${res.status}`);
    return res.blob();
}
```

#### Concurrency:
Process notes in **batches of 5** (matches old extension). Do NOT go higher — portal rate-limits aggressively.

```javascript
const BATCH_SIZE = 5;
for (let i = 0; i < allChaves.length; i += BATCH_SIZE) {
    const batch = allChaves.slice(i, i + BATCH_SIZE);
    await Promise.all(batch.map(chave => processNote(chave)));
    updateProgress(Math.min(i + BATCH_SIZE, allChaves.length), allChaves.length);
}
```

#### Error handling per note:
- Retry XML fetch up to 3 times with 2s delay
- If XML fails after retries: log error, skip note, continue
- If PDF fails: log warning, add XML only to ZIP, continue
- Never let a single note failure abort the whole run

---

## 6. Portal-Specific Knowledge

| Thing | Detail |
|---|---|
| Pagination element | `.paginacao .descricao` → text "X de Y registros" |
| Note rows selector | `tbody tr[data-chave]` |
| Chave attribute | `tr[data-chave="..."]` — base64-encoded key |
| XML endpoint | `GET /emissornacional/DPS/ModalCaptcha/NFSe/{chave}` |
| PDF endpoint | `GET /emissornacional/DPS/ModalCaptcha/DANFSe/{chave}` |
| Auth | Session cookies automatic — no extra headers needed in extension context (unlike Playwright which needed Referer) |
| Page URL params | `datainicio`, `datafim`, `executar=1`, `busca`, `pg` |
| Page size | Fixed at ~15 rows server-side, cannot override |
| JWT token | `window.sessionStorage.getItem('accessToken')` — available but not needed for ModalCaptcha downloads |
| REST API | `window.UrlRest` points to internal SERPRO network — NOT publicly reachable, ignore |

---

## 7. Classification Rules (DO NOT CHANGE WITHOUT AUDIT)

```
is_federal = (vRetIRRF > 0)
          OR (vRetCSLL > 0)
          OR (vRetINSS > 0)
          OR (vRetCP > 0)
          OR (tpRetPisCofins === '1' AND (vPis > 0 OR vCofins > 0))

is_municipal = !is_federal AND tpRetISSQN === '1'

is_cancelada = cStat !== '100' AND cStat !== ''

CBS (vCBSTot, vCBS) and IBS (vIBSTot) = reforma tributaria, ISS replacement
→ appear in data/reporting but DO NOT count toward is_federal
```

---

## 8. Build Order

Build and test each module in isolation before integrating:

1. **`parser.js`** — test against known XMLs from `C:\Users\bryan\OneDrive\Desktop\NFESAUTOMATION\Empresas` before anything else. Must produce identical classification to Python.

2. **`ui.js`** — inject panel, verify it renders correctly on both Recebidas and Emitidas pages without breaking portal UI.

3. **`content.js` scraper only** — `collectAllChaves()` first, log chave count to console, verify it matches portal's "Y registros" total.

4. **`content.js` downloader** — add XML+PDF fetching, verify files are valid (XML parses, PDF is binary).

5. **`excel.js`** — generate Excel from sample parsed data, verify sheet structure matches Python output.

6. **Full integration** — wire everything together, test ZIP output on a small company (< 20 notes) first.

7. **Emitidas** — add Emitidas flow after Recebidas is confirmed working.

---

## 9. Testing Approach

For each module, test in browser console on the live portal (logged in as a test company):

```javascript
// Test parser against a known federal note
const xml = await (await fetch('https://www.nfse.gov.br/emissornacional/DPS/ModalCaptcha/NFSe/{known_chave}')).text();
const result = parseXml(xml);
console.assert(result.isFederal === true, 'Should be federal');
console.log(result);
```

Reference classification results from Python runs at `C:\Users\bryan\OneDrive\Desktop\NFESAUTOMATION\Empresas` — the JS parser must agree with the Python parser on every note.

---

## 10. Known Gotchas

- **`.paginacao .descricao` may not exist** on page 1 if there's only 1 page — handle gracefully (totalPages = 1, rowsOnPage = actual rows).
- **`tr[data-chave]` count on page 1 may differ from other pages** — last page typically has fewer rows. Use actual row count per page, not assumed 15.
- **Canceladas rows** — in the portal these have `class="nfse-cancelada"` on the `tr`. Still download their XML (for the canceladas folder), skip their PDF.
- **ExcelJS in content script context** — ExcelJS uses `require`/module syntax internally. The minified build is self-contained but must be loaded before `excel.js`. Verify `typeof ExcelJS !== 'undefined'` before generating.
- **ZIP size** — for large companies (ECO CLINICA ~290 notes, FEMA ~105 notes) the ZIP can be 50-100MB in memory. This is fine for modern Chrome but should be noted.
- **Session expiry mid-run** — if `fetch()` starts returning HTML login page instead of XML (response is text/html, starts with `<!DOCTYPE`), the session has expired. Detect this, stop the run, alert the user to re-login and retry.
- **Rate limiting** — portal returns 429 occasionally. On 429 response, wait 30 seconds before retrying. On 403, wait 5 seconds.
