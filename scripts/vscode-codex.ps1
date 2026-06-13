param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $CodexArgs
)

$ErrorActionPreference = "Stop"

$command = Get-Command codex.exe -ErrorAction SilentlyContinue
if ($command) {
  $codex = $command.Source
} else {
  $extensionRoot = Join-Path $env:USERPROFILE ".vscode\extensions"
  $codex = Get-ChildItem -Path $extensionRoot -Recurse -Filter codex.exe -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -like "*\openai.chatgpt-*\bin\windows-x86_64\codex.exe" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
}

if (-not $codex) {
  Write-Error "Could not find codex.exe. Please check that the VSCode OpenAI/Codex extension is installed."
  exit 1
}

& $codex @CodexArgs
exit $LASTEXITCODE
