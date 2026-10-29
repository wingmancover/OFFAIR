param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Cursor','Gemini','VSCode','Generic')]
    [string]$Client
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$destinations=@{Cursor='.cursor/mcp.json';Gemini='.gemini/settings.json';VSCode='.vscode/mcp.json';Generic='.mcp.json'}
$templates=@{Cursor='Cursor.mcp.json';Gemini='Gemini.settings.json';VSCode='VSCode.mcp.json';Generic='Generic.mcp.json'}
$destination=Join-Path $projectRoot $destinations[$Client]
if(Test-Path -LiteralPath $destination){throw "Existing configuration preserved: $destination"}
$parent=Split-Path $destination -Parent
New-Item -ItemType Directory -Path $parent -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('Templates/'+$templates[$Client])) -Destination $destination
Write-Output "Restored $Client project connection: $destination"
