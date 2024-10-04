import argparse
import os
import re
import sys

from setup_utils import get_profile_path_fine_name, run_model_team_git_parser


def usage():
    print("Usage: build_my_team_profile.py -r <repo_path> -t <team_name> [-e <email_ids_as_csv>] [-n <num_years>]")
    print("e.g. build_my_team_profile.py -r /home/user/repos -e user1@org.ai,user2@org.ai -t model_team -n 3")
    print("If email_ids are not provided, profiles will be generated for all users in the repos")
    print("Default num_years is 5")
    sys.exit(1)


def validate_input(input_path, num_years):
    """Validate the command line inputs."""
    if not os.path.isdir(input_path):
        print("Input path does not exist")
        usage()

    if not re.match(r"^[0-9]+$", str(num_years)):
        print("num_years should be a number")
        usage()


def main():
    parser = argparse.ArgumentParser(description="Create a ModelTeam profile.")
    parser.add_argument("-r", "--repo_path", required=True, help="Path to the repository")
    parser.add_argument("-t", "--team_name", required=True, help="Name of the team")
    parser.add_argument("-e", "--email_ids", required=False, help="Email ID for the user")
    parser.add_argument("-n", "--num_years", type=int, default=5, help="Number of years (default is 5)")

    args = parser.parse_args()
    input_path = args.repo_path
    team_name = args.team_name
    email_ids = args.email_ids
    num_years = args.num_years

    validate_input(input_path, num_years)

    output_path = run_model_team_git_parser(input_path, email_ids, num_years, team_name)
    print(f"ModelTeam profile created in {output_path} directory")


if __name__ == "__main__":
    main()
