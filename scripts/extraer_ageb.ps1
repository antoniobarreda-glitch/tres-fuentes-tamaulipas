# extraer_ageb.ps1  (v2 — el zip nacional trae un zip por estado adentro)
#
# Saca del Marco Geoestadistico nacional (3.1 GB) SOLO las capas de AGEB urbana
# y localidades de Tamaulipas (28) y Nuevo Leon (19).
# Son dos niveles: primero extrae 19_nuevoleon.zip y 28_tamaulipas.zip a una
# carpeta temporal, y de cada uno saca los shapefiles que hacen falta.
#
# COMO CORRERLO
# ------------
# 1) Abre PowerShell (tecla Windows, escribe "PowerShell", Enter). Sin permisos de admin.
# 2) cd "C:\Users\arq_b\Documents\Urbanismo\Tampico Accesibilidad\tres_fuentes_tamaulipas\scripts"
# 3) powershell -ExecutionPolicy Bypass -File .\extraer_ageb.ps1
#
# Deja los shapefiles en ...\tres_fuentes_tamaulipas\datos\mg\ y borra lo temporal.
# Tarda unos minutos: tiene que sacar dos zips de estado de varios cientos de MB.

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

$zipPath = "C:\Users\arq_b\Downloads\889463807469_s.zip"
$base    = "C:\Users\arq_b\Documents\Urbanismo\Tampico Accesibilidad\tres_fuentes_tamaulipas\datos"
$dest    = Join-Path $base "mg"
$tmp     = Join-Path $base "_tmp_estados"

if (-not (Test-Path $zipPath)) { Write-Host "No encuentro $zipPath" -ForegroundColor Red; exit 1 }
New-Item -ItemType Directory -Force -Path $dest, $tmp | Out-Null

# --- nivel 1: sacar los dos zips de estado ---
Write-Host "Abriendo el zip nacional..." -ForegroundColor Cyan
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
$estados = $zip.Entries | Where-Object { $_.Name -match '^(19_nuevoleon|28_tamaulipas)\.zip$' }
if ($estados.Count -eq 0) { Write-Host "No encontre los zips de estado." -ForegroundColor Red; $zip.Dispose(); exit 1 }

foreach ($e in $estados) {
    $out = Join-Path $tmp $e.Name
    Write-Host ("  extrayendo {0} ({1:N0} MB)..." -f $e.Name, ($e.Length/1MB)) -ForegroundColor Gray
    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e, $out, $true)
}
$zip.Dispose()

# --- nivel 2: de cada zip de estado, sacar AGEB urbana (a) y localidades (l) ---
# Puede venir otro zip anidado adentro; si pasa, el script lo detecta y avisa.
$patron = '^(28|19)(a|l)\.(shp|shx|dbf|prj|cpg)$'
$total = 0

foreach ($f in (Get-ChildItem $tmp -Filter *.zip)) {
    Write-Host "`nRevisando $($f.Name)..." -ForegroundColor Cyan
    $z2 = [System.IO.Compression.ZipFile]::OpenRead($f.FullName)
    $hits = $z2.Entries | Where-Object { $_.Name -match $patron }

    if ($hits.Count -eq 0) {
        Write-Host "  No hay match. Primeras 30 entradas de este zip:" -ForegroundColor Yellow
        $z2.Entries | Select-Object -First 30 | ForEach-Object { Write-Host "     $($_.FullName)" }
        Write-Host "  ($($z2.Entries.Count) entradas en total)" -ForegroundColor Yellow
    } else {
        foreach ($e in $hits) {
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e, (Join-Path $dest $e.Name), $true)
            "  {0,-12} {1,8:N0} KB" -f $e.Name, ($e.Length/1KB) | Write-Host
            $total++
        }
    }
    $z2.Dispose()
}

# --- limpieza ---
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue

if ($total -gt 0) {
    Write-Host "`nListo: $total archivos en $dest" -ForegroundColor Green
    Write-Host "Avisale a Claude que ya estan en datos\mg\" -ForegroundColor Green
} else {
    Write-Host "`nNo se extrajo nada. Pasale a Claude las lineas amarillas de arriba." -ForegroundColor Yellow
}
