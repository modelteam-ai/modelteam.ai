import os
import platform

from setup_utils import get_python_bin, run_command_stream


def main():
    print("Getting latest ModelTeam code")
    run_command_stream(["git", "pull"])

    print("Setting Virtual Environment and installing dependencies")
    python_bin = get_python_bin(create_venv=True)

    # Use virtual environment's Python to install dependencies and run scripts
    run_command_stream([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
    run_command_stream([python_bin, "-m", "pip", "install", "-r", "requirements.txt"])
    # in windows set "HF_HUB_DISABLE_SYMLINKS_WARNING=1" to avoid warning
    if platform.system() == "Windows":
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    print("Downloading models..")
    run_command_stream([python_bin, "download_models.py", "--config", "config.ini"])

    print("ModelTeam setup complete")


if __name__ == "__main__":
    main()
