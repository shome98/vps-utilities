#!/bin/bash

# API Factory - Git Clone & Setup Script (Bash)
# Clones all 5 repositories and checks out to dev branch

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

# Functions
write_success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

write_info() {
    echo -e "${CYAN}[INFO] $1${NC}"
}

write_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

write_header() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

write_separator() {
    echo ""
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo ""
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Repository definitions
REPO_NAMES=(
    "Auth API"
    "PG Registry API"
    "Mongo Factory API"
    "Payments & Subscriptions API"
    "Frontend (Next.js)"
)

REPO_DIRS=(
    "auth-api"
    "af-pg-registry-api"
    "api-factory-mongo"
    "payments-subscriptions-api"
    "af-client-user-next"
)

REPO_URLS=(
    ""
    ""
    ""
    ""
    ""
)

REPO_BRANCHES=(
    "dev"
    "dev"
    "dev"
    "dev"
    "dev"
)

# Check if Git is installed
test_git() {
    if command -v git &> /dev/null; then
        write_success "Git found"
        return 0
    else
        write_error "Git is not installed. Please install Git first."
        echo "Download from: https://git-scm.com/downloads"
        return 1
    fi
}

# Clone a single repository
clone_repository() {
    local index=$1
    local array_index=$2
    local total=$3
    local parent_dir=$4
    
    local name="${REPO_NAMES[$array_index]}"
    local dir_name="${REPO_DIRS[$array_index]}"
    local url="${REPO_URLS[$array_index]}"
    local branch="${REPO_BRANCHES[$array_index]}"
    local target_dir="$parent_dir/$dir_name"
    
    write_separator "[$index/$total] Cloning: $name"
    echo -e "Repository: ${WHITE}$url${NC}"
    echo -e "Directory: ${WHITE}$target_dir${NC}"
    echo -e "Branch: ${WHITE}$branch${NC}"
    echo ""
    
    # Check if directory already exists
    if [ -d "$target_dir" ]; then
        write_error "Directory already exists: $target_dir"
        read -p "Do you want to delete it and re-clone? (y/n): " overwrite
        if [ "$overwrite" = "y" ]; then
            write_info "Removing existing directory..."
            rm -rf "$target_dir"
        else
            write_info "Skipping $name"
            return 1
        fi
    fi
    
    # Clone repository
    write_info "Cloning $name..."
    if git clone "$url" "$target_dir"; then
        write_success "$name cloned successfully"
        
        # Checkout to dev branch
        cd "$target_dir" || return 1
        
        write_info "Checking out to branch: $branch"
        if git checkout "$branch"; then
            write_success "Switched to branch '$branch'"
            
            # Pull latest changes
            write_info "Pulling latest changes..."
            if git pull origin "$branch"; then
                write_success "Repository is up to date"
            else
                write_error "Failed to pull latest changes"
            fi
            
            return 0
        else
            write_error "Branch '$branch' not found. Available branches:"
            git branch -r | sed 's/^/  /'
            echo ""
            write_info "Keeping default branch (usually main/master)"
            return 0
        fi
    else
        write_error "Failed to clone $name"
        return 1
    fi
}

# Main Script
write_header "API Factory - Git Clone & Setup"

write_info "Script Directory: $SCRIPT_DIR"
echo ""

# Check prerequisites
test_git || exit 1

echo ""

# Get GitHub username/organization
write_header "Repository Configuration"

read -p "Use custom repository URLs? (y/n - press Enter for defaults): " use_custom_urls

if [ "$use_custom_urls" = "y" ]; then
    echo ""
    write_info "Enter the full Git URLs for each repository:"
    echo "(Example: https://github.com/your-org/auth-api.git)"
    echo ""
    
    for i in "${!REPO_NAMES[@]}"; do
        read -p "${REPO_NAMES[$i]} URL: " url
        if [ -n "$url" ]; then
            REPO_URLS[$i]="$url"
        fi
    done
else
    # Default URLs - Update these with your actual repository URLs
    REPO_URLS[0]="https://github.com/shome98/auth-api.git"
    REPO_URLS[1]="https://github.com/shome98/af-pg-registry-api.git"
    REPO_URLS[2]="https://github.com/shome98/api-factory-mongo.git"
    REPO_URLS[3]="https://github.com/shome98/payments-subscriptions-api.git"
    REPO_URLS[4]="https://github.com/shome98/af-client.git"
    
    write_info "Using default repository URLs"
    echo ""
    echo -e "${CYAN}Repositories to clone:${NC}"
    for i in "${!REPO_NAMES[@]}"; do
        echo -e "  $((i + 1)). ${WHITE}${REPO_NAMES[$i]}${NC}"
        echo -e "     ${GRAY}${REPO_URLS[$i]}${NC}"
    done
    echo ""
    
    read -p "Continue with these URLs? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        write_info "Aborted. Please update the default URLs in the script."
        exit 0
    fi
fi

echo ""

# Get target directory
read -p "Parent directory for clones (press Enter for current directory): " parent_dir
if [ -z "$parent_dir" ]; then
    parent_dir="$SCRIPT_DIR"
fi

# Create parent directory if it doesn't exist
if [ ! -d "$parent_dir" ]; then
    write_info "Creating directory: $parent_dir"
    mkdir -p "$parent_dir"
fi

echo ""

# Clone all repositories sequentially
write_header "Cloning All Repositories"

successful=0
failed=0
failed_repos=()

for i in "${!REPO_NAMES[@]}"; do
    index=$((i + 1))
    total=${#REPO_NAMES[@]}
    
    if clone_repository $index $i $total "$parent_dir"; then
        ((successful++))
    else
        ((failed++))
        failed_repos+=("${REPO_NAMES[$i]}")
    fi
    
    # Small delay between clones
    sleep 1
done

# Show summary
echo ""
write_header "Clone Summary"

echo -e "${GREEN}Successful: $successful${NC}"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed: $failed${NC}"
    echo -e "${RED}Failed repositories:${NC}"
    for repo in "${failed_repos[@]}"; do
        echo -e "${RED}  - $repo${NC}"
    done
else
    echo -e "${GREEN}Failed: 0${NC}"
fi
echo ""

# Show cloned directories
if [ $successful -gt 0 ]; then
    echo -e "${CYAN}Cloned repositories:${NC}"
    echo -e "${CYAN}========================================${NC}"
    
    cd "$parent_dir" || exit 1
    for i in "${!REPO_NAMES[@]}"; do
        target_dir="$parent_dir/${REPO_DIRS[$i]}"
        if [ -d "$target_dir" ]; then
            cd "$target_dir" || continue
            branch=$(git branch --show-current 2>/dev/null)
            commit=$(git log --oneline -1 2>/dev/null)
            echo -e "  ${GREEN}✓ ${REPO_DIRS[$i]}${NC}"
            echo -e "    ${GRAY}Branch: $branch${NC}"
            echo -e "    ${GRAY}Latest: $commit${NC}"
            echo ""
        fi
    done
fi

# Next steps
write_header "Next Steps"

echo -e "${YELLOW}1. Configure environment variables:${NC}"
for i in "${!REPO_NAMES[@]}"; do
    target_dir="$parent_dir/${REPO_DIRS[$i]}"
    if [ -d "$target_dir" ]; then
        echo -e "   ${WHITE}cd ${REPO_DIRS[$i]}${NC}"
        echo -e "   ${GRAY}cp .env.example .env  (or create .env file)${NC}"
    fi
done

echo ""
echo -e "${YELLOW}2. Install dependencies:${NC}"
for i in "${!REPO_NAMES[@]}"; do
    target_dir="$parent_dir/${REPO_DIRS[$i]}"
    if [ -d "$target_dir" ]; then
        echo -e "   ${WHITE}cd ${REPO_DIRS[$i]}${NC}"
        echo -e "   ${GRAY}npm install${NC}"
    fi
done

echo ""
echo -e "${YELLOW}3. Start services:${NC}"
echo -e "   ${WHITE}cd ngnix-confs-2${NC}"
echo -e "   ${GRAY}./start-factory-apps.sh${NC}"

echo ""
if [ $failed -eq 0 ]; then
    write_success "All repositories cloned successfully!"
else
    echo -e "${YELLOW}Some repositories failed to clone. Check the errors above for details.${NC}"
fi
echo ""

# Return to original directory
cd "$SCRIPT_DIR"
