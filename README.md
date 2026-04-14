# VPS Utilities

Automated tools for managing VPS deployments, Docker installations, and GitHub repository orchestration.

## Quick Start

1. **Clone the repository** (Recommended branch: `main`):
   ```bash
   git clone -b main <REPOSITORY_URL> vps-utilities
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

## Configuration

Installation commands and repository tracking are stored in JSON files located in the `deployment-utilities/` directory:
- `docker_installation_commands.json`
- `coolify_installation_manual_commands.json`
- `deployed_repos.json` (Auto-generated)
