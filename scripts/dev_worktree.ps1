<#
.SYNOPSIS
  Siapkan dan jalankan Cheat Clip PRO dari worktree task, terpisah dari data produksi.

.DESCRIPTION
  Dijalankan dari dalam worktree task (bukan checkout utama):
    1. Junction node_modules dan venv ke milik checkout utama (bila belum ada).
    2. backend\.env worktree: GEMINI_API_KEY disalin dari checkout utama (nilai tidak dicetak),
       CHEAT_CLIP_EXPORTS_DIR diarahkan ke D:\CheatClip-dev (folder dibuat bila belum ada).
       .env worktree yang sudah ada tidak ditimpa kecuali dengan -Force.
    3. Port 8000 harus kosong: app produksi ditutup dulu, dev dan produksi tidak jalan bersamaan.
    4. Tanpa -Siapkan: jalankan npm run dev.

.EXAMPLE
  powershell -File scripts\dev_worktree.ps1
  powershell -File scripts\dev_worktree.ps1 -Siapkan
  powershell -File scripts\dev_worktree.ps1 -Siapkan -Force
#>
param(
    [switch]$Siapkan,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$DevExportsDir = 'D:\CheatClip-dev'
$ProdExportsDir = 'D:\CheatClip'

function Stop-Dev([string]$Pesan) {
    Write-Host "GAGAL: $Pesan" -ForegroundColor Red
    exit 1
}

function Get-NormPath([string]$P) {
    return [System.IO.Path]::GetFullPath(($P -replace '/', '\')).TrimEnd('\').ToLowerInvariant()
}

# --- Lokasi worktree dan checkout utama ---
$top = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $top) { Stop-Dev 'Bukan di dalam repo git.' }
$top = "$top".Trim()

# Baris pertama 'git worktree list' selalu checkout utama.
$mainLine = (& git worktree list --porcelain | Where-Object { $_ -like 'worktree *' } | Select-Object -First 1)
if (-not $mainLine) { Stop-Dev 'Tidak bisa membaca git worktree list.' }
$main = $mainLine.Substring(9).Trim()

if ((Get-NormPath $top) -eq (Get-NormPath $main)) {
    Stop-Dev "Skrip ini untuk worktree task, bukan checkout utama ($main). Produksi tetap dijalankan dengan npm run dev di checkout utama."
}

$wt = [System.IO.Path]::GetFullPath(($top -replace '/', '\'))
$mainWin = [System.IO.Path]::GetFullPath(($main -replace '/', '\'))
$branch = "$(& git rev-parse --abbrev-ref HEAD)".Trim()
Write-Host "Worktree : $wt"
Write-Host "Branch   : $branch"
Write-Host "Utama    : $mainWin"

# --- Junction node_modules dan venv ---
foreach ($nama in @('node_modules', 'venv')) {
    $target = Join-Path $mainWin $nama
    $link = Join-Path $wt $nama
    if (Test-Path -LiteralPath $link) {
        Write-Host "[ada]     $nama"
        continue
    }
    if (-not (Test-Path -LiteralPath $target)) {
        Stop-Dev "$target tidak ada. Pasang dulu di checkout utama (npm install / python -m venv venv)."
    }
    New-Item -ItemType Junction -Path $link -Target $target | Out-Null
    Write-Host "[dibuat]  $nama -> $target"
}

# Git melihat junction sebagai symlink, jadi pola 'venv/' dan 'node_modules/' di .gitignore
# (khusus folder) tidak berlaku. Tambah pola tanpa garis miring akhir ke info/exclude bersama
# (berlaku untuk semua worktree, tidak di-commit).
$common = "$(& git rev-parse --git-common-dir)".Trim()
if (-not [System.IO.Path]::IsPathRooted($common)) { $common = Join-Path $wt $common }
$exclude = Join-Path $common 'info\exclude'
$isiExclude = @()
if (Test-Path -LiteralPath $exclude) { $isiExclude = @(Get-Content -LiteralPath $exclude) }
foreach ($pola in @('/node_modules', '/venv')) {
    if ($isiExclude -notcontains $pola) {
        New-Item -ItemType Directory -Force -Path (Split-Path $exclude) | Out-Null
        Add-Content -LiteralPath $exclude -Value $pola -Encoding ascii
        Write-Host "[exclude] $pola"
    }
}

# --- backend\.env worktree ---
$envWt = Join-Path $wt 'backend\.env'
$envMain = Join-Path $mainWin 'backend\.env'
if ((Test-Path -LiteralPath $envWt) -and -not $Force) {
    Write-Host "[ada]     backend\.env (pakai -Force untuk menulis ulang)"
    $dirLine = Get-Content -LiteralPath $envWt | Where-Object { $_ -match '^\s*CHEAT_CLIP_EXPORTS_DIR\s*=' } | Select-Object -Last 1
    if (-not $dirLine) {
        Stop-Dev "backend\.env worktree tidak punya CHEAT_CLIP_EXPORTS_DIR, data akan masuk ke ~/CheatClip. Jalankan ulang dengan -Force."
    }
    $val = (($dirLine -split '=', 2)[1]).Trim().Trim('"').Trim("'")
    if ($val) { $DevExportsDir = $val }
}
else {
    $keyLine = $null
    if (Test-Path -LiteralPath $envMain) {
        $keyLine = Get-Content -LiteralPath $envMain | Where-Object { $_ -match '^\s*GEMINI_API_KEY\s*=' } | Select-Object -Last 1
    }
    $baris = @()
    if ($keyLine) {
        $baris += $keyLine
        Write-Host "[salin]   GEMINI_API_KEY dari checkout utama (nilai tidak dicetak)"
    }
    else {
        Write-Host "[peringatan] GEMINI_API_KEY tidak ditemukan di $envMain; isi lewat UI atau pakai 'mock'." -ForegroundColor Yellow
    }
    $baris += "CHEAT_CLIP_EXPORTS_DIR=$DevExportsDir"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($envWt, [string[]]$baris, $utf8NoBom)
    Write-Host "[ditulis] backend\.env (CHEAT_CLIP_EXPORTS_DIR=$DevExportsDir)"
}

if ((Get-NormPath $DevExportsDir) -eq (Get-NormPath $ProdExportsDir)) {
    Stop-Dev "CHEAT_CLIP_EXPORTS_DIR worktree menunjuk folder produksi $ProdExportsDir. Jalankan ulang dengan -Force."
}
if (-not (Test-Path -LiteralPath $DevExportsDir)) {
    New-Item -ItemType Directory -Path $DevExportsDir | Out-Null
    Write-Host "[dibuat]  $DevExportsDir"
}
else {
    Write-Host "[ada]     $DevExportsDir"
}

# --- Port 8000 ---
$listen = $null
try { $listen = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction Stop } catch { $listen = $null }
if ($listen) {
    Stop-Dev "Port 8000 sedang dipakai. Tutup app produksi dulu (dev dan produksi tidak dijalankan bersamaan)."
}
Write-Host "[kosong]  port 8000"

if ($Siapkan) {
    Write-Host "Siap. Jalankan tanpa -Siapkan untuk memulai npm run dev." -ForegroundColor Green
    exit 0
}

# Variabel proses tidak ditimpa load_dotenv, jadi set eksplisit agar env shell lama tidak menang.
$env:CHEAT_CLIP_EXPORTS_DIR = $DevExportsDir
Write-Host "Menjalankan npm run dev dari $wt (data: $DevExportsDir) ..." -ForegroundColor Green
Set-Location -LiteralPath $wt
& npm run dev
exit $LASTEXITCODE
