import argparse
import os
import re
import sys

from setup_utils import get_profile_path_file_name, run_model_team_git_parser


def usage():
    print("Usage: gen_git_stats.py -g <git_email_id> -r <repo_list.txt> [-n <num_years_lookback>]")
    print("e.g. gen_git_stats.py -r /home/user/repo_list.txt -g user@org.ai -n 5")
    print("e.g. gen_git_stats.py -r /home/user/repo_list.txt -g user@users.noreply.github.com -n 5")
    print("Default num_years_lookback is 5")
    sys.exit(1)


def validate_input(git_email_id, num_years, repo_list):
    """Validate the command line inputs."""
    if repo_list and not os.path.isfile(repo_list) and not os.path.isdir(repo_list):
        print("Repo list does not exist.. Create a file with list of git folders or provide a directory path that contains git folders")

    if not re.match(r"^[0-9]+$", str(num_years)):
        print("num_years should be a number")

    if "," in git_email_id:
        print("Please provide only one git id")


def main():
    parser = argparse.ArgumentParser(description="Create a modelteam profile.")
    parser.add_argument("-r", "--repos", required=True,
                        help="Path to the file containing paths of git folders or Path to directory containing git folders")
    parser.add_argument("-g", "--git_email_id", required=True, help="Git ID of the user present in git log")
    parser.add_argument("-n", "--num_years", type=int, default=5,
                        help="Number of years to lookback in git history (default is 5)")
    parser.add_argument("--dev", required=False, default=False, action='store_true', help="Development Mode")


    args = parser.parse_args()
    repo_list = args.repos
    git_email_id = args.git_email_id
    num_years = args.num_years

    validate_input(git_email_id, num_years, repo_list)

    profile_path_file = get_profile_path_file_name(git_email_id)
    if os.path.exists(profile_path_file):
        os.remove(profile_path_file)

    output_path = run_model_team_git_parser(repo_list, git_email_id, num_years, args.dev)

    with open(profile_path_file, "w") as f:
        f.write(output_path)
    star_line = "*" * 80
    print(star_line)
    print("Please run the following command to edit your stats file: (add --cli_mode for CLI mode)")
    print(f"\033[1m\033[94mpython3 edit_skills.py -g {git_email_id}\033[0m")
    print(star_line)


if __name__ == "__main__":
    main()
