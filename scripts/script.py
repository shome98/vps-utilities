import json
import subprocess
import sys
from pathlib import Path
import shutil
import os
from enum import Enum
from commands import Command

# --- Path Configuration ---
SCRIPTS_DIR = Path(__file__).resolve().parent
VPS_UTILS_DIR = SCRIPTS_DIR.parent
DEPLOYMENT_UTILS_DIR = VPS_UTILS_DIR.parent
APPS_DIR = DEPLOYMENT_UTILS_DIR.parent
CREDENTIALS_FILE = DEPLOYMENT_UTILS_DIR / 'credentials.json'

# --- Emoji Definitions ---

class Emoji(Enum):
    """Emoji constants for consistent messaging throughout the script."""
    # Status indicators
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    
    # Process indicators
    START = "🚀"
    STOP = "🛑"
    RESTART = "🔄"
    BUILD = "🔨"
    DEPLOY = "📦"
    REBUILD = "🔧"
    
    # Git operations
    CLONE = "📥"
    PULL = "⬇️"
    CHECKOUT = "🔀"
    BRANCH = "🌿"
    
    # Docker operations
    DOCKER = "🐳"
    CONTAINER = "📦"
    IMAGE = "🖼️"
    START_CONTAINER = "▶️"
    STOP_CONTAINER = "⏹️"
    DELETE_CONTAINER = "🗑️"
    BATCH = "📋"
    
    # File operations
    FILE = "📄"
    COPY = "📋"
    SAVE = "💾"
    FOLDER = "📁"
    
    # Checkmarks and indicators
    CHECK = "✓"
    ARROW = "➡️"
    
    # Other
    GEAR = "⚙️"
    TOOLS = "🛠️"
    LINK = "🔗"
    KEY = "🔑"
    QUESTION = "❓"

# --- Utilities ---


