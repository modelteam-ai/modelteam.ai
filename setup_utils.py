import os
import platform
import subprocess
import sys
import venv
from datetime import datetime


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


def get_profile_path_fine_name():
    curr_dir = os.getcwd()
    profile_path_file = os.path.join(curr_dir, "model_team_profile", "model_team_profile_path.txt")
    return profile_path_file


def sanitize_email(email):
    """Sanitize email for use in file paths."""
    return email.replace('@', '_').replace('.', '_')


def run_model_team_git_parser(input_path, email_id, num_years, team_name=None, config_file="config.ini"):
    """Run the ModelTeamGitParser script with the appropriate arguments."""
    curr_dir = os.getcwd()
    curr_date = datetime.now().strftime("%Y-%m-%d")
    if team_name:
        output_path = os.path.join(curr_dir, "model_team_profile", team_name, curr_date)
    else:
        # Sanitize the email ID for the output path
        email_path = sanitize_email(email_id)
        output_path = os.path.join(curr_dir, "model_team_profile", email_path, curr_date)

    # Create the output directory
    os.makedirs(output_path, exist_ok=True)
    print(f"Creating ModelTeam profile in {output_path} directory")
    python_bin = get_python_bin(create_venv=False)
    os.environ["HF_HUB_OFFLINE"] = "1"
    cmd = [
        python_bin, "-m", "ModelTeamGitParser",
        "--input_path", input_path,
        "--output_path", output_path,
        "--config", config_file,
        "--user_emails", email_id,
        "--num_years", str(num_years)
    ]

    # Check if running on macOS or Linux and add caffeinate if available
    if sys.platform in ["darwin", "linux"]:
        cmd = ["caffeinate"] + cmd

    # Run the process
    run_command(cmd)
    return output_path