import argparse
import sys

from modelteam_utils.utils import sha256_hash
from setup_utils import get_python_bin, run_command_stream, get_profile_path_file_name


def usage():
    print("Usage: edit_skills.py -g <git_email_id> [--cli_mode]")
    print("e.g. edit_skills.py -g user@org.ai --cli_mode")
    print("e.g. edit_skills.py -g user@org.ai")


def run_edit_and_sign(input_path, git_email_id, cli_mode, dev):
    if dev:
        config = "../config-dev.ini"
    else:
        config = "config.ini"
    user_key = sha256_hash(git_email_id)
    python_bin = get_python_bin(create_venv=False)
    edit_and_sign_command = [
        python_bin, "-m", "edit_and_sign",
        "--profile_path", input_path,
        "--user_key", user_key,
        "--config", config
    ]

    if cli_mode:
        edit_and_sign_command.append('--cli_mode')
    run_command_stream(edit_and_sign_command)


def main():
    parser = argparse.ArgumentParser(description="Create a ModelTeam profile.")
    parser.add_argument("-g", "--git_email_id", required=True, help="Git ID of the user present in git log")
    parser.add_argument("-c", "--cli_mode", required=False, default=False, action='store_true', help="CLI Mode")
    parser.add_argument("--dev", required=False, default=False, action='store_true', help="Development Mode")

    args = parser.parse_args()
    git_email_id = args.git_email_id
    cli_mode = args.cli_mode
    profile_path_file = get_profile_path_file_name(git_email_id)
    try:
        with open(profile_path_file, "r") as f:
            input_path = f.read().strip()
    except FileNotFoundError:
        print(f"{profile_path_file} not found. First run gen_git_stats.py")
        sys.exit(1)
    print("Loading...", flush=True)
    run_edit_and_sign(input_path, git_email_id, cli_mode, args.dev)


if __name__ == "__main__":
    main()
