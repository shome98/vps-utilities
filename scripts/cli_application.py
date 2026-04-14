import sys
import os
import time
from pathlib import Path

# Import from existing script.py
from script import (
    Emoji, read_json, write_json, execute,
    git_clone, git_checkout, pull_latest,
    docker_build, docker_start, docker_rebuild_image,
    stop_service, restart_service, delete_service,
    get_deployment_details, update_repo_tracking,
    deploy_docker, clone_and_checkout, resolve_docker_compose_file
)

# --- CLI Helper Functions ---

def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Print formatted header."""
    clear_screen()
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_separator():
    """Print separator line."""
    print(f"\n{'-'*60}")

def wait_for_enter(message="Press Enter to continue..."):
    """Wait for user to press Enter."""
    input(f"\n{message}")

def get_user_choice(prompt, choices):
    """Get validated user choice from list."""
    while True:
        choice = input(f"\n{prompt}").strip()
        if choice in choices:
            return choice
        print(f"{Emoji.WARNING.value} Invalid choice. Please try again.")

def get_yes_no(prompt):
    """Get yes/no confirmation."""
    while True:
        answer = input(f"\n{prompt} (y/n): ").strip().lower()
        if answer in ['y', 'yes']:
            return True
        elif answer in ['n', 'no']:
            return False
        print(f"{Emoji.WARNING.value} Please enter 'y' or 'n'.")

# --- Deployment Status Checking ---

def check_deployment_status(repo):
    """Check if deployment containers are running."""
    repo_path = repo.get('folderPath')
    
    if not repo_path or not Path(repo_path).exists():
        return f"{Emoji.ERROR.value} Missing"
    
    services = repo.get('services', [])
    if not services:
        return f"{Emoji.WARNING.value} Not Deployed"
    
    # Check if containers are actually running
    try:
        for service in services:
            container_id = service.get('id')
            if container_id:
                # Check container state
                result = execute("", f"docker inspect --format='{{{{.State.Status}}}}' {container_id}", 
                               capture=True)
                # Docker inspect returns the status with quotes, so we need to strip them
                status = result.strip("'\"")
                if status != 'running':
                    return f"{Emoji.WARNING.value} {status.title()}"
        return f"{Emoji.SUCCESS.value} Running"
    except:
        return f"{Emoji.WARNING.value} Unknown"

def get_deployment_mode(repo):
    """Get the deployment mode for a repository."""
    return repo.get('deployMode', 'dev')

# --- Core Features ---

def list_deployments():
    """Display all deployments with their current status."""
    print_header(f"{Emoji.FOLDER.value} Deployment Dashboard")
    
    repos = read_json('deployed_repos.json')
    
    if not repos:
        print(f"{Emoji.INFO.value} No deployments found.")
        wait_for_enter()
        return
    
    # Display table header
    print(f"{'#':<4} {'Name':<25} {'Status':<12} {'Branch':<15} {'Mode':<8} {'Services':<10}")
    print(f"{'-'*4} {'-'*25} {'-'*12} {'-'*15} {'-'*8} {'-'*10}")
    
    for idx, repo in enumerate(repos, 1):
        name = repo.get('folder_name', 'Unknown')
        branch = repo.get('checkoutBranch', 'N/A')
        services = repo.get('services', [])
        mode = repo.get('deployMode', 'dev')
        
        # Check actual Docker status
        status = check_deployment_status(repo)
        service_count = len(services) if services else 0
        
        print(f"{idx:<4} {name:<25} {status:<12} {branch:<15} {mode:<8} {service_count:<10}")
    
    print_separator()
    wait_for_enter()

def select_deployment():
    """Show deployments and let user select one."""
    repos = read_json('deployed_repos.json')
    
    if not repos:
        print(f"{Emoji.INFO.value} No deployments found.")
        wait_for_enter()
        return None
    
    print(f"\n{Emoji.INFO.value} Select a deployment:\n")
    
    for idx, repo in enumerate(repos, 1):
        name = repo.get('folder_name', 'Unknown')
        status = check_deployment_status(repo)
        print(f"  {idx}. {name} - {status}")
    
    print(f"\n  0. Cancel")
    
    choice = get_user_choice(f"\n{Emoji.ARROW.value} Enter number (0-{len(repos)}): ",
                            [str(i) for i in range(len(repos) + 1)])
    
    if choice == '0':
        return None
    
    return repos[int(choice) - 1]

def clone_and_deploy():
    """Interactive wizard to clone and deploy a new repository."""
    print_header(f"{Emoji.CLONE.value} Clone & Deploy New Repository")
    
    # Get repository URL
    url = input(f"{Emoji.LINK.value} GitHub Repository URL: ").strip()
    if not url:
        print(f"{Emoji.ERROR.value} URL cannot be empty.")
        wait_for_enter()
        return
    
    # Extract repo name
    repo_name = url.split('/')[-1].replace('.git', '')
    
    # Get branch
    branch = input(f"{Emoji.BRANCH.value} Branch (default: main): ").strip() or 'main'
    
    # Get env file path (optional)
    env_path = input(f"{Emoji.FILE.value} Env file name in scripts/ (optional, press Enter to skip): ").strip()
    env_path = env_path if env_path else None
    
    # Get deployment mode
    mode = get_user_choice(f"{Emoji.GEAR.value} Deployment mode (dev/qa/prod) [dev]: ", 
                          ['dev', 'qa', 'prod', '']) or 'dev'
    
    # Confirm
    print(f"\n{Emoji.INFO.value} Summary:")
    print(f"  Repository: {repo_name}")
    print(f"  URL: {url}")
    print(f"  Branch: {branch}")
    print(f"  Env File: {env_path or 'None'}")
    print(f"  Mode: {mode}")
    
    # Add missing Emoji.QUESTION
    if not get_yes_no(f"\n{Emoji.INFO.value} Proceed with deployment?"):
        print(f"{Emoji.INFO.value} Deployment cancelled.")
        wait_for_enter()
        return
    
    # Execute deployment
    try:
        repo_data = {
            'githubUrl': url,
            'checkoutBranch': branch,
            'envPath': env_path
        }
        
        repo_path, name, has_changes, is_new, env = clone_and_checkout(repo_data, mode=mode)
        
        if is_new:
            deploy_docker(repo_path, name, mode=mode, env_file=env)
        
        print(f"\n{Emoji.SUCCESS.value} Deployment completed successfully!")
    except Exception as e:
        print(f"\n{Emoji.ERROR.value} Deployment failed: {e}")
    
    wait_for_enter()

# --- Deployment Operations ---

def deployment_operations():
    """Show operations menu for selected deployment."""
    repo = select_deployment()
    if not repo:
        return
    
    repo_name = repo.get('folder_name')
    repo_path = Path(repo.get('folderPath', ''))
    branch = repo.get('checkoutBranch', 'main')
    env_path = repo.get('envPath')
    mode = get_deployment_mode(repo)
    
    while True:
        print_header(f"{Emoji.TOOLS.value} Operations: {repo_name}")
        
        status = check_deployment_status(repo)
        print(f"Status: {status}\n")
        
        print("  1. Start Service")
        print("  2. Stop Service")
        print("  3. Restart Service")
        print("  4. Re-deploy (Rebuild & Restart)")
        print("  5. Git Pull (Update Code)")
        print("  6. View Logs")
        print("  7. View Deployment Details")
        print("  8. Git Status & Diff")
        print("  9. Remove Deployment")
        print("  0. Back to Main Menu")
        
        choice = get_user_choice(f"\n{Emoji.ARROW.value} Select operation (0-9): ",
                                [str(i) for i in range(10)])
        
        if choice == '0':
            break
        
        try:
            if choice == '1':
                start_deployment(repo, repo_path, repo_name, mode, env_path)
            elif choice == '2':
                stop_deployment(repo)
            elif choice == '3':
                restart_deployment(repo, repo_path, repo_name)
            elif choice == '4':
                redeploy(repo, repo_path, repo_name, mode, env_path)
            elif choice == '5':
                git_pull_update(repo, repo_path, repo_name, branch, mode, env_path)
            elif choice == '6':
                view_logs(repo, repo_path)
            elif choice == '7':
                view_deployment_details(repo)
            elif choice == '8':
                view_git_status(repo_path)
            elif choice == '9':
                remove_deployment(repo, repo_name)
        except Exception as e:
            print(f"\n{Emoji.ERROR.value} Operation failed: {e}")
        
        wait_for_enter()

def start_deployment(repo, repo_path, repo_name, mode, env_path):
    """Start deployment service."""
    if not repo_path.exists():
        print(f"{Emoji.ERROR.value} Repository path not found.")
        return
    
    print(f"{Emoji.START_CONTAINER.value} Starting {repo_name}...")
    docker_start(repo_path, repo_name, mode=mode, env_file=env_path)
    
    # Update tracking
    image_info, services = get_deployment_details(repo_path)
    update_repo_tracking(repo_name, image_info=image_info, services=services)
    
    print(f"{Emoji.SUCCESS.value} Service started!")

def stop_deployment(repo):
    """Stop all containers for deployment."""
    services = repo.get('services', [])
    if not services:
        print(f"{Emoji.WARNING.value} No services to stop.")
        return
    
    print(f"{Emoji.STOP.value} Stopping {len(services)} container(s)...")
    for service in services:
        container_id = service.get('id')
        container_name = service.get('name')
        if container_id or container_name:
            stop_service(container_id, container_name)
    
    # Update tracking
    repo_name = repo.get('folder_name')
    update_repo_tracking(repo_name, services=[])
    
    print(f"{Emoji.SUCCESS.value} Services stopped!")

def restart_deployment(repo, repo_path, repo_name):
    """Restart all containers."""
    services = repo.get('services', [])
    if not services:
        print(f"{Emoji.WARNING.value} No services to restart.")
        return
    
    print(f"{Emoji.RESTART.value} Restarting {len(services)} container(s)...")
    for service in services:
        container_id = service.get('id')
        container_name = service.get('name')
        if container_id or container_name:
            restart_service(container_id, container_name)
    
    print(f"{Emoji.SUCCESS.value} Services restarted!")

def redeploy(repo, repo_path, repo_name, mode, env_path):
    """Rebuild and redeploy."""
    if not get_yes_no(f"{Emoji.WARNING.value} This will rebuild and redeploy {repo_name}. Continue?"):
        return
    
    docker_rebuild_image(repo_path, repo_name, mode=mode, env_file=env_path)
    print(f"{Emoji.SUCCESS.value} Re-deployment completed!")

def git_pull_update(repo, repo_path, repo_name, branch, mode, env_path):
    """Pull latest changes and redeploy if changes detected."""
    print(f"{Emoji.PULL.value} Pulling latest changes from {branch}...")
    
    # Get commit before
    commit_before = execute("", "git rev-parse HEAD", cwd=repo_path, capture=True)
    
    # Pull
    pull_latest(repo_path, branch)
    
    # Get commit after
    commit_after = execute("", "git rev-parse HEAD", cwd=repo_path, capture=True)
    
    if commit_before != commit_after:
        print(f"{Emoji.INFO.value} Changes detected. Rebuilding...")
        docker_rebuild_image(repo_path, repo_name, mode=mode, env_file=env_path)
    else:
        print(f"{Emoji.SUCCESS.value} Already up to date. No rebuild needed.")

def view_logs(repo, repo_path):
    """View Docker container logs."""
    services = repo.get('services', [])
    if not services:
        print(f"{Emoji.WARNING.value} No services running.")
        return
    
    print(f"\n{Emoji.INFO.value} Available services:")
    for idx, service in enumerate(services, 1):
        print(f"  {idx}. {service.get('name')}")
    
    choice = get_user_choice(f"\n{Emoji.ARROW.value} Select service to view logs: ",
                            [str(i) for i in range(1, len(services) + 1)])
    
    service_name = services[int(choice) - 1].get('name')
    print(f"\n{Emoji.INFO.value} Showing logs for {service_name} (Ctrl+C to exit):\n")
    
    try:
        execute("", f"docker compose -f docker-compose.yml logs -f {service_name}", 
               cwd=repo_path)
    except KeyboardInterrupt:
        print(f"\n{Emoji.INFO.value} Logs closed.")

def view_deployment_details(repo):
    """Show detailed deployment information."""
    print_header(f"{Emoji.INFO.value} Deployment Details: {repo.get('folder_name')}")
    
    print(f"Name: {repo.get('folder_name')}")
    print(f"Path: {repo.get('folderPath')}")
    print(f"URL: {repo.get('githubUrl')}")
    print(f"Branch: {repo.get('checkoutBranch')}")
    print(f"Mode: {repo.get('deployMode', 'dev')}")
    print(f"Env File: {repo.get('envPath', 'None')}")
    
    # Show docker-compose file being used
    repo_path = Path(repo.get('folderPath', ''))
    mode = get_deployment_mode(repo)
    compose_file, compose_path = resolve_docker_compose_file(repo_path, mode)
    if compose_file:
        print(f"Docker Compose: {compose_file}")
    else:
        print(f"Docker Compose: {Emoji.WARNING.value} Not found")
    
    image = repo.get('image', {})
    if image:
        print(f"\nImage:")
        print(f"  Name: {image.get('name')}")
        print(f"  ID: {image.get('id', 'N/A')[:12]}")
    
    services = repo.get('services', [])
    if services:
        print(f"\nServices ({len(services)}):")
        for service in services:
            print(f"  - {service.get('name')} ({service.get('id', 'N/A')[:12]})")

def view_git_status(repo_path):
    """Show git status and recent commits."""
    print_header(f"{Emoji.INFO.value} Git Status")
    
    # Show status
    print(f"\n{Emoji.FILE.value} Working Tree Status:")
    status = execute("", "git status --short", cwd=repo_path, capture=True)
    print(status if status else "  Clean (no changes)")
    
    # Show recent commits
    print(f"\n{Emoji.BRANCH.value} Recent Commits:")
    commits = execute("", "git log --oneline -5", cwd=repo_path, capture=True)
    print(commits)

def remove_deployment(repo, repo_name):
    """Remove deployment completely."""
    if not get_yes_no(f"{Emoji.ERROR.value} WARNING: This will remove {repo_name} completely. Continue?"):
        return
    
    # Stop and remove containers
    services = repo.get('services', [])
    for service in services:
        container_id = service.get('id')
        container_name = service.get('name')
        if container_id or container_name:
            try:
                stop_service(container_id, container_name)
                delete_service(container_id, container_name)
            except:
                print(f"{Emoji.WARNING.value} Could not stop/remove container {container_name} (may already be stopped)")
    
    # Remove from tracking
    repos = read_json('deployed_repos.json')
    repos = [r for r in repos if r.get('folder_name') != repo_name]
    write_json('deployed_repos.json', repos)
    
    print(f"{Emoji.SUCCESS.value} Deployment removed from tracking.")
    print(f"{Emoji.WARNING.value} Repository files still exist at: {repo.get('folderPath')}")

# --- Main Menu ---

def main_menu():
    """Display main menu and handle user choice."""
    while True:
        print_header(f"{Emoji.DOCKER.value} Deployment Manager CLI")
        
        print("  1. List All Deployments (Dashboard)")
        print("  2. Clone & Deploy New Repository")
        print("  3. Manage Deployment (Start/Stop/Restart/Redeploy)")
        print("  4. Batch Operations (Coming Soon)")
        print("  5. View Configuration")
        print("  0. Exit")
        
        choice = get_user_choice(f"\n{Emoji.ARROW.value} Select option (0-5): ",
                                [str(i) for i in range(6)])
        
        if choice == '0':
            print(f"\n{Emoji.SUCCESS.value} Goodbye!")
            sys.exit(0)
        elif choice == '1':
            list_deployments()
        elif choice == '2':
            clone_and_deploy()
        elif choice == '3':
            deployment_operations()
        elif choice == '4':
            print(f"{Emoji.INFO.value} Batch operations - Coming soon!")
            wait_for_enter()
        elif choice == '5':
            view_configuration()

def view_configuration():
    """View current configuration."""
    print_header(f"{Emoji.GEAR.value} Configuration")
    
    config = read_json('commands_2.json')
    print(f"Config File: commands_2.json\n")
    print(f"Repositories: {len(config.get('repositories', []))}")
    print(f"Installation Steps: {len(config.get('installation_steps', []))}")
    
    wait_for_enter()

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Emoji.WARNING.value} Interrupted by user.")
        print(f"{Emoji.SUCCESS.value} Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Emoji.ERROR.value} Unexpected error: {e}")
        sys.exit(1)
