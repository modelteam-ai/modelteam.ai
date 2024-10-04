import os
import platform
import subprocess
import sys
import venv


def run_command(command, shell=False):
    # Start the subprocess
    process = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # Stream the output line by line
    for line in iter(process.stdout.readline, ''):
        print(line, end='')  # Print each line as it comes

    # Wait for the process to finish and get the final return code
    process.stdout.close()
    return_code = process.wait()

    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)


def get_python_bin(create_venv=False):
    venv_dir = "mdltm"
    # Create virtual environment
    if create_venv and not os.path.exists(venv_dir):
        venv.create(venv_dir, with_pip=True)
    elif not os.path.exists(venv_dir):
        print("Error: Virtual environment does not exist. Please run setup.py first.")
        sys.exit(1)

    # Path to the virtual environment's Python
    if platform.system() == "Windows":
        python_bin = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_bin = os.path.join(venv_dir, "bin", "python")
    return python_bin
