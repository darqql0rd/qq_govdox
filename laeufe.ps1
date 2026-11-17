# Evaluation qq_govdox: 3x Haiku (Standard-Temperatur), 1x Apertus (temperature 0), alle als Foto.
# Start im Projektordner:
#   powershell -ExecutionPolicy Bypass -File .\laeufe.ps1
# Nur Haiku:     powershell -ExecutionPolicy Bypass -File .\laeufe.ps1 -OhneApertus
# Hold-out (46-65, einmalig, Pipeline vorher nicht mehr aendern):
#                powershell -ExecutionPolicy Bypass -File .\laeufe.ps1 -Holdout
# Dauer: grob 30-40 Minuten pro Lauf. Laptop am Strom lassen, Ruhezustand aus.
# Ergebnisse: daten\laeufe\<Datum>_foto_haiku_1..3.txt und <Datum>_foto_apertus.txt (Hold-out: <Datum>_holdout_foto_...)

param([switch]$OhneApertus, [switch]$Holdout)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:KALENDER_KANAL = "ics"     # sonst landen 45 Briefe im Google Kalender

# Apertus-Key nur einmal am Anfang abfragen (wird nirgends gespeichert)
$apertusKey = $null
if (-not $OhneApertus) {
    $sicher = Read-Host "Apertus-Key (Swiss AI, sk-rc-...). Leer lassen = Apertus ueberspringen" -AsSecureString
    $apertusKey = [System.Net.NetworkCredential]::new("", $sicher).Password
    if (-not $apertusKey) { $OhneApertus = $true }
}

$tag = Get-Date -Format "yyyy-MM-dd"
$ordner = "daten\laeufe"
$datenArg = @()
if ($Holdout) { $tag = "${tag}_holdout"; $datenArg = @("--daten", "daten\holdout") }
New-Item -ItemType Directory -Force $ordner | Out-Null

foreach ($i in 1..3) {
    $datei = "$ordner\${tag}_foto_haiku_$i.txt"
    Write-Host "Haiku Lauf $i gestartet um $(Get-Date -Format HH:mm) -> $datei"
    python -u main.py _ --variante foto @datenArg | Out-File -Encoding utf8 $datei
    Write-Host "  fertig um $(Get-Date -Format HH:mm): $((Get-Content $datei -Tail 4) -join ' | ')"
}

if (-not $OhneApertus) {
    $env:LLM_BASE_URL = "https://api.swissai.svc.cscs.ch/v1"
    $env:LLM_API_KEY = $apertusKey
    $env:LLM_MODEL = "CSCS-Inference/swiss-ai/Apertus-v1.5-70B"
    $env:LLM_TEMPERATURE = "0"
    $datei = "$ordner\${tag}_foto_apertus.txt"
    Write-Host "Apertus gestartet um $(Get-Date -Format HH:mm) -> $datei"
    python -u main.py _ --variante foto @datenArg | Out-File -Encoding utf8 $datei
    Write-Host "  fertig um $(Get-Date -Format HH:mm): $((Get-Content $datei -Tail 4) -join ' | ')"
    Remove-Item Env:LLM_API_KEY
}

Write-Host "Alle Laeufe fertig um $(Get-Date -Format HH:mm). Claude Bescheid geben."
