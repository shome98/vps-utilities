# API Factory - Git Clone & Setup Script (PowerShell)
# Clones all 5 repositories and checks out to dev branch

$ErrorActionPreference = "Continue"

# Colors
function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Separator {
    param([string]$Message)
    Write-Host ""
    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host "  $Message" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host ""
}

# Get script directory
$ScriptDir = $PSScriptRoot

# Repository definitions
$Repositories = @(
    @{
        Name = "Auth API"
        DirName = "auth-api"
        Url = ""  # Will be prompted or use default
        Branch = "dev"
    },
    @{
        Name = "PG Registry API"
        DirName = "af-pg-registry-api"
        Url = ""
        Branch = "dev"
    },
    @{
        Name = "Mongo Factory API"
        DirName = "api-factory-mongo"
        Url = ""
        Branch = "dev"
    },
    @{
        Name = "Payments & Subscriptions API"
        DirName = "payments-subscriptions-api"
        Url = ""
        Branch = "dev"
    },
    @{
        Name = "Frontend (Next.js)"
        DirName = "af-client-user-next"
        Url = ""
        Branch = "dev"
    }
)

# Check if Git is installed
function Test-Git {
    try {
        $null = git --version
        Write-Success "Git found"
        return $true
    } catch {
        Write-Error-Custom "Git is not installed. Please install Git first."
        Write-Host "Download from: https://git-scm.com/downloads" -ForegroundColor Yellow
        return $false
    }
}

# Clone a single repository
function Clone-Repository {
    param(
        [hashtable]$Repo,
        [int]$Index,
        [int]$Total,
        [string]$TargetDir
    )
    
    Write-Separator "[$Index/$Total] Cloning: $($Repo.Name)"
    Write-Host "Repository: $($Repo.Url)" -ForegroundColor White
    Write-Host "Directory: $TargetDir" -ForegroundColor White
    Write-Host "Branch: $($Repo.Branch)" -ForegroundColor White
    Write-Host ""
    
    # Check if directory already exists
    if (Test-Path $TargetDir) {
        Write-Error-Custom "Directory already exists: $TargetDir"
        $overwrite = Read-Host "Do you want to delete it and re-clone? (y/n)"
        if ($overwrite -eq "y") {
            Write-Info "Removing existing directory..."
            Remove-Item -Path $TargetDir -Recurse -Force
        } else {
            Write-Info "Skipping $($Repo.Name)"
            return $false
        }
    }
    
    try {
        # Clone repository
        Write-Info "Cloning $($Repo.Name)..."
        Set-Location (Split-Path $TargetDir -Parent)
        
        git clone $Repo.Url $TargetDir
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to clone $($Repo.Name)"
            return $false
        }
        
        Write-Success "$($Repo.Name) cloned successfully"
        
        # Checkout to dev branch
        Set-Location $TargetDir
        
        Write-Info "Checking out to branch: $($Repo.Branch)"
        git checkout $Repo.Branch
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Switched to branch '$($Repo.Branch)'"
            
            # Pull latest changes
            Write-Info "Pulling latest changes..."
            git pull origin $Repo.Branch
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Repository is up to date"
            } else {
                Write-Error-Custom "Failed to pull latest changes"
            }
            
            return $true
        } else {
            Write-Error-Custom "Branch '$($Repo.Branch)' not found. Available branches:"
            git branch -r | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
            Write-Host ""
            Write-Info "Keeping default branch (usually main/master)"
            return $true
        }
    } catch {
        Write-Error-Custom "Error cloning $($Repo.Name): $_"
        return $false
    }
}

# Main Script
Write-Header "API Factory - Git Clone & Setup"

Write-Info "Script Directory: $ScriptDir"
Write-Host ""

# Check prerequisites
if (-not (Test-Git)) { exit 1 }

Write-Host ""

# Get GitHub username/organization
Write-Header "Repository Configuration"

$useCustomUrls = Read-Host "Use custom repository URLs? (y/n - press Enter for defaults)"

