import os
import platform
from platform import python_version

from setup_utils import get_python_bin, run_command_stream


def main():
    # check if python version is >= 3.9
    pv = python_version()
    if int(pv.split(".")[0]) < 3 or int(pv.split(".")[1]) < 9:
        print("Please install python version >= 3.9")
        exit(1)

    print("Getting latest modelteam code")
    run_command_stream(["git", "pull"])

    print("Setting Virtual Environment and installing dependencies", flush=True)
    python_bin = get_python_bin(create_venv=True)

    # Use virtual environment's Python to install dependencies and run scripts
    run_command_stream([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
    run_command_stream([python_bin, "-m", "pip", "install", "-r", "requirements.txt"])
    # in windows set "HF_HUB_DISABLE_SYMLINKS_WARNING=1" to avoid warning
    if platform.system() == "Windows":
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    print("Downloading models..")
    run_command_stream([python_bin, "download_models.py", "--config", "config.ini"])

    print("modelteam setup complete")


if __name__ == "__main__":
    main()
