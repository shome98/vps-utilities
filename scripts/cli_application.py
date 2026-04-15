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
    deploy_docker, clone_and_checkout, resolve_docker_compose_file,
    load_installation_steps, execute_installation_steps,
    get_all_containers_status, validate_batch_json,
    DEPLOYMENT_UTILS_DIR, APPS_DIR, SCRIPTS_DIR,
    resolve_authenticated_url, get_credentials, get_token_by_id,
    CREDENTIALS_FILE
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

# --- UI Helpers ---

def display_menu(title, options, subtitle=None):
    """
    Displays a menu from a list of options and returns the validated choice.
    options: list of dicts with 'id' and 'name'
    """
    print_header(title)
    if subtitle:
        print(f"{subtitle}\n")
    
    for opt in options:
        print(f"  {opt['id']}. {opt['name']}")
    
    valid_ids = [str(opt['id']) for opt in options]
    # Re-use get_user_choice but provide a clean prompt
    range_str = f"0-{len(options)-1}" if "0" in valid_ids else f"1-{len(options)}"
    return get_user_choice(f"Select option ({range_str}): ", valid_ids)

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
    
    repos = read_json(DEPLOYMENT_UTILS_DIR / 'deployed_repos.json')
    
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

def show_services_status():
    """Display status of all running Docker services."""
    print_header(f"{Emoji.CONTAINER.value} Services Status")
    
    repos = read_json(DEPLOYMENT_UTILS_DIR / 'deployed_repos.json')
    
    if not repos:
        print(f"{Emoji.INFO.value} No deployments found.")
        wait_for_enter()
        return
    
    # Track total stats
    total_containers = 0
    running_count = 0
    
    for repo in repos:
        repo_name = repo.get('folder_name')
        services = repo.get('services', [])
        
        if not services:
            continue
        
        print(f"\n{Emoji.FOLDER.value} {repo_name}:")
        print(f"  {'Name':<25} {'ID':<15} {'Status':<15}")
        print(f"  {'-'*25} {'-'*15} {'-'*15}")
        
        for service in services:
            container_id = service.get('id')
            container_name = service.get('name')
            
            if container_id:
                # Get container status
                status = execute("", f"docker inspect --format='{{{{.State.Status}}}}' {container_id}", 
                               capture=True).strip("'\"")
                
                status_emoji = Emoji.SUCCESS.value if status == 'running' else Emoji.WARNING.value
                print(f"  {container_name:<25} {container_id[:12]:<15} {status_emoji} {status.title()}")
                
                total_containers += 1
                if status == 'running':
                    running_count += 1
    
    if total_containers == 0:
        print(f"\n{Emoji.INFO.value} No services deployed.")
    else:
        print_separator()
        print(f"\n{Emoji.INFO.value} Total: {running_count}/{total_containers} containers running")
    
    wait_for_enter()

