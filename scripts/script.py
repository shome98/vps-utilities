import json
import subprocess
import sys
from pathlib import Path

# --- Utilities ---

def read_json(path):
    path = Path(path)
    if not path.exists(): return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def execute(desc, cmd, cwd=None, capture=False):
    if not capture: print(f"--- {desc} ---")
    try:
        if capture:
            return subprocess.check_output(cmd, shell=True, cwd=cwd, text=True).strip()
        subprocess.check_call(cmd, shell=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        if capture: return ""
        # Improved error reporting for git/docker failures
        error_msg = f"\n[!] Error during: {desc}. Aborting."
        if e.output: error_msg += f"\nDetails: {e.output}"
        sys.exit(error_msg)

# --- Docker Utilities ---

def stop_service(target):
    execute(f"Stopping: {target}", f"docker stop {target}")

def restart_service(target):
    execute(f"Restarting: {target}", f"docker restart {target}")

def remove_image(target, force=False):
    flag = "-f" if force else ""
    execute(f"Removing image: {target}", f"docker rmi {flag} {target}")

# --- Git Utilities ---

def pull_latest(repo_path, branch):
    """Pulls latest changes and fails if merge conflicts occur."""
    print(f"--- Pulling latest changes for branch: {branch} ---")
    try:
        # fetch and pull
        subprocess.check_call("git fetch origin", shell=True, cwd=repo_path)
        # We use --no-rebase to ensure a standard pull; check for success
        subprocess.check_call(f"git pull origin {branch}", shell=True, cwd=repo_path)
    except subprocess.CalledProcessError:
        sys.exit(f"\n[!] GIT PULL FAILED: Merge conflict or network error in {repo_path}. Aborting.")

def git_clone(url, repo_name, parent_dir):
    """Clones a repository from the given URL to the specified parent directory."""
    execute(f"Cloning {repo_name}", f"git clone {url} {repo_name}", cwd=parent_dir)
    return parent_dir / repo_name

def git_checkout(repo_path, branch):
    """Checks out to the specified branch in the given repository path."""
    execute(f"Checking out {branch} in {repo_path.name}", f"git checkout {branch}", cwd=repo_path)

# --- Core Logic ---

def update_repo_tracking(repo_name,repo_path=None, github_url=None, branch=None, image_info=None, services=None, tracking_file='deployed_repos.json'):
    data = read_json(tracking_file)
    entry = next((item for item in data if item.get('folder_name') == repo_name), None)
    
    if not entry:
        entry = {"folder_name": repo_name}
        data.append(entry)
    
    
    if repo_path: entry['folderPath'] = str(repo_path)
    if github_url: entry['githubUrl'] = github_url
    if branch: entry['checkoutBranch'] = branch
    
    if image_info: entry['image'] = image_info
    if services is not None: entry['services'] = services
    
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
                    primary_image = {"name": s.get("Image"), "id": image_id}

                services.append({"name": s.get("Service"), "id": container_id})
            except (json.JSONDecodeError, Exception):
                continue
    return primary_image, services

def clone_and_checkout(repo_data):
    url = repo_data['githubUrl']
    branch = repo_data.get('checkoutBranch', 'main')
    repo_name = url.split('/')[-1].replace('.git', '')
    
    parent_dir = Path(__file__).resolve().parent.parent
    repo_path = parent_dir / repo_name

    if not repo_path.exists():
        repo_path = git_clone(url, repo_name, parent_dir)
    else:
        # If it exists, pull latest changes
        pull_latest(repo_path, branch)
    
    # Save the basic info including URL and Branch
    update_repo_tracking(repo_name, repo_path=repo_path, github_url=url, branch=branch)
    
    git_checkout(repo_path, branch)
    return repo_path, repo_name

def deploy_docker(repo_path, repo_name, mode='dev'):
    file_name = "docker-compose.yml" if mode == 'prod' else "docker-compose.dev.yml"
    
    if not (repo_path / file_name).exists():
        print(f"  [!] Skipping Docker: {file_name} not found.")
        return

    cmd = f"docker compose -f {file_name} up -d --build"
    execute(f"Deploying {repo_name} ({mode})", cmd, cwd=repo_path)
    
    image_info, services = get_deployment_details(repo_path)
    update_repo_tracking(repo_name, image_info=image_info, services=services)

def run_all(config_file, mode='dev'):
    data = read_json(config_file)
    for repo in data.get('repositories', []):
        repo_path, repo_name = clone_and_checkout(repo)
        deploy_docker(repo_path, repo_name, mode=mode)

    for step in data.get('installation_steps', []):
        execute(step['desc'], step['cmd'])
        
    print(f"\n[+] All tasks completed successfully in {mode} mode!")

if __name__ == "__main__":
    # pass
    deploy_mode = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    run_all('commands_2.json', mode=deploy_mode)
    # repo_to_update = Path(__file__).resolve().parent.parent / "crud-api-mongodb"
    # pull_latest(repo_to_update,'main')
    # remove_image('sha256:9d699b033067922774e3ab8cf38eb6e5cd9f40c28bebec386df11a07e1d0e47e')