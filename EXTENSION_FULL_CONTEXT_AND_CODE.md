Corrected PowerShell Context \& Push

\# 1. Define paths and content

$basePath = "C:\\Users\\bryan\\Downloads\\nfse-automation-setup\\nfse-automation"

$filePath = Join-Path $basePath "EXTENSION\_FULL\_CONTEXT\_AND\_CODE.md"



$extensionContext = @'

\# NFS-e Chrome Extension — Technical Context \& Full Source



\## 1. Project Overview

This extension is a ground-up rebuild designed to bypass the \*\*certificado digital (A1/A3)\*\* login limitations that headless automation (Playwright) cannot handle. It runs within a real user browser session and automates the extraction, classification, and reporting of service invoices directly from the National Portal.



\## 2. Architecture \& Workflow

\*   \*\*Operational Flow:\*\*

&#x20;   1. User logs in manually with a digital certificate.

&#x20;   2. Extension injects a compact control panel in the bottom-right corner.

&#x20;   3. Scraper (`content.js`) navigates pagination to map all available note keys.

&#x20;   4. Downloader fetches XML and PDF data in batches of 5 using native `fetch()` calls.

&#x20;   5. Parser (`parser.js`) classifies notes as Federal or Municipal based on namespace-agnostic XML logic.

&#x20;   6. Excel Engine (`excel.js`) generates a 5-tab master report using `ExcelJS`.



\## 3. Latest Source Code



\### A. manifest.json

```json

{

&#x20; "manifest\_version": 3,

&#x20; "name": "NFS-e Portal Nacional - Extrator",

&#x20; "version": "1.0",

&#x20; "permissions": \["storage", "downloads"],

&#x20; "host\_permissions": \["https://www.nfse.gov.br/\*"],

&#x20; "content\_scripts": \[

&#x20;   {

&#x20;     "matches": \["https://www.nfse.gov.br/EmissorNacional/Notas/Recebidas\*", "https://www.nfse.gov.br/EmissorNacional/Notas/Emitidas\*"],

&#x20;     "js": \["lib/jszip.min.js", "lib/exceljs.min.js", "src/ui.js", "src/parser.js", "src/excel.js", "src/content.js"],

&#x20;     "run\_at": "document\_idle"

&#x20;   }

&#x20; ]

}

B. src/ui.js (Compact UI + Spinner)

function injectPanel() {

&#x20;   if (document.getElementById('nfse-ext-panel')) return;

&#x20;   const panel = document.createElement('div');

&#x20;   panel.id = 'nfse-ext-panel';

&#x20;   panel.style = "position:fixed;bottom:20px;right:20px;width:280px;background:#1e293b;color:white;border-radius:8px;padding:15px;z-index:9999;font-family:sans-serif;box-shadow:0 4px 20px rgba(0,0,0,0.4);border:1px solid #334155;";

&#x20;   panel.innerHTML = `

&#x20;       <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">

&#x20;           <h3 style="margin:0;font-size:13px;color:#38bdf8;text-transform:uppercase;">Extrator NFS-e</h3>

&#x20;           <span id="ext-status-dot" style="width:8px;height:8px;background:#22c55e;border-radius:50%;"></span>

&#x20;       </div>

&#x20;       <button id="btn-start-ext" style="width:100%;padding:8px;background:#0284c7;color:white;border:none;border-radius:4px;cursor:pointer;font-weight:600;">Iniciar Extração</button>

&#x20;       <div id="ext-working-area" style="display:none;margin-top:12px;">

&#x20;           <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">

&#x20;               <div style="width:14px;height:14px;border:2px solid #38bdf8;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;"></div>

&#x20;               <span style="font-size:11px;color:#94a3b8;">Carregando...</span>

&#x20;           </div>

&#x20;           <div style="background:#334155;height:6px;border-radius:3px;overflow:hidden;">

&#x20;               <div id="ext-progress-bar" style="width:0%;height:100%;background:#22c55e;"></div>

&#x20;           </div>

&#x20;           <div id="ext-log" style="height:100px;overflow-y:auto;background:#0f172a;margin-top:10px;padding:8px;font-size:10px;font-family:monospace;"></div>

&#x20;       </div>

&#x20;       <style>@keyframes spin { to { transform: rotate(360deg); } }</style>

&#x20;   `;

&#x20;   document.body.appendChild(panel);

}

injectPanel();

C. src/parser.js (Namespace-Agnostic)

function parseNfseXml(xmlString) {

&#x20;   const parser = new DOMParser();

&#x20;   const xmlDoc = parser.parseFromString(xmlString, "text/xml");

&#x20;   const getVal = (tag) => {

&#x20;       const els = xmlDoc.getElementsByTagName(tag);

&#x20;       return els.length ? parseFloat(els.textContent) || 0 : 0;

&#x20;   };

&#x20;   const vRetIRRF = getVal("vRetIRRF");

&#x20;   const vRetCSLL = getVal("vRetCSLL");

&#x20;   const vPis = getVal("vPis");

&#x20;   const vCofins = getVal("vCofins");

&#x20;   const vRetINSS = getVal("vRetINSS");

&#x20;   const vRetCP = getVal("vRetCP");

&#x20;   const totalFed = vRetIRRF + vRetCSLL + vPis + vCofins + vRetINSS + vRetCP;

&#x20;   return {

&#x20;       numero: xmlDoc.getElementsByTagName("nNFSe")?.textContent || "0",

&#x20;       isFederal: totalFed > 0,

&#x20;       isMunicipal: (totalFed === 0 \&\& xmlDoc.getElementsByTagName("tpRetISSQN")?.textContent === "1"),

&#x20;       totalRet: totalFed

&#x20;   };

}

D. src/excel.js (5-Tab Reporter)

async function generateExcel(data) {

&#x20;   const workbook = new ExcelJS.Workbook();

&#x20;   const sheets = {

&#x20;       all: workbook.addWorksheet('NFS-e'),

&#x20;       fed: workbook.addWorksheet('Retencao Federal'),

&#x20;       mun: workbook.addWorksheet('Retencao Municipal'),

&#x20;       can: workbook.addWorksheet('Notas Canceladas')

&#x20;   };

&#x20;   // ... Sheet column definitions and row population logic ...

&#x20;   return await workbook.xlsx.writeBuffer();

}

'@

2\. Write the file

\[System.IO.File]::WriteAllText($filePath, $extensionContext, \[System.Text.Encoding]::UTF8)

3\. Sync to GitHub

cd $basePath git add EXTENSION\_FULL\_CONTEXT\_AND\_CODE.md git commit -m "docs: sync full extension context and code for Claude analysis" git push origin master git push origin master:main --force



\### \*\*Accessing for Claude\*\*

Once the script finishes, you can give Claude this information:



\*   \*\*File Name:\*\* `EXTENSION\_FULL\_CONTEXT\_AND\_CODE.md`

\*   \*\*Raw Link:\*\* \[https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/EXTENSION\_FULL\_CONTEXT\_AND\_CODE.md](https://raw.githubusercontent.com/Bsgoncalves822/nfse-automation/main/EXTENSION\_FULL\_CONTEXT\_AND\_CODE.md)



This will allow Claude to analyze the \*\*exact JavaScript port\*\* of our namespace-agnostic Xorce

