import sys
import os
from pathlib import Path

# Add the scripts directory to sys.path to allow imports from it
scripts_dir = Path(__file__).resolve().parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

import cli_application

if __name__ == "__main__":
    try:
        cli_application.main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
