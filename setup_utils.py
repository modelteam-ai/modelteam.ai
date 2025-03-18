import os
import platform
import shutil
import signal
import subprocess
import sys
import urllib.parse
import venv
from datetime import datetime


def run_command_stream(command, shell=False):
    if shutil.which("caffeinate"):
        if sys.platform == "linux":
            command = ["caffeinate"] + command
        elif sys.platform == "darwin":
            command = ["caffeinate", "-dimsu"] + command

    process = subprocess.Popen(
        command,
        shell=shell,
        stdout=None,
        stderr=None,
        text=True
    )

    def handle_interrupt(signum, frame):
        generate_git_issue(130, command)
        process.terminate()  # Ensure the process is terminated
        sys.exit(130)  # Exit with code 130 (SIGINT)

    signal.signal(signal.SIGINT, handle_interrupt)

    return_code = process.wait()
    if return_code != 0:
        generate_git_issue(return_code, command)
        raise subprocess.CalledProcessError(return_code, command)


def generate_git_issue(return_code, command):
    blue_text = "\033[94m"
    reset_text = "\033[0m"
    if command[0] == "caffeinate":
        if command[1] == "-dimsu":
            command = command[2:]
        else:
            command = command[1:]
    if len(command) > 2:
        if command[1] == "-m":
            command_name = command[2]
        elif command[0].endswith("python"):
            command_name = command[1]
        else:
            command_name = " ".join(command[0:2])
    else:
        command_name = " ".join(command)
    title = urllib.parse.quote(f"Error:{command_name}")

    print(f"Error: Command {command} failed with return code {return_code}.")
    link = f"https://github.com/modelteam-ai/modelteam.ai/issues/new?title={title}"
    print(
        f"Please raise an issue at {blue_text}{link}{reset_text} with the error message. Or email us at support@modelteam.ai")


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


def run_model_team_git_parser(repo_list, email_id, num_years, is_dev_mode, team_name=None, force_rerun=False):
    """Run the ModelTeamGitParser script with the appropriate arguments."""
    print("!!!IMPORTANT!!! Please turn off sleep mode so that the job is not interrupted.", flush=True)
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

    if force_rerun and os.path.exists(output_path) and output_path != "/":
        print(f"Deleting the existing profile in {output_path} directory")
        print("Are you sure you want to delete the existing profile? (yes/no)")
        user_input = input()
        if user_input.lower() == "yes":
            shutil.rmtree(output_path)
    os.makedirs(output_path, exist_ok=True)
    print(f"Creating modelteam profile in {output_path} directory")
    python_bin = get_python_bin(create_venv=False)
    os.environ["HF_HUB_OFFLINE"] = "1"
    cmd = [
        python_bin, "-m", "ModelTeamGitParser",
        "--output_path", output_path,
        "--config", config,
        "--num_years", str(num_years),
        "--show_progress"
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

    # Run the process
    run_command_stream(cmd)
    return output_path
