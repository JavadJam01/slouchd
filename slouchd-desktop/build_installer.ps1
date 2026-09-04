# local build script for slouchd-desktop
# freezes app with pyinstaller and packages installer with inno setup

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   building slouchd windows installer     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. locate python in venv or path
$Python = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "[1/3] using python: $Python" -ForegroundColor Green

# 2. run pyinstaller
Write-Host "[2/3] freezing app with pyinstaller..." -ForegroundColor Green
& $Python -m PyInstaller --noconfirm --clean slouchd.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "pyinstaller build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "pyinstaller build succeeded -> dist\slouchd" -ForegroundColor Green

# 3. locate and run inno setup compiler (iscc)
Write-Host "[3/3] compiling installer with inno setup..." -ForegroundColor Green

$IsccPaths = @(
    "iscc.exe",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

$IsccCmd = $null
foreach ($path in $IsccPaths) {
    if (Get-Command $path -ErrorAction SilentlyContinue) {
        $IsccCmd = $path
        break
    }
    if (Test-Path $path) {
        $IsccCmd = $path
        break
    }
}

if ($IsccCmd) {
    Write-Host "compiling installer with: $IsccCmd" -ForegroundColor Green
    & $IsccCmd "installer\slouchd.iss"
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "success! installer created in dist\installer\" -ForegroundColor Cyan
        Get-ChildItem -Path "dist\installer\*.exe" | ForEach-Object {
            Write-Host "  -> $($_.FullName) ($([math]::Round($_.Length / 1MB, 2)) MB)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "inno setup compilation failed!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "notice: inno setup (iscc.exe) was not found." -ForegroundColor Yellow
    Write-Host "the application was frozen successfully at: dist\slouchd\slouchd.exe" -ForegroundColor White
    Write-Host "to compile the single-file setup installer locally, run:" -ForegroundColor White
    Write-Host "  winget install JRSoftware.InnoSetup" -ForegroundColor Cyan
    Write-Host "and re-run this script." -ForegroundColor White
}
