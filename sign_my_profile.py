import argparse
import os
import sys

from setup_utils import get_python_bin, run_command, get_profile_path_fine_name


def usage():
    print("Usage: sign_my_profile.py --key <validation_key> [--cli_mode]")
    print("e.g. sign_my_profile.py --key 123456 --cli_mode")


def run_edit_and_sign(input_path, user_key, cli_mode):
    python_bin = get_python_bin(create_venv=False)
    edit_and_sign_command = [
        python_bin, "-m", "edit_and_sign",
        "--profile_path", input_path,
        "--user_key", user_key,
    ]

    if cli_mode:
        edit_and_sign_command.append('--cli_mode')
    run_command(edit_and_sign_command)


def main():
    parser = argparse.ArgumentParser(description="Create a ModelTeam profile.")
    parser.add_argument("-k", "--key", required=True, help="Validation Key")
    parser.add_argument("-c", "--cli_mode", required=False, default=False, action='store_true', help="CLI Mode")

    args = parser.parse_args()
    key = args.key
    cli_mode = args.cli_mode
    if not key:
        usage()
        sys.exit(1)
    profile_path_file = get_profile_path_fine_name()
    try:
        with open(profile_path_file, "r") as f:
            input_path = f.read().strip()
    except FileNotFoundError:
        print(f"{profile_path_file} not found.")
        sys.exit(1)
    print("Loading...", flush=True)
    run_edit_and_sign(input_path, key, cli_mode)


if __name__ == "__main__":
    main()
