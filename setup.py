import os
import platform

from setup_utils import run_command, get_python_bin


def main():
    print("Getting latest ModelTeam code")
    run_command(["git", "pull"])

    print("Setting Virtual Environment and installing dependencies")
    python_bin = get_python_bin(create_venv=True)

    # Use virtual environment's Python to install dependencies and run scripts
    run_command([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([python_bin, "-m", "pip", "install", "-r", "requirements.txt"])
    # in windows set "HF_HUB_DISABLE_SYMLINKS_WARNING=1" to avoid warning
    if platform.system() == "Windows":
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    print("Downloading models.. Please be patient, this may take a while")
    run_command([python_bin, "download_models.py", "--config", "config.ini"], show_spinner=True)

    print("ModelTeam setup complete")


if __name__ == "__main__":
    main()
