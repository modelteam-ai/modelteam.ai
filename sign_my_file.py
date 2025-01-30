import argparse
import os
import sys

from setup_utils import get_python_bin, run_command, get_profile_path_file_name


def usage():
    print("Usage: sign_my_file.py -g <git_email_id> -k <validation_key> [--cli_mode]")
    print("e.g. sign_my_file.py -g user@org.ai -k 123456 --cli_mode")
    print("e.g. sign_my_file.py -g user@org.ai -k 123456")


def run_edit_and_sign(input_path, user_key, cli_mode, config):
    python_bin = get_python_bin(create_venv=False)
    edit_and_sign_command = [
        python_bin, "-m", "edit_and_sign",
        "--profile_path", input_path,
        "--user_key", user_key,
        "--config", config
    ]

    if cli_mode:
        edit_and_sign_command.append('--cli_mode')
    run_command(edit_and_sign_command)


def main():
    parser = argparse.ArgumentParser(description="Create a ModelTeam profile.")
    parser.add_argument("-k", "--key", required=True, help="Validation Key")
    parser.add_argument("-g", "--git_email_id", required=True, help="Git ID of the user present in git log")
    parser.add_argument("-c", "--cli_mode", required=False, default=False, action='store_true', help="CLI Mode")
    parser.add_argument("--dev", required=False, default=False, action='store_true', help="Development Mode")

    args = parser.parse_args()
    key = args.key
    git_email_id = args.git_email_id
    cli_mode = args.cli_mode
    if args.dev:
        config = "../config-dev.ini"
    else:
        config = "config.ini"
    if not key:
        usage()
        sys.exit(1)
    profile_path_file = get_profile_path_file_name(git_email_id)
    try:
        with open(profile_path_file, "r") as f:
            input_path = f.read().strip()
    except FileNotFoundError:
        print(f"{profile_path_file} not found. First run gen_git_stats.py")
        sys.exit(1)
    print("Loading...", flush=True)
    run_edit_and_sign(input_path, key, cli_mode, config)


if __name__ == "__main__":
    main()
