# VPS Utilities

Automated tools for managing VPS deployments, Docker installations, and GitHub repository orchestration.

# About
It uses docker files for deployment via docker. docker-compose file names must be `docker-compose.dev` or `docker-compose.prod` or `docker-compose.qa` with yaml and yml extension without this it fall backs to `docker-compose.yml` or `docker-compose.yaml`. May provide env file inside the folder that requires rebuild and restart otherwise can provide the env path.
can check [crud-api-mongodb](https://github.com/shome98/crud-api-mongodb) for better understanding.

## Quick Start

1. **Clone the repository** (Recommended branch: `dev-latest`):
   ```bash
   git clone -b dev-latest https://github.com/shome98/vps-utilities.git vps-utilities
   ```
2. **Launch the CLI**:
   ```bash
   python run_cli.py
   ```
   *Usage:* Run the script, select a menu option, and follow interactive prompts to deploy or manage services.

## Important: Folder Structure
To ensure paths resolve correctly, maintain this specific hierarchy:
```text
/apps (or your root)
├── deployment-utilities/       <-- Put JSON config files here
│   └── vps-utilities/          <-- This Repository
│       ├── run_cli.py
│       └── scripts/
└── [Cloned Repositories]       <-- Automatic deployment location
```

## Docker Permissions (Safe Execution)
To run Docker commands without using `sudo` (highly recommended), add your user to the `docker` group:
```bash
# 1. Create the docker group (if it doesn't exist)
sudo groupadd docker

# 2. Add your current user to the group
sudo usermod -aG docker $USER

# 3. Apply the changes (log out and back in, or run this)
newgrp docker
```
*Note: This prevents file permission issues and allows the script to manage containers securely.*

## Features

1. **Deployment Dashboard**: View status of all your deployed repositories.
2. **Interactive Deployment**: Clone and deploy new repositories with Docker support.
3. **Batch Operations**: Deploy multiple repositories from a JSON configuration file.
4. **Service Management**: Start, stop, restart, or re-deploy existing services.
5. **Installation Manager**: Run automated installation scripts for Docker, Coolify, and more.
6. **Private Repository Support**: Securely store GitHub PATs and clone private repos without hardcoded secrets.

## Configuration

Installation commands and repository tracking and batch deployment are stored in JSON files located in the `deployment-utilities/` directory:
- `docker_installation_commands.json`
```json
{
    "installation_steps": [
        {
            "desc": "Update package index and install prerequisites",
            "cmd": "sudo apt-get update && sudo apt-get install -y ca-certificates curl"
        },
        {
            "desc": "Create directory for keyrings",
            "cmd": "sudo install -m 0755 -d /etc/apt/keyrings"
        },
        {
            "desc": "Download Docker's official GPG key",
            "cmd": "sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc"
        },
        {
            "desc": "Ensure proper permissions for the GPG key",
            "cmd": "sudo chmod a+r /etc/apt/keyrings/docker.asc"
        },
        {
            "desc": "Add the Docker repository to Apt sources",
            "cmd": "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null"
        },
        {
            "desc": "Update package index with new repository",
            "cmd": "sudo apt-get update"
        },
        {
            "desc": "Install Docker Engine and Compose plugins",
            "cmd": "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
        },
        {
            "desc": "Verify installation with Hello World",
            "cmd": "sudo docker run --rm hello-world"
        }
    ]
}
```
- `batch_deployment_example.json`
```json
[
    {
        "githubUrl": "git hub url here",
        "checkoutBranch": "preferred checkout branch name here on git pull this branch will be used",
        "envPath": "your env file",
        "deployMode": "mode of deployment dev , prod, qa",
        "credentialId": "optional-token-alias-here"
    }
]
```
- `credentials.json` (Auto-generated/Manual)
- `deployed_repos.json` (Auto-generated)

## Private Repository Setup

1. Open the CLI: `python run_cli.py`
2. Select **Manage Credentials (Tokens)** (Option 8).
3. Add your GitHub Personal Access Token (PAT) and give it an alias (e.g., `work-token`).
4. When deploying a private repository, the CLI will prompt you to select one of your saved tokens.

*Note: The CLI automatically redacts tokens from terminal output and logs for security.*
