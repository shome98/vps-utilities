import json
import subprocess
import sys

def read_json(path):
    """Reads and returns JSON data."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        sys.exit(f"Terminating: {e}")

def execute(desc, cmd):
    """Executes a shell command and exits on failure."""
    print(f"--- Executing: {desc} ---")
    try:
        # check_call automatically raises an error if return code != 0
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
        sys.exit(f"\n[!] Error during: {desc}. Aborting.")

def run_installation(config_file):
    data = read_json(config_file)
    
    # Iterate through the steps defined in your JSON
    for step in data.get('installation_steps', []):
        execute(step['desc'], step['cmd'])
        
    print("\n[+] Process completed successfully!")

# add a method to get the githubUrl from teh json file and execute it.
# it is in json in this format {[{githubUrl,checkoutBranch},...]} so get the url then extract the repo name from here, create a folder 
# at parent for it like suppose the scripts and json are in the apps/scripts folder the go to parent and create it if does not exist
# other wise can clone it inside if that is empty after that checkout to the branch 
# create reusable methods and can use existing ones as well.
#  for execute use pass the desc as something with the name extracted and then command
if __name__ == "__main__":
    run_installation('commands.json')