# dump-context.ps1
# Dumps all relevant project files into a single MD for pasting into Deepseek.
# Run this before any Deepseek session to get the latest code.
# Output: C:\Users\{user}\Downloads\md-files\context_dump.md

$outDir  = Join-Path $env:USERPROFILE "Downloads\md-files"
$outFile = Join-Path $outDir "context_dump.md"

# Create output dir if it doesn't exist
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

# Files to include — add or remove as needed
$files = @(
    # Core Python
    @{ path = "C:\nfse-automation\src\downloader.py";     label = "src/downloader.py"     },
    @{ path = "C:\nfse-automation\worker.py";             label = "worker.py"             },
    @{ path = "C:\nfse-automation\main.py";               label = "main.py"               },
    @{ path = "C:\nfse-automation\generate_fiscal.py";    label = "generate_fiscal.py"    },
    @{ path = "C:\nfse-automation\generate_summary.py";   label = "generate_summary.py"   },
    @{ path = "C:\nfse-automation\app.py";                label = "app.py"                },

    # Extension
    @{ path = "C:\nfse-automation\extension-src\manifest.json";      label = "extension-src/manifest.json"      },
    @{ path = "C:\nfse-automation\extension-src\src\parser.js";      label = "extension-src/src/parser.js"      },
    @{ path = "C:\nfse-automation\extension-src\src\content.js";     label = "extension-src/src/content.js"     },
    @{ path = "C:\nfse-automation\extension-src\src\excel.js";       label = "extension-src/src/excel.js"       },
    @{ path = "C:\nfse-automation\extension-src\src\ui.js";          label = "extension-src/src/ui.js"          }
)

$lines = @()
$lines += "# NFS-e Automation — Code Dump"
$lines += "Generated: $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
$lines += ""
$lines += "---"
$lines += ""
$lines += "## Classification Rules (CRITICAL — do not change without audit)"
$lines += ""
$lines += "- **Federal**: vRetIRRF > 0 OR vRetCSLL > 0 OR vRetINSS > 0 OR vRetCP > 0"
$lines += "  OR (tpRetPisCofins == '1' AND vPis/vCofins > 0)"
$lines += "- **Municipal**: not federal AND tpRetISSQN == '1'"
$lines += "- **CBS/IBS**: reforma tributaria — shown in Excel but NOT federal retention"
$lines += "- **Cancelada**: cStat != '100'"
$lines += ""
$lines += "---"
$lines += ""

$included = 0
$skipped  = 0

foreach ($f in $files) {
    if (Test-Path $f.path) {
        $ext = [System.IO.Path]::GetExtension($f.path).TrimStart('.')
        $content = [System.IO.File]::ReadAllText($f.path, [System.Text.Encoding]::UTF8)
        $lines += "## $($f.label)"
        $lines += ""
        $lines += '```' + $ext
        $lines += $content
        $lines += '```'
        $lines += ""
        $included++
    } else {
        $lines += "## $($f.label)"
        $lines += ""
        $lines += "_File not found: $($f.path)_"
        $lines += ""
        $skipped++
    }
}

[System.IO.File]::WriteAllText($outFile, ($lines -join "`n"), [System.Text.Encoding]::UTF8)

Write-Host ""
Write-Host "  Context dump complete" -ForegroundColor Green
Write-Host "  Files included : $included" -ForegroundColor Cyan
Write-Host "  Files skipped  : $skipped" -ForegroundColor $(if ($skipped -gt 0) { 'Yellow' } else { 'Cyan' })
Write-Host "  Output         : $outFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Paste into Deepseek along with nfse-extension-blueprint.md" -ForegroundColor Gray
Write-Host ""
