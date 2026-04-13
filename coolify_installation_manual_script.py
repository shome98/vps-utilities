import json
import subprocess
import sys

def run_installation(json_file):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_file} not found.")
        return

    for step in data['installation_steps']:
        print(f"--- Proceeding: {step['desc']} ---")
        
        # shell=True is used here because the commands involve shell features 
        # like curly brace expansion and pipes.
        process = subprocess.run(step['cmd'], shell=True, executable='/bin/bash')
        
        if process.returncode != 0:
            print(f"❌ Error occurred during: {step['desc']}")
            sys.exit(1)
        
    print("\n✅ Coolify installation complete!")
    print("Access it at http://<your-vps-ip>:8000")

if __name__ == "__main__":
    run_installation('commands.json')