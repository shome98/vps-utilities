import json
import subprocess
import sys

def run_commands(config_file):
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_file} not found.")
        return

    for step in data['installation_steps']:
        print(f"--- Executing: {step['desc']} ---")
        
        # We use shell=True because some commands use pipes and redirects
        process = subprocess.run(step['cmd'], shell=True)
        
        if process.returncode != 0:
            print(f"\n[!] Error occurred during: {step['desc']}")
            print("Aborting installation.")
            sys.exit(1)
            
    print("\n[+] Docker installation completed successfully!")

if __name__ == "__main__":
    run_commands('commands.json')