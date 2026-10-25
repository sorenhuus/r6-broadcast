$ErrorActionPreference = "Stop"
Start-Transcript -Path C:\r6cast-bootstrap.log -Append

# Package manager
Set-ExecutionPolicy Bypass -Scope Process -Force
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Invoke-Expression ((New-Object Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}
$env:Path += ";C:\ProgramData\chocolatey\bin"

choco install -y --no-progress steam ubisoft-connect obs-studio python311 ffmpeg git

# r6cast + capture agent
$py = "C:\Python311\python.exe"
& $py -m pip install --upgrade pip
New-Item -ItemType Directory -Force -Path C:\r6cast | Out-Null
if (-not (Test-Path C:\r6cast\repo)) { Write-Host "Repo is private: clone it manually into C:\r6cast\repo (see README)" }
if (Test-Path C:\r6cast\repo) { & $py -m pip install -e "C:\r6cast\repo[capture]" }

# Job folders the agent watches
foreach ($d in "jobs","done","recordings") { New-Item -ItemType Directory -Force -Path "C:\r6cast\$d" | Out-Null }

# Run the agent elevated at logon, so its input reaches the game
$action  = New-ScheduledTaskAction -Execute $py -Argument "-m r6cast.agent C:\r6cast" -WorkingDirectory "C:\r6cast\repo"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\huus" -RunLevel Highest -LogonType Interactive
Register-ScheduledTask -TaskName "r6cast-agent" -Action $action -Trigger $trigger -Principal $principal -Force

Stop-Transcript
