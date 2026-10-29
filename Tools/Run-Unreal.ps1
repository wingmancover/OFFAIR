param(
    [ValidateSet('Build', 'Test')]
    [string]$Mode = 'Build',
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8'
)

$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'unrealsharp.py'
$operation = if ($Mode -eq 'Build') { 'prototype-build' } else { 'test' }
# Preserve the original asset-build/test entry points with the C# SDK environment.
# Build still regenerates gameplay assets; it is not the native/C# build command.
& python $runner $operation --engine-root $EngineRoot
if ($LASTEXITCODE -ne 0) { throw "${Mode} failed with exit code $LASTEXITCODE" }
