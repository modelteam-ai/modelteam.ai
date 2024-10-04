import argparse
import os
import re
import sys

from setup_utils import get_profile_path_fine_name, run_model_team_git_parser


def usage():
    print("Usage: build_my_profile.py -r <repo_path> [-e <email_id>] [-n <num_years>]")
    print("e.g. build_my_profile.py -r /home/user/repos -e user@org.ai -n 5")
    print("Default num_years is 5")
    sys.exit(1)


def validate_input(input_path, email_id, num_years):
    """Validate the command line inputs."""
    if not os.path.isdir(input_path):
        print("Input path does not exist")
        usage()

    if not re.match(r"^[0-9]+$", str(num_years)):
        print("num_years should be a number")
        usage()

    if "," in email_id:
        print("Please provide only one email id")
        usage()


def main():
    parser = argparse.ArgumentParser(description="Create a ModelTeam profile.")
    parser.add_argument("-r", "--repo_path", required=True, help="Path to the repository")
    parser.add_argument("-e", "--email_id", required=True, help="Email ID for the user")
    parser.add_argument("-n", "--num_years", type=int, default=5, help="Number of years (default is 5)")

    args = parser.parse_args()
    input_path = args.repo_path
    email_id = args.email_id
    num_years = args.num_years

    validate_input(input_path, email_id, num_years)

    profile_path_file = get_profile_path_fine_name()
    if os.path.exists(profile_path_file):
        os.remove(profile_path_file)

    output_path = run_model_team_git_parser(input_path, email_id, num_years)

    with open(profile_path_file, "w") as f:
        f.write(output_path)

    print(f"ModelTeam profile created in {output_path} directory")


if __name__ == "__main__":
    main()