def read_json(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def execute(desc, cmd, cwd=None, capture=False, env=None):
    if not capture:
        # Redact potential tokens from printed description or command
        display_cmd = cmd
        if "ghp_" in cmd or "@github.com" in cmd:
            import re
            display_cmd = re.sub(r'https://[^@]+@', 'https://***@', cmd)
        print(f"{Emoji.GEAR.value} {desc}")
        if display_cmd != cmd:
            # We don't print the actual raw command if it has secrets
            pass 
            
    try:
        # Merge provided env with current process environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
            
        if capture:
            return subprocess.check_output(cmd, shell=True, cwd=cwd, text=True, env=full_env).strip()
        subprocess.check_call(cmd, shell=True, cwd=cwd, env=full_env)
    except subprocess.CalledProcessError as e:
        if capture:
            return ""
        # Improved error reporting for git/docker failures
        error_msg = f"Error during: {desc}. Command: {cmd}"
        if e.output:
            error_msg += f"\nDetails: {e.output}"
        raise RuntimeError(error_msg)

# --- Docker Utilities ---


def stop_service(container_id, container_name=None):
    """Stops a Docker container by ID or name. Prefers ID if provided."""
    target = container_id if container_id else container_name
    identifier = container_name if container_name else (
        container_id[:12] if container_id else "unknown")
    execute(f"{Emoji.STOP_CONTAINER.value} Stopping container: {identifier}", 
            Command.DOCKER_STOP.value.format(target=target))

def delete_service(container_id, container_name=None):
    """Deletes a Docker container by ID or name. Prefers ID if provided."""
    target = container_id if container_id else container_name
    identifier = container_name if container_name else (
        container_id[:12] if container_id else "unknown")
    execute(f"{Emoji.DELETE_CONTAINER.value} Deleting container: {identifier}", 
            Command.DOCKER_RM.value.format(target=target))

def restart_service(container_id, container_name=None):
    """Restarts a Docker container by ID or name. Prefers ID if provided."""
    target = container_id if container_id else container_name
    identifier = container_name if container_name else (
        container_id[:12] if container_id else "unknown")
    execute(f"{Emoji.RESTART.value} Restarting container: {identifier}", 
            Command.DOCKER_RESTART.value.format(target=target))


def remove_image(image_id, image_name=None, force=False):
    """Removes a Docker image by ID or name. Prefers ID if provided."""
    # Extract just the hash part, removing 'sha256:' prefix and any quotes
    target = clean_image_id(image_id) if image_id else image_name
    
    identifier = image_name if image_name else (target[:12] if target else "unknown")
    flag = "-f" if force else ""
    execute(f"{Emoji.IMAGE.value} Removing image: {identifier}", 
            Command.DOCKER_RMI.value.format(flags=flag, target=target))

def clean_image_id(image_id):
    """Cleans image ID by removing 'sha256:' prefix and quotes."""
    if not image_id:
        return image_id
    clean_id = image_id.replace("'", "").replace('"', "")  # Remove quotes
    if clean_id.startswith("sha256:"):
        return clean_id.replace("sha256:", "", 1)
    return clean_id

def load_env_file(env_file_path):
    """Loads environment variables from a .env file."""
    env_vars = {}
    if not env_file_path or not Path(env_file_path).exists():
        return env_vars
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

def resolve_env_file_path(env_file):
    """Resolves env file path relative to deployment-utilities or scripts directory."""
    if not env_file:
        return None
    
    env_path = Path(env_file)
    if not env_path.is_absolute():
        # Check deployment-utilities first
        if (DEPLOYMENT_UTILS_DIR / env_file).exists():
            env_path = DEPLOYMENT_UTILS_DIR / env_file
        # Then check scripts dir
        elif (SCRIPTS_DIR / env_file).exists():
            env_path = SCRIPTS_DIR / env_file
        else:
            # Fallback to scripts dir path even if not exists
            env_path = SCRIPTS_DIR / env_file
    
    return env_path

def copy_env_file_to_repo(env_file, repo_path):
    """Copies env file from scripts directory to repository directory."""
    if not env_file:
        return None
    
    env_path = resolve_env_file_path(env_file)
    
    if env_path and env_path.exists():
        dest_env = repo_path / ".env"
        shutil.copy2(str(env_path), str(dest_env))
        print(f"  {Emoji.COPY.value} Copied env file to {dest_env}")
        return str(dest_env)
    
    return None

def load_and_apply_env_file(env_file):
    """Loads env file and returns environment variables dict."""
    if not env_file:
        return {}
    
    env_path = resolve_env_file_path(env_file)
    
    if env_path and env_path.exists():
        env_vars = load_env_file(str(env_path))
        if env_vars:
            print(f"  {Emoji.KEY.value} Loaded {len(env_vars)} environment variables from {env_path}")
        return env_vars
    
    return {}

def resolve_docker_compose_file(repo_path, mode='dev'):
    """Resolves the appropriate docker-compose file based on mode with fallback logic.
    
    Priority for each mode:
    - prod: docker-compose.prod.yml -> docker-compose.prod.yaml -> docker-compose.yml -> docker-compose.yaml
    - dev: docker-compose.dev.yml -> docker-compose.dev.yaml -> docker-compose.yml -> docker-compose.yaml
    - qa: docker-compose.qa.yml -> docker-compose.qa.yaml -> docker-compose.yml -> docker-compose.yaml
    
    Returns:
        tuple: (file_name, file_path) or (None, None) if no file found
    """
    # Define file priority based on mode
    if mode == 'prod':
        file_candidates = [
            'docker-compose.prod.yml',
            'docker-compose.prod.yaml',
            'docker-compose.yml',
            'docker-compose.yaml'
        ]
    elif mode == 'qa':
        file_candidates = [
            'docker-compose.qa.yml',
            'docker-compose.qa.yaml',
            'docker-compose.yml',
            'docker-compose.yaml'
        ]
    else:  # dev or default
        file_candidates = [
            'docker-compose.dev.yml',
            'docker-compose.dev.yaml',
            'docker-compose.yml',
            'docker-compose.yaml'
        ]
    
    # Check each candidate file
    for file_name in file_candidates:
        file_path = repo_path / file_name
        if file_path.exists():
            return file_name, file_path
    
    # No file found
    return None, None

def docker_build(repo_path, repo_name, mode='dev', no_cache=False, env_file=None):
    """Builds Docker images using docker compose."""
    file_name, file_path = resolve_docker_compose_file(repo_path, mode)
    
    if not file_name:
        print(f"  {Emoji.WARNING.value} Skipping Docker build: No docker-compose file found for {mode} mode.")
        return False
    
    cache_flag = "--no-cache" if no_cache else ""
    cmd = Command.DOCKER_COMPOSE_BUILD.value.format(file=file_name, flags=cache_flag).strip()
    
    # Load and set environment variables from env_file
    env_vars = load_and_apply_env_file(env_file)
    
    execute(f"{Emoji.BUILD.value} Building {repo_name} ({mode})", cmd, cwd=repo_path, env=env_vars)
    return True

def docker_start(repo_path, repo_name, mode='dev', env_file=None):
    """Starts Docker containers using docker compose."""
    file_name, file_path = resolve_docker_compose_file(repo_path, mode)
    
    if not file_name:
        print(f"  {Emoji.WARNING.value} Skipping Docker start: No docker-compose file found for {mode} mode.")
        return False
    
    # Copy env file to repo directory and load variables
    dest_env = copy_env_file_to_repo(env_file, repo_path)
    env_vars = {}
    
    if dest_env:
        env_vars = load_env_file(dest_env)
        if env_vars:
            print(f"  {Emoji.KEY.value} Loaded {len(env_vars)} environment variables")
    
    cmd = Command.DOCKER_COMPOSE_UP.value.format(file=file_name)
    execute(f"{Emoji.START_CONTAINER.value} Starting {repo_name} ({mode})", cmd, cwd=repo_path, env=env_vars)
    return True

# let's change it a bit so on change first stop the corresponding docker containers and then remove the old image then rebuild and update it in the json as well again
# start it again as well, so it's ready to use right away


def docker_rebuild_image(repo_path, repo_name, mode='dev', env_file=None):
    """Rebuilds Docker image with proper container lifecycle management: stop -> remove old image -> rebuild -> start."""
    file_name, file_path = resolve_docker_compose_file(repo_path, mode)

    if not file_name:
        print(f"  {Emoji.WARNING.value} Skipping Docker rebuild: No docker-compose file found for {mode} mode.")
        return False

    print(f"\n{Emoji.REBUILD.value} Rebuilding Docker image for {repo_name} ({mode} mode)")

    # Step 1: Get current image info before stopping containers
    print(f"  {Emoji.INFO.value} [1/5] Capturing current deployment details...")
    old_image_info, old_services, _ = get_deployment_details(repo_path)
    old_image_id = old_image_info.get('id', '') if old_image_info else ''

    # Step 2: Stop running containers
    if old_services:
        print(f"  {Emoji.STOP.value} [2/5] Stopping {len(old_services)} container(s)...")
        for service in old_services:
            container_id = service.get('id')
            container_name = service.get('name')
            if container_id or container_name:
                stop_service(container_id, container_name)
                delete_service(container_id, container_name)
    else:
        print(f"  {Emoji.INFO.value} [2/5] No running containers to stop.")

    # Step 3: Remove old image if it exists
    if old_image_id:
        old_image_name = old_image_info.get('name')
        print(f"  {Emoji.IMAGE.value} [3/5] Removing old image...")
        try:
            remove_image(old_image_id, old_image_name, force=True)
        except SystemExit:
            print(
                f"  {Emoji.WARNING.value} Could not remove old image (may be in use by other containers). Continuing...")
    else:
        print(f"  {Emoji.INFO.value} [3/5] No old image to remove.")

    # Step 4: Rebuild and start containers
    print(f"  {Emoji.BUILD.value} [4/5] Building new image and starting containers...")
    docker_build(repo_path, repo_name, mode, env_file=env_file)
    docker_start(repo_path, repo_name, mode, env_file=env_file)

    # Step 5: Update tracking with new image info and services
    print(f"  {Emoji.SAVE.value} [5/5] Updating deployment tracking...")
    image_info, services, port = get_deployment_details(repo_path)
    update_repo_tracking(repo_name, image_info=image_info, services=services, port=port)

    print(f"  {Emoji.SUCCESS.value} Successfully rebuilt and deployed {repo_name}")
    if image_info:
        print(f"      New image: {image_info.get('name', 'N/A')}")
    print(f"      Running services: {len(services)}")

    return True


# --- Installation Utilities ---

def load_installation_steps(json_path):
    """Load installation steps from a JSON file."""
    path = Path(json_path)
    if not path.exists():
        print(f"{Emoji.ERROR.value} Installation file not found: {path}")
        return []
    
    data = read_json(path)
    
    # Support both formats: {installation_steps: [...]} or [...]
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get('installation_steps', [])
    
    return []

def execute_installation_steps(steps, interactive=True, skip_prompt=False, get_yes_no_fn=None, get_user_choice_fn=None, print_separator_fn=None):
    """Execute installation steps with optional interactive controls.
    
    Args:
        steps: List of step objects with 'desc' and 'cmd'
        interactive: If True, show choices (execute all, one-by-one, skip)
        skip_prompt: If True and interactive, skip confirmation for each step
        get_yes_no_fn: Function for yes/no prompts (from cli_application)
        get_user_choice_fn: Function for user choice (from cli_application)
        print_separator_fn: Function for printing separator (from cli_application)
    """
    if not steps:
        print(f"{Emoji.WARNING.value} No installation steps to execute.")
        return False
    
    # Show all steps first
    print(f"\n{Emoji.INFO.value} Installation Steps ({len(steps)}):\n")
    for idx, step in enumerate(steps, 1):
        desc = step.get('desc', 'No description')
        cmd = step.get('cmd', '')
        print(f"  {idx}. {desc}")
        print(f"     Command: {cmd}")
        print()
    
    # Use provided functions or simple input fallback
    if get_yes_no_fn is None:
        def get_yes_no_fn(prompt):
            return input(f"{prompt} (y/n): ").strip().lower() in ['y', 'yes']
    
    if get_user_choice_fn is None:
        def get_user_choice_fn(prompt, choices):
            while True:
                choice = input(prompt).strip().lower()
                if choice in choices:
                    return choice
                print(f"{Emoji.WARNING.value} Invalid choice.")
    
    if print_separator_fn is None:
        def print_separator_fn():
            print(f"\n{'-'*60}")
    
    if not interactive:
        # Execute all automatically
        if not get_yes_no_fn(f"{Emoji.INFO.value} Execute all {len(steps)} steps?"):
            return False
        
        for idx, step in enumerate(steps, 1):
            print(f"\n{Emoji.GEAR.value} [{idx}/{len(steps)}] {step.get('desc')}")
            try:
                execute(step.get('desc'), step.get('cmd'))
            except SystemExit as e:
                print(f"{Emoji.ERROR.value} Step {idx} failed: {e}")
                if not get_yes_no_fn("Continue with remaining steps?"):
                    return False
        return True
    
    # Interactive mode - show execution choices
    modes = [
        {"id": "1", "name": "Execute All Steps"},
        {"id": "2", "name": "Execute Step-by-Step (with control)"},
        {"id": "3", "name": "Cancel"}
    ]
    
    print(f"\n{Emoji.TOOLS.value} Execution Mode:")
    for mode in modes:
        print(f"  {mode['id']}. {mode['name']}")
    
    valid_ids = [m["id"] for m in modes]
    choice = get_user_choice_fn(f"\n{Emoji.ARROW.value} Select mode ({valid_ids[0]}-{valid_ids[-1]}): ", valid_ids)
    
    if choice == '3':
        print(f"{Emoji.INFO.value} Installation cancelled.")
        return False
    
    if choice == '1':
        # Execute all
        for idx, step in enumerate(steps, 1):
            print(f"\n{Emoji.GEAR.value} [{idx}/{len(steps)}] {step.get('desc')}")
            try:
                execute(step.get('desc'), step.get('cmd'))
            except SystemExit as e:
                print(f"{Emoji.ERROR.value} Step {idx} failed: {e}")
                if not get_yes_no_fn("Continue with remaining steps?"):
                    return False
        return True
    
    # Step-by-step mode
    success_count = 0
    skipped_count = 0
    
    for idx, step in enumerate(steps, 1):
        print(f"\n{'-'*60}")
        print(f"{Emoji.GEAR.value} Step {idx}/{len(steps)}: {step.get('desc')}")
        print(f"Command: {step.get('cmd')}")
        
        if not skip_prompt:
            action = get_user_choice_fn(f"\n{Emoji.ARROW.value} Action (execute/skip/quit): ", 
                                   ['execute', 'skip', 'quit', 'e', 's', 'q'])
            
            if action in ['quit', 'q']:
                print(f"{Emoji.INFO.value} Installation stopped by user.")
                break
            elif action in ['skip', 's']:
                print(f"{Emoji.WARNING.value} Step {idx} skipped.")
                skipped_count += 1
                continue
        
        # Execute step
        try:
            execute(step.get('desc'), step.get('cmd'))
            success_count += 1
            print(f"{Emoji.SUCCESS.value} Step {idx} completed!")
        except SystemExit as e:
            print(f"{Emoji.ERROR.value} Step {idx} failed: {e}")
            if not get_yes_no_fn("Continue with next step?"):
                break
    
    print_separator_fn()
    print(f"\n{Emoji.INFO.value} Installation Summary:")
    print(f"  {Emoji.SUCCESS.value} Executed: {success_count}")
    print(f"  {Emoji.WARNING.value} Skipped: {skipped_count}")
    print(f"  {Emoji.ERROR.value} Failed: {len(steps) - success_count - skipped_count}")
    
    return success_count > 0


# --- Container Status Utilities ---

def get_all_containers_status():
    """Get status of all containers from docker ps."""
    try:
        output = execute("", Command.DOCKER_PS_FORMATTED.value, 
                        capture=True)
        containers = []
        for line in output.splitlines():
            parts = line.split('|')
            if len(parts) >= 4:
                containers.append({
                    'id': parts[0],
                    'name': parts[1],
                    'status': parts[2],
                    'image': parts[3]
                })
        return containers
    except:
        return []


def validate_batch_json(data):
    """Validate batch deployment JSON structure."""
    if not isinstance(data, list):
        return False, "JSON must be an array"
    
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"Item {idx+1} must be an object"
        if 'githubUrl' not in item:
            return False, f"Item {idx+1} missing 'githubUrl'"
    
    return True, "Valid"


def has_git_changes(repo_path):
    """Checks if there are uncommitted changes or if the repository was recently updated."""
    try:
        # Check for uncommitted changes (modified, added, deleted files)
        status = execute("", Command.GIT_STATUS_PORCELAIN.value,
                         cwd=repo_path, capture=True)
        if status:
            return True

        # Check if there are any commits that differ from the last known state
        # Using git log to see if there are recent commits (last 24 hours)
        recent_commits = execute(
            "", Command.GIT_LOG_RECENT.value, cwd=repo_path, capture=True)
        if recent_commits:
            return True

        return False
    except Exception:
        # If any check fails, assume changes exist to be safe
        return True

# --- Authentication Utilities ---

def resolve_authenticated_url(url, token=None):
    """Injects token into https URLs for private repository access."""
    if not token or "git@" in url or "@github.com" in url:
        return url
    
    if "https://" in url:
        return url.replace("https://", f"https://{token}@")
    
    # Handle cases like github.com/user/repo
    return f"https://{token}@{url}"

def get_credentials():
    """Load credentials from JSON file."""
    return read_json(CREDENTIALS_FILE)

def get_token_by_id(cred_id):
    """Retrieve a specific token from credentials store."""
    if not cred_id:
        return None
    creds = get_credentials()
    for c in creds:
        if c.get('id') == cred_id or c.get('alias') == cred_id:
            return c.get('token')
    return None

# --- Git Utilities ---


def pull_latest(repo_path, branch, token=None):
    """Pulls latest changes and fails if merge conflicts occur."""
    print(f"{Emoji.PULL.value} Pulling latest changes for branch: {branch}")
    
    # If a token is provided, we need to ensure the remote uses it
    # However, git usually remembers the authenticated URL from clone.
    # If not, we might need: git remote set-url origin <auth_url>
    
    try:
        # fetch and pull
        subprocess.check_call(Command.GIT_FETCH.value, shell=True, cwd=repo_path)
        # We use --no-rebase to ensure a standard pull; check for success
        subprocess.check_call(
            Command.GIT_PULL.value.format(branch=branch), shell=True, cwd=repo_path)
    except subprocess.CalledProcessError:
        raise RuntimeError(f"GIT PULL FAILED: Merge conflict or network error in {repo_path}")


def git_clone(url, repo_name, parent_dir, token=None):
    """Clones a repository from the given URL to the specified parent directory."""
    auth_url = resolve_authenticated_url(url, token)
    execute(f"{Emoji.CLONE.value} Cloning {repo_name}",
            Command.GIT_CLONE.value.format(url=auth_url, name=repo_name), cwd=parent_dir)
    return parent_dir / repo_name


def git_checkout(repo_path, branch):
    """Checks out to the specified branch in the given repository path."""
    execute(f"{Emoji.CHECKOUT.value} Checking out {Emoji.BRANCH.value} {branch} in {repo_path.name}",
            Command.GIT_CHECKOUT.value.format(branch=branch), cwd=repo_path)

# --- Core Logic ---


def update_repo_tracking(repo_name, repo_path=None, github_url=None, branch=None, env_path=None, mode=None, image_info=None, services=None, port=None, reverse_proxy=None, tracking_file=None):
    if tracking_file is None:
        tracking_file = DEPLOYMENT_UTILS_DIR / 'deployed_repos.json'
    
    data = read_json(tracking_file)
    entry = next((item for item in data if item.get(
        'folder_name') == repo_name), None)

    if not entry:
        entry = {"folder_name": repo_name}
        data.append(entry)

    if repo_path:
        entry['folderPath'] = str(repo_path)
    if github_url:
        entry['githubUrl'] = github_url
    if branch:
        entry['checkoutBranch'] = branch
    if env_path:
        entry['envPath'] = env_path
    if mode:
        entry['deployMode'] = mode

    if image_info:
        entry['image'] = image_info
    if services is not None:
        entry['services'] = services
    if port is not None:
        entry['port'] = port
    if reverse_proxy is not None:
        entry['reverse_proxy'] = reverse_proxy

    write_json(tracking_file, data)


def get_deployment_details(repo_path):
    cmd = Command.DOCKER_COMPOSE_PS.value
    output = execute("", cmd, cwd=repo_path, capture=True)

    services = []
    primary_image = {}
    main_port = None

    if output:
        # Docker compose ps can return a list of objects or one per line
        data = []
        try:
            # Try to parse as a single JSON array first
            parsed_output = json.loads(output)
            data = parsed_output if isinstance(parsed_output, list) else [parsed_output]
        except json.JSONDecodeError:
            # Fallback to line by line
            for line in output.splitlines():
                try:
                    if line.strip():
                        data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        for s in data:
            try:
                container_id = s.get("ID")
                service_name = s.get("Service")
                
                # Get ports from Publishers
                ports = []
                publishers = s.get("Publishers") or []
                for pub in publishers:
                    if pub.get("PublishedPort"):
                        ports.append(str(pub.get("PublishedPort")))
                
                if ports and main_port is None:
                    main_port = ports[0]

                if not primary_image:
                    img_id_cmd = Command.DOCKER_INSPECT_IMAGE.value.format(target=container_id)
                    image_id = execute("", img_id_cmd, capture=True)
                    # Clean the image ID by removing sha256: prefix and quotes
                    cleaned_image_id = clean_image_id(image_id)
                    primary_image = {"name": s.get("Image"), "id": cleaned_image_id}

                service_entry = {"name": service_name, "id": container_id}
                if ports:
                    service_entry["port"] = ", ".join(ports)
                services.append(service_entry)
            except Exception:
                continue
                
    return primary_image, services, main_port


def clone_and_checkout(repo_data, mode='dev'):
    url = repo_data['githubUrl']
    branch = repo_data.get('checkoutBranch', 'main')
    env_path = repo_data.get('envPath')  # Optional env file path
    repo_name = url.split('/')[-1].replace('.git', '')

    parent_dir = APPS_DIR
    repo_path = parent_dir / repo_name

    is_new_clone = False
    has_changes = False
    commit_before = ""

    if not repo_path.exists():
        token = get_token_by_id(repo_data.get('credentialId'))
        repo_path = git_clone(url, repo_name, parent_dir, token=token)
        is_new_clone = True
        has_changes = True  # New clone always needs build
    else:
        # If it exists, get commit hash before pull
        try:
            commit_before = execute(
                "", Command.GIT_REV_PARSE.value, cwd=repo_path, capture=True)
        except:
            commit_before = ""

    # Pull latest changes
    token = get_token_by_id(repo_data.get('credentialId'))
    pull_latest(repo_path, branch, token=token)

    # Get commit hash after pull
    try:
        commit_after = execute(
            "", Command.GIT_REV_PARSE.value, cwd=repo_path, capture=True)
    except:
        commit_after = ""
    
    # Check if commit changed or if there are uncommitted changes
    has_changes = (commit_before != commit_after) or has_git_changes(repo_path)

    # Save the basic info including URL, Branch, envPath, and mode
    update_repo_tracking(repo_name, repo_path=repo_path,
                         github_url=url, branch=branch, env_path=env_path, mode=mode)

    git_checkout(repo_path, branch)

    # Check if we need to rebuild Docker image
    # For new clones or if there are changes, rebuild the image
    if not is_new_clone and has_changes:
        print(
            f"  {Emoji.INFO.value} Changes detected in {repo_name}, rebuilding Docker image...")
        docker_rebuild_image(repo_path, repo_name, mode, env_file=env_path)

    return repo_path, repo_name, has_changes, is_new_clone, env_path


def deploy_docker(repo_path, repo_name, mode='dev', env_file=None):
    file_name, file_path = resolve_docker_compose_file(repo_path, mode)

    if not file_name:
        print(f"  {Emoji.WARNING.value} Skipping Docker: No docker-compose file found for {mode} mode.")
        return

    # Build and start using utility methods
    docker_build(repo_path, repo_name, mode, env_file=env_file)
    docker_start(repo_path, repo_name, mode, env_file=env_file)

    image_info, services, port = get_deployment_details(repo_path)
    update_repo_tracking(repo_name, image_info=image_info, services=services, mode=mode, port=port)


def ensure_nginx_rate_limit_zones():
    """Ensures that Nginx rate limit zones are defined in conf.d."""
    limits_content = """limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=frontend_limit:10m rate=20r/s;
"""
    try:
        execute("Initializing Nginx rate limit zones", 
                Command.NGINX_CREATE_LIMITS.value.format(content=limits_content))
        execute("Testing Nginx configuration", Command.NGINX_TEST.value)
        execute("Reloading Nginx", Command.NGINX_RELOAD.value)
    except Exception as e:
        print(f"{Emoji.WARNING.value} Could not initialize rate limit zones: {e}")

def generate_nginx_config(domain, subdomain, port, options=None):
    """Generates an extensive Nginx reverse proxy configuration block."""
    if options is None:
        options = {}
    
    server_name = f"{subdomain}.{domain}" if subdomain else domain
    service_type = options.get('type', 'api')  # 'api' or 'frontend'
    rate_limit = options.get('rate_limit', {'enabled': True, 'burst': 50, 'excluded_paths': []})
    cors = options.get('cors', {'enabled': service_type == 'api', 'origins': ['*']})
    
    # Upstream definition
    upstream_name = f"{server_name.replace('.', '_')}_upstream"
    
    config = f"upstream {upstream_name} {{\n"
    config += f"    server 127.0.0.1:{port};\n"
    config += f"    keepalive 32;\n"
    config += "}\n\n"
    
    config += f"server {{\n"
    config += f"    listen 80;\n"
    config += f"    server_name {server_name};\n\n"
    
    # Security headers
    config += "    # Security headers\n"
    config += "    add_header X-Frame-Options \"SAMEORIGIN\" always;\n"
    config += "    add_header X-Content-Type-Options \"nosniff\" always;\n"
    config += "    add_header X-XSS-Protection \"1; mode=block\" always;\n"
    config += "    add_header Referrer-Policy \"strict-origin-when-cross-origin\" always;\n\n"
    
    # Excluded paths from rate limiting (Webhooks)
    for path in rate_limit.get('excluded_paths', []):
        config += f"    # No rate limiting for {path}\n"
        config += f"    location {path} {{\n"
        config += f"        proxy_pass http://{upstream_name};\n"
        config += "        proxy_http_version 1.1;\n"
        config += "        proxy_set_header Host $host;\n"
        config += "        proxy_set_header X-Real-IP $remote_addr;\n"
        config += "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        config += "        proxy_set_header X-Forwarded-Proto $scheme;\n"
        
        if cors.get('enabled'):
            origins = ", ".join(cors.get('origins', ['*']))
            config += f"        add_header Access-Control-Allow-Origin \"{origins}\" always;\n"
            config += "        add_header Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, OPTIONS' always;\n"
            config += "        add_header Access-Control-Allow-Headers 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;\n"
        config += "    }\n\n"

    # Main location
    config += "    location / {\n"
    config += f"        proxy_pass http://{upstream_name};\n"
    config += "        proxy_http_version 1.1;\n"
    config += "        proxy_set_header Host $host;\n"
    config += "        proxy_set_header X-Real-IP $remote_addr;\n"
    config += "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
    config += "        proxy_set_header X-Forwarded-Proto $scheme;\n"
    config += "        proxy_set_header Upgrade $http_upgrade;\n"
    config += "        proxy_set_header Connection \"upgrade\";\n\n"
    
    # Rate limiting
    if rate_limit.get('enabled'):
        zone = "api_limit" if service_type == 'api' else "frontend_limit"
        burst = rate_limit.get('burst', 50 if service_type == 'api' else 20)
        config += f"        # Rate limiting\n"
        config += f"        limit_req zone={zone} burst={burst} nodelay;\n\n"
    
    # CORS
    if cors.get('enabled'):
        origins = ", ".join(cors.get('origins', ['*']))
        config += "        # CORS headers\n"
        config += f"        add_header Access-Control-Allow-Origin \"{origins}\" always;\n"
        config += "        add_header Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, OPTIONS' always;\n"
        config += "        add_header Access-Control-Allow-Headers 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;\n"
        config += "        add_header Access-Control-Expose-Headers 'Content-Length,Content-Range' always;\n"
        config += "        add_header Access-Control-Allow-Credentials 'true' always;\n\n"
        
        config += "        # Handle preflight requests\n"
        config += "        if ($request_method = 'OPTIONS') {\n"
        config += f"            add_header Access-Control-Allow-Origin \"{origins}\";\n"
        config += "            add_header Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, OPTIONS';\n"
        config += "            add_header Access-Control-Allow-Headers 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';\n"
        config += "            add_header Access-Control-Allow-Credentials 'true';\n"
        config += "            add_header Access-Control-Max-Age 1728000;\n"
        config += "            add_header Content-Type 'text/plain; charset=utf-8';\n"
        config += "            add_header Content-Length 0;\n"
        config += "            return 204;\n"
        config += "        }\n"
    
    # Static caching for Frontend
    if service_type == 'frontend':
        config += "        # Caching for static assets\n"
        config += "        location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {\n"
        config += f"            proxy_pass http://{upstream_name};\n"
        config += "            expires 30d;\n"
        config += "            add_header Cache-Control \"public, immutable\";\n"
        config += "        }\n"
    
    config += "    }\n\n"
    
    # Health check
    config += "    # Health check\n"
    config += "    location /health {\n"
    config += f"        proxy_pass http://{upstream_name};\n"
    config += "        proxy_http_version 1.1;\n"
    config += "        proxy_set_header Host $host;\n"
    config += "        access_log off;\n"
    config += "    }\n"
    
    config += "}\n"
    return config


def setup_nginx_proxy(repo_name, domain, subdomain, port, email=None, run_ssl=False, options=None):
    """Sets up Nginx reverse proxy and optionally SSL via Certbot."""
    if options is None:
        options = {}
        
    server_name = f"{subdomain}.{domain}" if subdomain else domain
    
    # Ensure rate limit zones are initialized
    ensure_nginx_rate_limit_zones()
    
    config = generate_nginx_config(domain, subdomain, port, options)
    
    # Path setup
    available_path = f"/etc/nginx/sites-available/{server_name}.conf"
    enabled_path = f"/etc/nginx/sites-enabled/{server_name}.conf"
    
    # Use a temporary file to write config
    temp_conf = Path(f"/tmp/{server_name}.conf")
    try:
        # Write config locally first
        with open(temp_conf, "w") as f:
            f.write(config)
            
        # Move to sites-available using sudo
        execute(f"{Emoji.GEAR.value} Moving config to sites-available", f"sudo mv {temp_conf} {available_path}")
        
        # Symlink to sites-enabled
        execute(f"{Emoji.LINK.value} Enabling Nginx site", f"sudo ln -sf {available_path} {enabled_path}")
        
        # Test config
        execute(f"{Emoji.GEAR.value} Testing Nginx configuration", Command.NGINX_TEST.value)
        
        # Reload Nginx
        execute(f"{Emoji.RESTART.value} Reloading Nginx", Command.NGINX_RELOAD.value)
        
        ssl_enabled = False
        if run_ssl and email:
            print(f"{Emoji.GEAR.value} Running Certbot for {server_name}...")
            execute(f"Issuing SSL certificate", 
                   Command.CERTBOT_NGINX.value.format(domain=server_name, email=email))
            ssl_enabled = True
            
        # Update tracking
        proxy_info = {
            "domain": domain,
            "subdomain": subdomain,
            "port": port,
            "ssl_enabled": ssl_enabled,
            "email": email,
            "server_name": server_name,
            "type": options.get('type', 'api'),
            "rate_limit": options.get('rate_limit', {}),
            "cors": options.get('cors', {})
        }
        update_repo_tracking(repo_name, reverse_proxy=proxy_info)
        
        print(f"{Emoji.SUCCESS.value} Nginx proxy setup completed for {server_name}")
        return True
    except Exception as e:
        if temp_conf.exists():
            temp_conf.unlink()
        raise RuntimeError(f"Nginx setup failed: {e}")


def remove_nginx_proxy(repo_name, server_name):
    """Removes Nginx proxy configuration for a deployment."""
    available_path = f"/etc/nginx/sites-available/{server_name}.conf"
    enabled_path = f"/etc/nginx/sites-enabled/{server_name}.conf"
    
    print(f"{Emoji.STOP.value} Removing Nginx configuration for {server_name}...")
    
    try:
        execute(f"Removing enabled link", Command.NGINX_RM_CONF.value.format(path=enabled_path))
        execute(f"Removing available config", Command.NGINX_RM_CONF.value.format(path=available_path))
        
        # Reload Nginx
        execute("Reloading Nginx", Command.NGINX_RELOAD.value)
        
        # Update tracking
        update_repo_tracking(repo_name, reverse_proxy={})
        return True
    except Exception as e:
        print(f"{Emoji.WARNING.value} Error removing Nginx config: {e}")
        return False


def run_all(config_file, mode='dev'):
    data = read_json(config_file)
    for repo in data.get('repositories', []):
        # clone_and_checkout now handles Docker rebuild automatically when changes are detected
        repo_path, repo_name, has_changes, is_new_clone, env_path = clone_and_checkout(
            repo, mode=mode)

        # Only deploy if not already handled by clone_and_checkout
        # (i.e., for new clones that need initial deployment)
        if is_new_clone:
            deploy_docker(repo_path, repo_name, mode=mode, env_file=env_path)

    for step in data.get('installation_steps', []):
        execute(step['desc'], step['cmd'])

    print(f"\n{Emoji.SUCCESS.value} All tasks completed successfully in {mode} mode!")


# if __name__ == "__main__":
#     pass
