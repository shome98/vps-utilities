from enum import Enum

class Command(Enum):
    """
    Enum for all system commands used in the deployment utilities.
    Double braces {{ }} are used for literal braces in Docker/Git formats 
    to remain compatible with Python's .format() method.
    """
    
    # Docker Basic
    DOCKER_STOP = "docker stop {target}"
    DOCKER_RM = "docker rm {target}"
    DOCKER_RESTART = "docker restart {target}"
    DOCKER_RMI = "docker rmi {flags} {target}"
    DOCKER_INSPECT_IMAGE = "docker inspect --format='{{{{.Image}}}}' {target}"
    DOCKER_INSPECT_STATUS = "docker inspect --format='{{{{.State.Status}}}}' {target}"
    DOCKER_PS_FORMATTED = "docker ps --format '{{{{.ID}}}}|{{{{.Names}}}}|{{{{.Status}}}}|{{{{.Image}}}}'"
    
    # Docker Compose
    DOCKER_COMPOSE_BUILD = "docker compose -f {file} build {flags}"
    DOCKER_COMPOSE_UP = "docker compose -f {file} up -d"
    DOCKER_COMPOSE_PS = "docker compose ps --format json"
    DOCKER_COMPOSE_LOGS = "docker compose -f {file} logs -f {service}"
    
    # Git
    GIT_CLONE = "git clone {url} {name}"
    GIT_CHECKOUT = "git checkout {branch}"
    GIT_FETCH = "git fetch origin"
    GIT_PULL = "git pull origin {branch}"
    GIT_REV_PARSE = "git rev-parse HEAD"
    GIT_STATUS_PORCELAIN = "git status --porcelain"
    GIT_LOG_RECENT = "git log --oneline --since='24 hours ago' -1"
    GIT_LOG_HISTORY = "git log --oneline -5"
    GIT_STATUS_SHORT = "git status --short"