def select_deployment():
    """Show deployments and let user select one."""
    repos = read_json(DEPLOYMENT_UTILS_DIR / 'deployed_repos.json')
    
    if not repos:
        print(f"{Emoji.INFO.value} No deployments found.")
        wait_for_enter()
        return None
    
    options = []
    for idx, repo in enumerate(repos, 1):
        name = repo.get('folder_name', 'Unknown')
        status = check_deployment_status(repo)
        options.append({"id": str(idx), "name": f"{name} - {status}"})
    
    options.append({"id": "0", "name": "Cancel"})
    
    choice = display_menu(f"{Emoji.INFO.value} Select a deployment", options)
    
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
    
    # Get Private Status
    is_private = get_yes_no(f"{Emoji.KEY.value} Is this a private repository?")
    cred_id = None
    
    if is_private:
        creds = get_credentials()
        if creds:
            print(f"\n{Emoji.INFO.value} Select credential to use:")
            cred_options = [{"id": str(i+1), "name": c.get('alias')} for i, c in enumerate(creds)]
            cred_options.append({"id": "0", "name": "Manual Entry (One-time)"})
            cred_options.append({"id": "N", "name": "Add New Credential"})
            
            cred_choice = display_menu(f"{Emoji.KEY.value} Select Credential", cred_options)
            
            if cred_choice == "0":
                cred_id = input("Enter PAT Token: ").strip()
            elif cred_choice == "N":
                add_credential_flow()
                # Reload creds and select last one
                creds = get_credentials()
                cred_id = creds[-1]['id'] if creds else None
            else:
                cred_id = creds[int(cred_choice)-1]['id']
        else:
            print(f"{Emoji.WARNING.value} No saved credentials found.")
            if get_yes_no("Add new credential now?"):
                add_credential_flow()
                creds = get_credentials()
                cred_id = creds[-1]['id'] if creds else None
            else:
                cred_id = input("Enter PAT Token (One-time): ").strip()

    # Confirm
    print(f"\n{Emoji.INFO.value} Summary:")
    print(f"  Repository: {repo_name}")
    print(f"  URL: {url}")
    print(f"  Private: {'Yes' if is_private else 'No'}")
    print(f"  Branch: {branch}")
    print(f"  Env File: {env_path or 'None'}")
    print(f"  Mode: {mode}")
    
    # Add missing Emoji.QUESTION
    if not get_yes_no(f"\n{Emoji.QUESTION.value} Proceed with deployment?"):
        print(f"{Emoji.INFO.value} Deployment cancelled.")
        wait_for_enter()
        return
    
    # Execute deployment
    try:
        repo_data = {
            'githubUrl': url,
            'checkoutBranch': branch,
            'envPath': env_path,
            'credentialId': cred_id
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
        options = [
            {"id": "1", "name": "Start Service"},
            {"id": "2", "name": "Stop Service"},
            {"id": "3", "name": "Restart Service"},
            {"id": "4", "name": "Re-deploy (Rebuild & Restart)"},
            {"id": "5", "name": "Git Pull (Update Code)"},
            {"id": "6", "name": "View Logs"},
            {"id": "7", "name": "View Deployment Details"},
            {"id": "8", "name": "Git Status & Diff"},
            {"id": "9", "name": "Remove Deployment"},
            {"id": "0", "name": "Back to Main Menu"}
        ]
        
        status = check_deployment_status(repo)
        subtitle = f"Status: {status}"
        
        choice = display_menu(f"{Emoji.TOOLS.value} Operations: {repo_name}", options, subtitle=subtitle)
        
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
    
    options = [{"id": str(idx), "name": service.get('name')} 
               for idx, service in enumerate(services, 1)]
    
    choice = display_menu(f"{Emoji.INFO.value} Available Services", options)
    
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
    repos = read_json(DEPLOYMENT_UTILS_DIR / 'deployed_repos.json')
    repos = [r for r in repos if r.get('folder_name') != repo_name]
    write_json(DEPLOYMENT_UTILS_DIR / 'deployed_repos.json', repos)
    
    print(f"{Emoji.SUCCESS.value} Deployment removed from tracking.")
    print(f"{Emoji.WARNING.value} Repository files still exist at: {repo.get('folderPath')}")

def batch_deploy_from_json():
    """Batch deploy multiple repositories from JSON file."""
    print_header(f"{Emoji.BATCH.value} Batch Deployment from JSON")
    
    # Get JSON file path
    json_path = input(f"{Emoji.FILE.value} Enter JSON file path: ").strip()
    if not json_path:
        print(f"{Emoji.ERROR.value} File path cannot be empty.")
        wait_for_enter()
        return
    
    # Resolve path: Try absolute, then deployment-utilities folder, then scripts folder
    batch_file = Path(json_path)
    if not batch_file.is_absolute():
        # Check deployment-utilities first
        if (DEPLOYMENT_UTILS_DIR / json_path).exists():
            batch_file = DEPLOYMENT_UTILS_DIR / json_path
        else:
            # Fallback to scripts dir
            batch_file = SCRIPTS_DIR / json_path
    
    if not batch_file.exists():
        print(f"{Emoji.ERROR.value} File not found: {batch_file}")
        wait_for_enter()
        return
    
    # Read and validate JSON
    try:
        batch_data = read_json(batch_file)
        if not isinstance(batch_data, list):
            print(f"{Emoji.ERROR.value} JSON must be an array of repository objects.")
            wait_for_enter()
            return
        
        # Validate structure
        is_valid, msg = validate_batch_json(batch_data)
        if not is_valid:
            print(f"{Emoji.ERROR.value} Invalid JSON structure: {msg}")
            wait_for_enter()
            return
    except Exception as e:
        print(f"{Emoji.ERROR.value} Invalid JSON file: {e}")
        wait_for_enter()
        return
    
    # Show summary
    print(f"\n{Emoji.INFO.value} Found {len(batch_data)} repositories to deploy:\n")
    for idx, repo in enumerate(batch_data, 1):
        url = repo.get('githubUrl', 'N/A')
        branch = repo.get('checkoutBranch', 'main')
        mode = repo.get('deployMode', 'dev')
        env = repo.get('envPath', 'None')
        repo_name = url.split('/')[-1].replace('.git', '')
        print(f"  {idx}. {repo_name} (branch: {branch}, mode: {mode}, env: {env})")
    
    if not get_yes_no(f"\n{Emoji.INFO.value} Proceed with batch deployment?"):
        print(f"{Emoji.INFO.value} Batch deployment cancelled.")
        wait_for_enter()
        return
    
    # Execute deployments
    success_count = 0
    failed_count = 0
    results = []
    
    for idx, repo_data in enumerate(batch_data, 1):
        repo_name = repo_data.get('githubUrl', '').split('/')[-1].replace('.git', '')
        print(f"\n{'='*60}")
        print(f"{Emoji.ARROW.value} [{idx}/{len(batch_data)}] Deploying: {repo_name}")
        print(f"{'='*60}")
        
        try:
            mode = repo_data.get('deployMode', 'dev')
            repo_path, name, has_changes, is_new, env = clone_and_checkout(repo_data, mode=mode)
            
            if is_new:
                deploy_docker(repo_path, name, mode=mode, env_file=env)
            
            success_count += 1
            results.append({'repo': repo_name, 'status': 'Success'})
            print(f"\n{Emoji.SUCCESS.value} {repo_name} deployed successfully!")
        except Exception as e:
            failed_count += 1
            results.append({'repo': repo_name, 'status': f'Failed: {e}'})
            print(f"\n{Emoji.ERROR.value} {repo_name} deployment failed: {e}")
    
    # Show summary
    print_separator()
    print(f"\n{Emoji.INFO.value} Batch Deployment Summary:")
    print(f"  Total: {len(batch_data)}")
    print(f"  {Emoji.SUCCESS.value} Success: {success_count}")
    print(f"  {Emoji.ERROR.value} Failed: {failed_count}")
    
    wait_for_enter()

def batch_operations_menu():
    """Submenu for batch operations."""
    while True:
        options = [
            {"id": "1", "name": "Deploy from JSON File"},
            {"id": "2", "name": "Coming Soon: Export Deployments to JSON"},
            {"id": "0", "name": "Back to Main Menu"}
        ]
        
        choice = display_menu(f"{Emoji.BATCH.value} Batch Operations", options)
        
        if choice == '0':
            break
        elif choice == '1':
            batch_deploy_from_json()
        elif choice == '2':
            print(f"{Emoji.INFO.value} Feature coming soon!")
            wait_for_enter()

def manage_installations():
    """Interactive installation steps manager."""
    # Define default installation files
    default_installations = {
        '1': {'name': 'Docker Installation', 'file': DEPLOYMENT_UTILS_DIR / 'docker_installation_commands.json'}
    }
    
    options = []
    for key, install in default_installations.items():
        exists_mark = "✓" if install['file'].exists() else "✗"
        options.append({"id": key, "name": f"{install['name']} [{exists_mark}]"})
    
    options.append({"id": "2", "name": "Provide custom JSON file path"})
    options.append({"id": "0", "name": "Cancel"})
    
    choice = display_menu(f"{Emoji.TOOLS.value} Installation Manager", options, 
                         subtitle="Select installation source:")
    
    if choice == '0':
        return
    
    # Get JSON file path
    if choice == '2':
        json_path = input(f"\n{Emoji.FILE.value} Enter JSON file path: ").strip()
        if not json_path:
            print(f"{Emoji.ERROR.value} Path cannot be empty.")
            wait_for_enter()
            return
        
        install_file = Path(json_path)
        if not install_file.is_absolute():
            if (DEPLOYMENT_UTILS_DIR / json_path).exists():
                install_file = DEPLOYMENT_UTILS_DIR / json_path
            else:
                install_file = SCRIPTS_DIR / json_path
    else:
        install_file = default_installations[choice]['file']
    
    if not install_file.exists():
        print(f"{Emoji.ERROR.value} File not found: {install_file}")
        wait_for_enter()
        return
    
    # Load installation steps
    steps = load_installation_steps(install_file)
    
    if not steps:
        print(f"{Emoji.WARNING.value} No installation steps found in file.")
        wait_for_enter()
        return
    
    # Execute steps with interactive controls
    execute_installation_steps(
        steps, 
        interactive=True,
        get_yes_no_fn=get_yes_no,
        get_user_choice_fn=get_user_choice,
        print_separator_fn=print_separator
    )
    
    wait_for_enter()

# --- Main Menu ---

def main_menu():
    """Display main menu and handle user choice."""
    options = [
        {"id": "1", "name": "List All Deployments (Dashboard)"},
        {"id": "2", "name": "Show Services Status"},
        {"id": "3", "name": "Clone & Deploy New Repository"},
        {"id": "4", "name": "Batch Operations"},
        {"id": "5", "name": "Manage Deployment (Start/Stop/Restart/Redeploy)"},
        {"id": "6", "name": "Installation Manager"},
        {"id": "7", "name": "Manage Credentials (Tokens)"},
        {"id": "0", "name": "Exit"}
    ]
    
    while True:
        choice = display_menu(f"{Emoji.DOCKER.value} Deployment Manager CLI", options)
        
        if choice == '0':
            print(f"\n{Emoji.SUCCESS.value} Goodbye!")
            sys.exit(0)
        elif choice == '1':
            list_deployments()
        elif choice == '2':
            show_services_status()
        elif choice == '3':
            clone_and_deploy()
        elif choice == '4':
            batch_operations_menu()
        elif choice == '5':
            deployment_operations()
        elif choice == '6':
            manage_installations()
        elif choice == '7':
            manage_credentials()


def manage_credentials():
    """Menu to manage Git tokens and credentials."""
    while True:
        creds = get_credentials()
        options = [
            {"id": "1", "name": "List Saved Credentials"},
            {"id": "2", "name": "Add New PAT Token"},
            {"id": "3", "name": "Delete Credential"},
            {"id": "0", "name": "Back to Main Menu"}
        ]
        
        choice = display_menu(f"{Emoji.KEY.value} Credentials Manager", options)
        
        if choice == '0':
            break
        elif choice == '1':
            print_header("Saved Credentials")
            if not creds:
                print("No credentials stored.")
            for c in creds:
                print(f"  - {c.get('alias')} ({c.get('type')}) [ID: {c.get('id')}]")
            wait_for_enter()
        elif choice == '2':
            add_credential_flow()
        elif choice == '3':
            if not creds:
                print("Nothing to delete.")
                wait_for_enter()
                continue
            
            del_options = [{"id": str(i+1), "name": c.get('alias')} for i, c in enumerate(creds)]
            del_options.append({"id": "0", "name": "Cancel"})
            del_choice = display_menu("Delete which credential?", del_options)
            
            if del_choice != "0":
                idx = int(del_choice) - 1
                creds.pop(idx)
                write_json(CREDENTIALS_FILE, creds)
                print(f"{Emoji.SUCCESS.value} Deleted.")
                wait_for_enter()

def add_credential_flow():
    """Interactive flow to add a new token."""
    print_header("Add New Credential")
    alias = input("Enter alias (e.g., 'Work GitHub'): ").strip()
    token = input("Enter Personal Access Token: ").strip()
    
    if not alias or not token:
        print(f"{Emoji.ERROR.value} Alias and Token are required.")
        wait_for_enter()
        return
    
    import uuid
    new_cred = {
        "id": str(uuid.uuid4())[:8],
        "alias": alias,
        "token": token,
        "type": "pat"
    }
    
    creds = get_credentials()
    creds.append(new_cred)
    write_json(CREDENTIALS_FILE, creds)
    print(f"\n{Emoji.SUCCESS.value} Credential saved successfully!")
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