if ($useCustomUrls -eq "y") {
    Write-Host ""
    Write-Info "Enter the full Git URLs for each repository:"
    Write-Host "(Example: https://github.com/your-org/auth-api.git)"
    Write-Host ""
    
    for ($i = 0; $i -lt $Repositories.Count; $i++) {
        $repo = $Repositories[$i]
        $url = Read-Host "$($repo.Name) URL"
        if ($url) {
            $Repositories[$i].Url = $url
        }
    }
} else {
    # Default URLs - Update these with your actual repository URLs
     $Repositories[0].Url ="https://github.com/shome98/auth-api.git"
    $Repositories[1].Url = "https://github.com/shome98/af-pg-registry-api.git"
    $Repositories[2].Url = "https://github.com/shome98/api-factory-mongo.git"
    $Repositories[3].Url = "https://github.com/shome98/payments-subscriptions-api.git"
    $Repositories[4].Url = "https://github.com/shome98/af-client.git"
    
    Write-Info "Using default repository URLs"
    Write-Host ""
    Write-Host "Repositories to clone:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $Repositories.Count; $i++) {
        Write-Host "  $($i + 1). $($Repositories[$i].Name)" -ForegroundColor White
        Write-Host "     $($Repositories[$i].Url)" -ForegroundColor Gray
    }
    Write-Host ""
    
    $confirm = Read-Host "Continue with these URLs? (y/n)"
    if ($confirm -ne "y") {
        Write-Info "Aborted. Please update the default URLs in the script."
        exit 0
    }
}

Write-Host ""

# Get target directory
$parentDir = Read-Host "Parent directory for clones (press Enter for current directory)"
if (-not $parentDir) {
    $parentDir = $ScriptDir
}

# Create parent directory if it doesn't exist
if (-not (Test-Path $parentDir)) {
    Write-Info "Creating directory: $parentDir"
    New-Item -Path $parentDir -ItemType Directory -Force | Out-Null
}

Write-Host ""

# Clone all repositories sequentially
Write-Header "Cloning All Repositories"

$successful = 0
$failed = 0
$failedRepos = @()

for ($i = 0; $i -lt $Repositories.Count; $i++) {
    $repo = $Repositories[$i]
    $targetDir = Join-Path $parentDir $repo.DirName
    
    $result = Clone-Repository -Repo $repo -Index ($i + 1) -Total $Repositories.Count -TargetDir $targetDir
    
    if ($result) {
        $successful++
    } else {
        $failed++
        $failedRepos += $repo.Name
    }
    
    # Small delay between clones
    Start-Sleep -Seconds 1
}

# Show summary
Write-Host ""
Write-Header "Clone Summary"

Write-Host "Successful: $successful" -ForegroundColor Green
if ($failed -gt 0) {
    Write-Host "Failed: $failed" -ForegroundColor Red
    Write-Host "Failed repositories:" -ForegroundColor Red
    foreach ($failedRepo in $failedRepos) {
        Write-Host "  - $failedRepo" -ForegroundColor Red
    }
} else {
    Write-Host "Failed: 0" -ForegroundColor Green
}
Write-Host ""

# Show cloned directories
if ($successful -gt 0) {
    Write-Host "Cloned repositories:" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    Set-Location $parentDir
    foreach ($repo in $Repositories) {
        $targetDir = Join-Path $parentDir $repo.DirName
        if (Test-Path $targetDir) {
            Set-Location $targetDir
            $branch = git branch --show-current 2>$null
            $commit = git log --oneline -1 2>$null
            Write-Host "  [OK] $($repo.DirName)" -ForegroundColor Green
            Write-Host "    Branch: $branch" -ForegroundColor Gray
            Write-Host "    Latest: $commit" -ForegroundColor Gray
            Write-Host ""
        }
    }
}

# Next steps
Write-Header "Next Steps"

Write-Host "1. Configure environment variables:" -ForegroundColor Yellow
foreach ($repo in $Repositories) {
    $targetDir = Join-Path $parentDir $repo.DirName
    if (Test-Path $targetDir) {
        Write-Host "   cd $($repo.DirName)" -ForegroundColor White
        Write-Host "   copy .env.example .env  (or create .env file)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "2. Install dependencies:" -ForegroundColor Yellow
foreach ($repo in $Repositories) {
    $targetDir = Join-Path $parentDir $repo.DirName
    if (Test-Path $targetDir) {
        Write-Host "   cd $($repo.DirName)" -ForegroundColor White
        Write-Host "   npm install" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "3. Start services:" -ForegroundColor Yellow
Write-Host "   cd ngnix-confs-2" -ForegroundColor White
Write-Host "   ./start-factory-apps.ps1" -ForegroundColor Gray

Write-Host ""
if ($failed -eq 0) {
    Write-Success "All repositories cloned successfully!"
} else {
    Write-Host "Some repositories failed to clone. Check the errors above for details." -ForegroundColor Yellow
}
Write-Host ""

# Return to original directory
Set-Location $ScriptDir
