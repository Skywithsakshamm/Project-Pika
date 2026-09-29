# Selvie Windows Setup & Auto-Start Script
param(
    [switch]$EnableAutoStart,
    [switch]$DisableAutoStart,
    [switch]$InstallDeps
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   SELVIE AI DESKTOP ASSISTANT SETUP     " -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Cyan

$CurrentDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BatPath = Join-Path $CurrentDir "run_selvie.bat"

if ($InstallDeps) {
    Write-Host "[*] Installing Python dependencies from requirements.txt..." -ForegroundColor Yellow
    python -m pip install -r (Join-Path $CurrentDir "requirements.txt")
}

if ($EnableAutoStart) {
    Write-Host "[*] Enabling Windows Startup Registry for Selvie..." -ForegroundColor Yellow
    $RegKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $Cmd = "`"$BatPath`" --headless"
    Set-ItemProperty -Path $RegKey -Name "SelvieAIAssistant" -Value $Cmd
    Write-Host "[+] Successfully enabled! Selvie will now start automatically when Windows boots." -ForegroundColor Green
}

if ($DisableAutoStart) {
    Write-Host "[*] Disabling Windows Startup Registry for Selvie..." -ForegroundColor Yellow
    $RegKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    Remove-ItemProperty -Path $RegKey -Name "SelvieAIAssistant" -ErrorAction SilentlyContinue
    Write-Host "[+] Auto-start disabled." -ForegroundColor Green
}

Write-Host "`nSetup complete! You can start Selvie anytime with run_selvie.bat or 'python run_selvie.py'." -ForegroundColor Cyan
