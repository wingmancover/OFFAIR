param(
    [ValidateSet('Build', 'Test')]
    [string]$Mode = 'Build',
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectFile = Join-Path $projectRoot 'OFFAIR.uproject'
$outputFolder = Join-Path $projectRoot ('Saved\' + $(if ($Mode -eq 'Build') { 'PrototypeBuild' } else { 'PrototypeTests' }))
New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
$logPath = Join-Path $outputFolder 'run.log'
$commonArguments = @(
    ('"{0}"' -f $projectFile),
    '-EnablePlugins=PythonScriptPlugin', '-unattended', '-nop4', '-nosound',
    ('-abslog="{0}"' -f $logPath)
)

if ($Mode -eq 'Build') {
    $editorPath = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
    $scriptPath = Join-Path $PSScriptRoot 'unreal\build_prototype.py'
    $arguments = $commonArguments + @('-NullRHI', '-run=pythonscript', ('-script="{0}"' -f $scriptPath))
} else {
    $editorPath = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
    $scriptPath = Join-Path $PSScriptRoot 'unreal\validate_prototype.py'
    $arguments = $commonArguments + @('-NullRHI', '-NoSplash', '-NoLiveCoding', ('-ExecutePythonScript="{0}"' -f $scriptPath))
}

if (-not (Test-Path -LiteralPath $editorPath)) { throw "Unreal Editor not found: $editorPath" }
$startedAt = [DateTime]::UtcNow
$ueProcess = Start-Process -FilePath $editorPath -ArgumentList $arguments -WindowStyle Hidden -PassThru
$ueProcess.WaitForExit()
if ($ueProcess.ExitCode -ne 0) { throw "Unreal exited with code $($ueProcess.ExitCode). See $logPath" }

if ($Mode -eq 'Build') {
    $navigationScript = Join-Path $PSScriptRoot 'unreal\finalize_navigation.py'
    $navigationLog = Join-Path $outputFolder 'navigation.log'
    $navigationArguments = @($commonArguments | Where-Object { -not $_.StartsWith('-abslog=') }) + @(
        '-NullRHI', '-NoSplash', ('-ExecutePythonScript="{0}"' -f $navigationScript), ('-abslog="{0}"' -f $navigationLog)
    )
    $navigationEditor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
    $navigationProcess = Start-Process -FilePath $navigationEditor -ArgumentList $navigationArguments -WindowStyle Hidden -PassThru
    $navigationProcess.WaitForExit()
    if ($navigationProcess.ExitCode -ne 0) { throw "Navigation build failed. See $navigationLog" }
}

$resultPath = Join-Path $outputFolder $(if ($Mode -eq 'Build') { 'build-result.json' } else { 'runtime-result.json' })
if (-not (Test-Path -LiteralPath $resultPath)) { throw "No result was produced. See $logPath" }
if ((Get-Item -LiteralPath $resultPath).LastWriteTimeUtc -lt $startedAt) { throw "Result is stale. See $logPath" }
$result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
if ($Mode -eq 'Test' -and $result.status -ne 'passed') { throw "Runtime tests failed: $($result.error)" }
if ($Mode -eq 'Build' -and (-not $result.compiled -or -not $result.navigation_ready)) { throw "Build is incomplete. See $logPath" }
Write-Output "${Mode} completed. Result: $resultPath"
