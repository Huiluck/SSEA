# Download papers from manifest using Invoke-WebRequest (works with arxiv)
$ErrorActionPreference = "Continue"

$ManifestPath = "C:\MyDocs\AGI\SSEA\docs\papers\_manifest.json"
$OutputDir = "C:\MyDocs\AGI\SSEA\docs\papers"
$LogFile = Join-Path $OutputDir "_ps_download_log.txt"

$manifest = Get-Content $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$total = $manifest.Count
Write-Output "Total papers to download: $total"

$success = 0
$failed = 0
$failedList = @()

$ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

for ($i = 0; $i -lt $total; $i++) {
    $item = $manifest[$i]
    $outFile = Join-Path $OutputDir $item.filename

    # Skip if already exists and valid
    if (Test-Path $outFile) {
        $sz = (Get-Item $outFile).Length
        if ($sz -gt 1024) {
            Write-Output "[$($i+1)/$total] SKIP (exists): $($item.filename)"
            $success++
            continue
        }
    }

    Write-Output "[$($i+1)/$total] $($item.original_url.Substring(0, [Math]::Min(70, $item.original_url.Length)))"

    $downloaded = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Invoke-WebRequest -Uri $item.pdf_url -UserAgent $ua -TimeoutSec 60 -OutFile $outFile -UseBasicParsing
            # Verify it's a PDF
            $bytes = [System.IO.File]::ReadAllBytes($outFile)
            if ($bytes.Length -gt 1024 -and $bytes[0] -eq 0x25 -and $bytes[1] -eq 0x50 -and $bytes[2] -eq 0x44 -and $bytes[3] -eq 0x46) {
                Write-Output "    -> OK ($([math]::Round($bytes.Length/1KB)) KB)"
                $success++
                $downloaded = $true
                break
            } else {
                Write-Output "    -> Not a valid PDF (size: $($bytes.Length)), removing"
                Remove-Item $outFile -Force -ErrorAction SilentlyContinue
            }
        } catch {
            $errMsg = $_.Exception.Message
            if ($errMsg -match "404|406|429") {
                Write-Output "    -> Attempt $attempt : HTTP error - $errMsg"
            } else {
                Write-Output "    -> Attempt $attempt : $errMsg"
            }
            if ($attempt -lt 3) {
                $wait = 5 * $attempt
                Write-Output "       Waiting $wait seconds..."
                Start-Sleep -Seconds $wait
            }
        }
    }

    if (-not $downloaded) {
        $failed++
        $failedList += "$($item.original_url) | $($item.pdf_url)"
        Write-Output "    -> FAILED after 3 attempts"
    }

    # Delay between downloads (longer for arxiv)
    if ($i -lt ($total - 1)) {
        if ($item.is_arxiv) {
            Start-Sleep -Milliseconds 2500
        } else {
            Start-Sleep -Milliseconds 800
        }
    }

    # Progress report every 20
    if (($i + 1) % 20 -eq 0) {
        Write-Output ""
        Write-Output "  === Progress: $($i+1)/$total | Success: $success | Failed: $failed ==="
        Write-Output ""
    }
}

Write-Output ""
Write-Output "========================================"
Write-Output "FINAL: Total=$total, Success=$success, Failed=$failed"
Write-Output "========================================"

# Count actual PDF files
$pdfCount = (Get-ChildItem $OutputDir -Filter "*.pdf").Count
Write-Output "Total PDF files in folder: $pdfCount"

# Write log
$logContent = "PowerShell Download Log - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`r`n"
$logContent += "Total: $total, Success: $success, Failed: $failed`r`n"
$logContent += "PDF files in folder: $pdfCount`r`n"
$logContent += "========================================`r`n`r`n"
$logContent += "--- FAILED --`r`n"
foreach ($f in $failedList) {
    $logContent += "$f`r`n"
}
Set-Content -Path $LogFile -Value $logContent -Encoding UTF8
Write-Output "Log written to $LogFile"
