$ErrorActionPreference = 'Stop'
# PowerShell 7 can turn Git's expected stderr on an empty repository into a
# terminating NativeCommandError when ErrorActionPreference is Stop. Keep Git
# exit codes available for explicit checks below instead.
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
$RepoUrl = 'https://github.com/Brentph505/snake-game.git'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $ProjectRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is not installed. Install Git for Windows, then rerun this script.'
}

if (-not (Test-Path (Join-Path $ProjectRoot '.git'))) {
    git init --initial-branch=main
    if ($LASTEXITCODE -ne 0) { throw 'git init failed.' }
}

$branch = (git branch --show-current).Trim()
if ($branch -ne 'main') {
    Write-Host "Current branch is '$branch'; switching/renaming it to 'main'."
    git branch -M main
    if ($LASTEXITCODE -ne 0) { throw 'Could not set branch to main.' }
}

$remotes = @(git remote)
if ($remotes -contains 'origin') {
    $currentUrl = (git remote get-url origin).Trim()
    if ($currentUrl -ne $RepoUrl) {
        throw "origin already points to '$currentUrl'. Check the remote before uploading to avoid pushing to the wrong repository."
    }
} else {
    git remote add origin $RepoUrl
    if ($LASTEXITCODE -ne 0) { throw 'Could not configure the origin remote.' }
}

git add -A
if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }

# Create an initial commit when needed, or commit only if there are staged changes.
git show-ref --verify --quiet refs/heads/main
$hasCommit = ($LASTEXITCODE -eq 0)
git diff --cached --quiet
$hasStagedChanges = ($LASTEXITCODE -ne 0)
if (-not $hasCommit -or $hasStagedChanges) {
    $message = if (-not $hasCommit) { 'Import cleaned Repair Terminal project' } else { 'Update cleaned Repair Terminal project' }
    git commit -m $message
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed. Configure git user.name and user.email, then rerun.' }
} else {
    Write-Host 'No changes to commit; uploading the current main branch.'
}

git push -u origin main
if ($LASTEXITCODE -ne 0) {
    throw 'Push failed. Confirm GitHub sign-in/permissions. If the GitHub repository has existing commits, reconcile them before retrying.'
}
Write-Host "Upload complete: https://github.com/Brentph505/snake-game"
