$ErrorActionPreference = 'Stop'
$port = 8501
$url = "http://127.0.0.1:$port"
$repo = Split-Path -Parent $PSScriptRoot
$python = 'C:\Users\Robinson\AppData\Local\Programs\Python\Python314\python.exe'
$app = Join-Path $repo 'app.py'
$statePath = Join-Path $repo 'outputs\mission_control_runtime.json'

function Ensure-MissionControlDependencies {
    $missingJson = (& $python -c "import json; from runtime_dependencies import missing_dependencies; print(json.dumps(missing_dependencies()))" | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw "No fue posible comprobar las dependencias de Mission Control." }
    if ($missingJson -eq '[]') { return }
    & $python -m pip install --disable-pip-version-check -r (Join-Path $repo 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw "No fue posible instalar las dependencias requeridas: $missingJson." }
    $verifiedJson = (& $python -c "import json; from runtime_dependencies import missing_dependencies; print(json.dumps(missing_dependencies()))" | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $verifiedJson -ne '[]') {
        throw "Mission Control no puede iniciar: faltan dependencias para leer documentos, incluido PDF."
    }
}

function Test-MissionControl {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch { return $false }
}

function Get-MissionControlListener {
    return Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Get-ProcessCommandLine([int] $ProcessId) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    return $process.CommandLine
}

function Test-MissionControlProcess([int] $ProcessId) {
    $commandLine = Get-ProcessCommandLine $ProcessId
    return $null -ne $commandLine -and
        $commandLine -match 'streamlit' -and
        ($commandLine -match 'run\s+app\.py' -or
         $commandLine -match [regex]::Escape($app))
}

function Get-RuntimeIdentity {
    $identityJson = & $python -c "import json; from mission_control_runtime import runtime_identity; print(json.dumps(runtime_identity()))" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "No fue posible calcular la versión de Mission Control: $identityJson" }
    return $identityJson | ConvertFrom-Json
}

function Get-RuntimeState {
    if (-not (Test-Path -LiteralPath $statePath)) { return $null }
    try { return Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json }
    catch { return $null }
}

function Stop-ValidatedMissionControl([int] $ProcessId) {
    if (-not (Test-MissionControlProcess $ProcessId)) {
        throw "El puerto $port no pertenece a una instancia validada de Mission Control; no se detuvo ningún proceso."
    }
    Stop-Process -Id $ProcessId -ErrorAction Stop
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-MissionControlListener) -and ((Get-Date) -lt $deadline)) { Start-Sleep -Milliseconds 250 }
    if (Get-MissionControlListener) { throw 'Mission Control no se detuvo de forma controlada.' }
}

Ensure-MissionControlDependencies
$identity = Get-RuntimeIdentity
$listener = Get-MissionControlListener
$state = Get-RuntimeState
$restartRequired = $false

if ($listener) {
    if (-not (Test-MissionControlProcess $listener.OwningProcess)) {
        throw "El puerto $port está ocupado por un proceso ajeno; Mission Control no se iniciará sobre él."
    }
    if ($null -eq $state -or
        $state.fingerprint -ne $identity.fingerprint -or
        [int]$state.pid -ne [int]$listener.OwningProcess) {
        $restartRequired = $true
    }
}

if ($restartRequired) {
    Stop-ValidatedMissionControl $listener.OwningProcess
    $listener = $null
}

if (-not $listener) {
    Start-Process -FilePath $python -ArgumentList '-m', 'streamlit', 'run', $app, '--server.address', '127.0.0.1', '--server.port', $port, '--server.headless', 'true' -WorkingDirectory $repo -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Milliseconds 500
        if (Test-MissionControl) { break }
    } while ((Get-Date) -lt $deadline)
}

if (-not (Test-MissionControl)) { throw 'Mission Control no quedó disponible en 45 segundos.' }
$listener = Get-MissionControlListener
if (-not $listener -or -not (Test-MissionControlProcess $listener.OwningProcess)) {
    throw 'Mission Control respondió, pero no fue posible validar su proceso local.'
}

$runtimeState = [ordered]@{
    fingerprint = $identity.fingerprint
    files = @($identity.files)
    pid = [int]$listener.OwningProcess
    port = $port
    started_at = (Get-Date).ToUniversalTime().ToString('o')
}
New-Item -ItemType Directory -Path (Split-Path -Parent $statePath) -Force | Out-Null
$runtimeState | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
Start-Process $url
