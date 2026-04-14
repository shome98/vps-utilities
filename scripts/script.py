import json
import subprocess
import sys
from pathlib import Path
import shutil
import os
from enum import Enum

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

# --- Utilities ---


def read_json(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)


def execute(desc, cmd, cwd=None, capture=False):
    if not capture:
        print(f"{Emoji.GEAR.value} {desc}")
    try:
        if capture:
            return subprocess.check_output(cmd, shell=True, cwd=cwd, text=True).strip()
        subprocess.check_call(cmd, shell=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        if capture:
            return ""
        # Improved error reporting for git/docker failures
        error_msg = f"\n{Emoji.ERROR.value} Error during: {desc}. Aborting."
        if e.output:
            error_msg += f"\nDetails: {e.output}"
        sys.exit(error_msg)

# --- Docker Utilities ---


def stop_service(container_id, container_name=None):
    """Stops a Docker container by ID or name. Prefers ID if provided."""
    target = container_id if container_id else container_name
    identifier = container_name if container_name else (
        container_id[:12] if container_id else "unknown")
    execute(f"{Emoji.STOP_CONTAINER.value} Stopping container: {identifier}", f"docker stop {target}")

def delete_service(container_id, container_name=None):
    """Deletes a Docker container by ID or name. Prefers ID if provided."""
    target = container_id if container_id else container_name
    identifier = container_name if container_name else (
        container_id[:12] if container_id else "unknown")
    execute(f"{Emoji.DELETE_CONTAINER.value} Deleting container: {identifier}", f"docker rm {target}")

def restart_service(container_id, container_name=None):
    """Restarts a Docker container by ID or name. Prefers ID if provided."""
    target = container_id if container_id else container_name
    identifier = container_name if container_name else (
        container_id[:12] if container_id else "unknown")
    execute(f"{Emoji.RESTART.value} Restarting container: {identifier}", f"docker restart {target}")


def remove_image(image_id, image_name=None, force=False):
    """Removes a Docker image by ID or name. Prefers ID if provided."""
    # Extract just the hash part, removing 'sha256:' prefix and any quotes
    target = clean_image_id(image_id) if image_id else image_name
    
    identifier = image_name if image_name else (target[:12] if target else "unknown")
    flag = "-f" if force else ""
    execute(f"{Emoji.IMAGE.value} Removing image: {identifier}", f"docker rmi {flag} {target}")

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
    """Resolves env file path relative to scripts directory if not absolute."""
    if not env_file:
        return None
    
    env_path = Path(env_file)
    if not env_path.is_absolute():
        scripts_dir = Path(__file__).resolve().parent
        env_path = scripts_dir / env_file
    
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

def docker_build(repo_path, repo_name, mode='dev', no_cache=False, env_file=None):
    """Builds Docker images using docker compose."""
    file_name = "docker-compose.yml" if mode == 'prod' else "docker-compose.dev.yml"
    
    if not (repo_path / file_name).exists():
        print(f"  {Emoji.WARNING.value} Skipping Docker build: {file_name} not found.")
        return False
    
    cache_flag = "--no-cache" if no_cache else ""
    cmd = f"docker compose -f {file_name} build {cache_flag}".strip()
    
    # Load and set environment variables from env_file
    env_vars = load_and_apply_env_file(env_file)
    
    # Merge with current environment
    build_env = os.environ.copy()
    build_env.update(env_vars)
    
    execute(f"{Emoji.BUILD.value} Building {repo_name} ({mode})", cmd, cwd=repo_path)
    return True

def docker_start(repo_path, repo_name, mode='dev', env_file=None):
    """Starts Docker containers using docker compose."""
    file_name = "docker-compose.yml" if mode == 'prod' else "docker-compose.dev.yml"
    
    if not (repo_path / file_name).exists():
        print(f"  {Emoji.WARNING.value} Skipping Docker start: {file_name} not found.")
        return False
    
    # Copy env file to repo directory and load variables
    dest_env = copy_env_file_to_repo(env_file, repo_path)
    
    if dest_env:
        env_vars = load_env_file(dest_env)
        if env_vars:
            print(f"  {Emoji.KEY.value} Loaded {len(env_vars)} environment variables")
    
    cmd = f"docker compose -f {file_name} up -d"
    execute(f"{Emoji.START_CONTAINER.value} Starting {repo_name} ({mode})", cmd, cwd=repo_path)
    return True

# let's change it a bit so on change first stop the corresponding docker containers and then remove the old image then rebuild and update it in the json as well again
# start it again as well, so it's ready to use right away


def docker_rebuild_image(repo_path, repo_name, mode='dev', env_file=None):
    """Rebuilds Docker image with proper container lifecycle management: stop -> remove old image -> rebuild -> start."""
    file_name = "docker-compose.yml" if mode == 'prod' else "docker-compose.dev.yml"

    if not (repo_path / file_name).exists():
        print(f"  {Emoji.WARNING.value} Skipping Docker rebuild: {file_name} not found.")
        return False

    print(f"\n{Emoji.REBUILD.value} Rebuilding Docker image for {repo_name} ({mode} mode)")

    # Step 1: Get current image info before stopping containers
    print(f"  {Emoji.INFO.value} [1/5] Capturing current deployment details...")
    old_image_info, old_services = get_deployment_details(repo_path)
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
    image_info, services = get_deployment_details(repo_path)
    update_repo_tracking(repo_name, image_info=image_info, services=services)

    print(f"  {Emoji.SUCCESS.value} Successfully rebuilt and deployed {repo_name}")
    if image_info:
        print(f"      New image: {image_info.get('name', 'N/A')}")
    print(f"      Running services: {len(services)}")

    return True


def has_git_changes(repo_path):
    """Checks if there are uncommitted changes or if the repository was recently updated."""
    try:
        # Check for uncommitted changes (modified, added, deleted files)
        status = execute("", "git status --porcelain",
                         cwd=repo_path, capture=True)
        if status:
            return True

        # Check if there are any commits that differ from the last known state
        # Using git log to see if there are recent commits (last 24 hours)
        recent_commits = execute(
            "", "git log --oneline --since='24 hours ago' -1", cwd=repo_path, capture=True)
        if recent_commits:
            return True

        return False
    except Exception:
        # If any check fails, assume changes exist to be safe
        return True

# --- Git Utilities ---


def pull_latest(repo_path, branch):
    """Pulls latest changes and fails if merge conflicts occur."""
    print(f"{Emoji.PULL.value} Pulling latest changes for branch: {branch}")
    try:
        # fetch and pull
        subprocess.check_call("git fetch origin", shell=True, cwd=repo_path)
        # We use --no-rebase to ensure a standard pull; check for success
        subprocess.check_call(
            f"git pull origin {branch}", shell=True, cwd=repo_path)
    except subprocess.CalledProcessError:
        sys.exit(
            f"\n{Emoji.ERROR.value} GIT PULL FAILED: Merge conflict or network error in {repo_path}. Aborting.")


def git_clone(url, repo_name, parent_dir):
    """Clones a repository from the given URL to the specified parent directory."""
    execute(f"{Emoji.CLONE.value} Cloning {repo_name}",
            f"git clone {url} {repo_name}", cwd=parent_dir)
    return parent_dir / repo_name


def git_checkout(repo_path, branch):
    """Checks out to the specified branch in the given repository path."""
    execute(f"{Emoji.CHECKOUT.value} Checking out {Emoji.BRANCH.value} {branch} in {repo_path.name}",
            f"git checkout {branch}", cwd=repo_path)

# --- Core Logic ---


def update_repo_tracking(repo_name, repo_path=None, github_url=None, branch=None, env_path=None, image_info=None, services=None, tracking_file='deployed_repos.json'):
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

    if image_info:
        entry['image'] = image_info
    if services is not None:
        entry['services'] = services

    write_json(tracking_file, data)


def get_deployment_details(repo_path):
    cmd = "docker compose ps --format json"
    output = execute("", cmd, cwd=repo_path, capture=True)

    services = []
    primary_image = {}

    if output:
        for line in output.splitlines():
            try:
                s = json.loads(line)
                container_id = s.get("ID")
                if not primary_image:
                    img_id_cmd = f"docker inspect --format='{{{{.Image}}}}' {container_id}"
                    image_id = execute("", img_id_cmd, capture=True)
                    # Clean the image ID by removing sha256: prefix and quotes
                    cleaned_image_id = clean_image_id(image_id)
                    primary_image = {"name": s.get("Image"), "id": cleaned_image_id}

                services.append({"name": s.get("Service"), "id": container_id})
            except (json.JSONDecodeError, Exception):
                continue
    return primary_image, services


def clone_and_checkout(repo_data, mode='dev'):
    url = repo_data['githubUrl']
    branch = repo_data.get('checkoutBranch', 'main')
    env_path = repo_data.get('envPath')  # Optional env file path
    repo_name = url.split('/')[-1].replace('.git', '')

    parent_dir = Path(__file__).resolve().parent.parent
    repo_path = parent_dir / repo_name

    is_new_clone = False
    has_changes = False

    if not repo_path.exists():
        repo_path = git_clone(url, repo_name, parent_dir)
        is_new_clone = True
        has_changes = True  # New clone always needs build
    else:
        # If it exists, get commit hash before pull
        try:
            commit_before = execute(
                "", f"git rev-parse HEAD", cwd=repo_path, capture=True)
        except:
            commit_before = ""

        # Pull latest changes
        pull_latest(repo_path, branch)

        # Get commit hash after pull
        try:
            commit_after = execute(
                "", f"git rev-parse HEAD", cwd=repo_path, capture=True)
        except:
            commit_after = ""

        # Check if commit changed or if there are uncommitted changes
        has_changes = (commit_before !=
                       commit_after) or has_git_changes(repo_path)

    # Save the basic info including URL, Branch, and envPath
    update_repo_tracking(repo_name, repo_path=repo_path,
                         github_url=url, branch=branch, env_path=env_path)

    git_checkout(repo_path, branch)

    # Check if we need to rebuild Docker image
    # For new clones or if there are changes, rebuild the image
    if not is_new_clone and has_changes:
        print(
            f"  {Emoji.INFO.value} Changes detected in {repo_name}, rebuilding Docker image...")
        docker_rebuild_image(repo_path, repo_name, mode, env_file=env_path)

    return repo_path, repo_name, has_changes, is_new_clone, env_path


def deploy_docker(repo_path, repo_name, mode='dev', env_file=None):
    file_name = "docker-compose.yml" if mode == 'prod' else "docker-compose.dev.yml"

    if not (repo_path / file_name).exists():
        print(f"  {Emoji.WARNING.value} Skipping Docker: {file_name} not found.")
        return

    # Build and start using utility methods
    docker_build(repo_path, repo_name, mode, env_file=env_file)
    docker_start(repo_path, repo_name, mode, env_file=env_file)

    image_info, services = get_deployment_details(repo_path)
    update_repo_tracking(repo_name, image_info=image_info, services=services)


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


if __name__ == "__main__":
    # pass
    deploy_mode = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    run_all('commands_2.json', mode=deploy_mode)
    # repo_to_update = Path(__file__).resolve().parent.parent / "crud-api-mongodb"
    # pull_latest(repo_to_update,'main')
    # remove_image('sha256:9d699b033067922774e3ab8cf38eb6e5cd9f40c28bebec386df11a07e1d0e47e', image_name='old_image_name', force=True)
