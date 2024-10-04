import os
import venv
import platform

from modelteam.setup_utils import get_python_bin
from setup_utils import run_command

def main():
    print("Getting latest ModelTeam code")
    run_command(["git", "pull"])

    print("Setting Virtual Environment and installing dependencies")
    python_bin = get_python_bin(create_venv=True)

    # Use virtual environment's Python to install dependencies and run scripts
    run_command([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([python_bin, "-m", "pip", "install", "-r", "requirements.txt"])

    print("Downloading models")
    run_command([python_bin, "download_models.py", "--config", "config.ini"])

    print("ModelTeam setup complete")

if __name__ == "__main__":
    main()
