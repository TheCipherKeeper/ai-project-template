param(
    [string]$Root = "",
    [string]$Report = ""
)

$ErrorActionPreference = "Stop"
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path }
$PolicyRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$checks = @()

function Add-Result {
    param([string]$Id, [bool]$Passed, [string]$Message, [string]$Location)
    $state = "failed"
    if ($Passed) { $state = "passed" }
    $script:checks += [pscustomobject]@{
        id = $Id
        status = $state
        message = $Message
        location = $Location
    }
}

$configPath = Join-Path $Root ".methodology.yml"
$repositoryType = "methodology"
if (Test-Path $configPath) {
    $typeLine = Select-String -Path $configPath -Pattern "^repository_type:\s*([a-z]+)" -Encoding utf8 | Select-Object -First 1
    if ($typeLine) { $repositoryType = $typeLine.Matches[0].Groups[1].Value }
}
$requiredByType = @{
    methodology = @("AGENTS.md", "README.md", "docs/INDEX.md", "docs/refs/VERIFICATION.md", ".methodology.yml")
    hub = @("AGENTS.md", "README.md", "BACKLOG.md", "COMPOSITION.md", "CONVENTIONS.md", ".methodology.yml")
    service = @("AGENTS.md", "README.md", "docs/ARCHITECTURE.md", "Dockerfile", ".methodology.yml")
    interface = @("AGENTS.md", "README.md", "docs/ARCHITECTURE.md", ".methodology.yml")
    standalone = @("AGENTS.md", "README.md", "docs/ARCHITECTURE.md", ".methodology.yml")
}
$required = $requiredByType[$repositoryType]
foreach ($item in $required) {
    Add-Result -Id "VER-001" -Passed (Test-Path (Join-Path $Root $item)) -Message "Обязательный файл: $item" -Location $item
}

$forbiddenRootArtifacts = @()
if ($repositoryType -eq "methodology") {
    $forbiddenRootArtifacts = @("ARCHITECTURE.md", "BACKLOG.md", "COMPOSITION.md", "CONVENTIONS.md", "Dockerfile", "docker-compose.yml")
}
foreach ($item in $forbiddenRootArtifacts) {
    Add-Result -Id "VER-002" -Passed (-not (Test-Path (Join-Path $Root $item))) -Message "Запрещённый корневой артефакт: $item" -Location $item
}

$brokenLinks = @()
$linkPattern = [regex]::new('\[[^]]+\]\(([^)]+)')
Get-ChildItem -Path $Root -Recurse -File -Filter "*.md" | Where-Object {
    $_.FullName -notmatch "[\\/]\.git[\\/]"
} | ForEach-Object {
    $markdownFile = $_
    $content = Get-Content -Raw -Encoding utf8 $markdownFile.FullName
    foreach ($linkMatch in $linkPattern.Matches($content)) {
        $target = ($linkMatch.Groups[1].Value -split "#", 2)[0].Trim("<", ">")
        if (-not $target -or $target -match "^(https?://|mailto:|<)") { continue }
        $candidate = Join-Path $markdownFile.DirectoryName ([uri]::UnescapeDataString($target))
        if (-not (Test-Path $candidate)) { $brokenLinks += "$($markdownFile.FullName): $target" }
    }
}
$linksOk = $brokenLinks.Count -eq 0
$linksMessage = "Markdown-ссылки разрешаются"
if (-not $linksOk) { $linksMessage = "Висячие ссылки: " + ($brokenLinks -join "; ") }
Add-Result -Id "VER-010" -Passed $linksOk -Message $linksMessage -Location "*.md"

$invalidJson = @()
Get-ChildItem (Join-Path $PolicyRoot "schemas") -Filter "*.json" -File | ForEach-Object {
    try { Get-Content -Raw -Encoding utf8 $_.FullName | ConvertFrom-Json | Out-Null }
    catch { $invalidJson += $_.Name }
}
$jsonOk = $invalidJson.Count -eq 0
$jsonMessage = "JSON-схемы валидны"
if (-not $jsonOk) { $jsonMessage = "Невалидные JSON-схемы: " + ($invalidJson -join ", ") }
Add-Result -Id "VER-011" -Passed $jsonOk -Message $jsonMessage -Location "schemas/"

$backlogPath = if ($repositoryType -eq "hub") { Join-Path $Root "BACKLOG.md" } else { Join-Path $Root "skeletons/hub/BACKLOG.md" }
$inFlight = 0
if (Test-Path $backlogPath) {
    $inFlight = (Select-String -Path $backlogPath -Pattern "^### .*\[~\]" -Encoding utf8).Count
}
Add-Result -Id "VER-005" -Passed ($inFlight -le 1) -Message "В backlog не более одного активного пункта" -Location "skeletons/hub/BACKLOG.md"

$failed = @($checks | Where-Object { $_.status -eq "failed" }).Count -gt 0
$overall = "passed"
if ($failed) { $overall = "failed" }
$result = [pscustomobject]@{
    status = $overall
    repository_type = $repositoryType
    methodology_version = "development"
    checks = $checks
}
$json = $result | ConvertTo-Json -Depth 8
if ($Report) { Set-Content -Encoding utf8 -Path $Report -Value $json }
$json
if ($failed) { exit 1 }
