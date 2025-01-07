import os
import platform
import shutil
import subprocess
import sys
import venv
from datetime import datetime


def run_command(command, shell=False):
    date = datetime.now().strftime("%Y-%m-%d")
    with open(f"log_{date}.txt", "a") as logfile:
        process = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ''):
            if 'MallocStackLogging' in line:
                continue
            print(line, end='')
            logfile.write(line)

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


def get_output_path(email_or_team_name):
    curr_dir = os.getcwd()
    sanitized_path = sanitize_email(email_or_team_name)
    profile_path_file = os.path.join(curr_dir, "model_team_profile", sanitized_path)
    return profile_path_file


def get_profile_path_file_name(git_id):
    out_path = get_output_path(git_id)
    profile_path_file = os.path.join(out_path, "model_team_profile_path.txt")
    return profile_path_file


def sanitize_email(email):
    """Sanitize email for use in file paths."""
    return email.replace('@', '_').replace('.', '_')


def run_model_team_git_parser(repo_list, email_id, num_years, is_dev_mode, team_name=None):
    """Run the ModelTeamGitParser script with the appropriate arguments."""
    if is_dev_mode:
        config = "../config-dev.ini"
    else:
        config = "config.ini"
    curr_date = datetime.now().strftime("%Y-%m-%d")
    if team_name:
        team_path = get_output_path(team_name)
        output_path = os.path.join(team_path, curr_date)
    else:
        # Sanitize the email ID for the output path
        email_path = get_output_path(email_id)
        output_path = os.path.join(email_path, curr_date)

    # Create the output directory
    os.makedirs(output_path, exist_ok=True)
    print(f"Creating ModelTeam profile in {output_path} directory")
    python_bin = get_python_bin(create_venv=False)
    os.environ["HF_HUB_OFFLINE"] = "1"
    cmd = [
        python_bin, "-m", "ModelTeamGitParser",
        "--output_path", output_path,
        "--config", config,
        "--num_years", str(num_years),
    ]
    # if repo_list is a file, pass it as --repo_list else pass it as --input_path
    if os.path.isfile(repo_list):
        cmd += ["--repo_list", repo_list]
    elif os.path.isdir(repo_list):
        cmd += ["--input_path", repo_list]
    else:
        print("Error: Invalid input. Please provide a valid repo_list file or directory.")
        sys.exit(1)

    if email_id:
        cmd += ["--user_emails", email_id]
    if team_name:
        cmd += ["--team_name", team_name, "--compress_output"]
    if sys.platform in ["darwin", "linux"] and shutil.which("caffeinate"):
        cmd = ["caffeinate"] + cmd
    else:
        print("WARNING!!! Caffeinate is not available on this system. Please turn off sleep mode manually.")

    # Run the process
    run_command(cmd)
    return output_path
