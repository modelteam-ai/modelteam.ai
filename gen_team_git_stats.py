import argparse
import os
import re
import sys

from setup_utils import get_profile_path_file_name, run_model_team_git_parser


def usage():
    print("Usage: gen_team_git_stats.py [-r <repo_list.txt>] -t <team_name> [-g <git_ids_as_csv>] [-n <num_years>]")
    print("e.g. gen_team_git_stats.py -r /home/user/repo_list.txt -g user1@org.ai,user2@org.ai -t model_team -n 3")
    print("e.g. gen_team_git_stats.py -r /home/user/repo_list.txt -t model_team -n 3")
    print("If git_ids are not provided, profiles will be generated for all users in the repos")
    print("Default num_years is 3")
    sys.exit(1)


def validate_input(num_years, repo_list):
    """Validate the command line inputs."""
    if repo_list and not os.path.isfile(repo_list) and not os.path.isdir(repo_list):
        print("Repo list does not exist")
        usage()

    if not re.match(r"^[0-9]+$", str(num_years)):
        print("num_years should be a number")
        usage()


def main():
    parser = argparse.ArgumentParser(description="Create a ModelTeam profile.")
    parser.add_argument("-r", "--repos", required=True,
                        help="Path to the file containing paths of git folders or Path to directory containing git folders")
    parser.add_argument("-t", "--team_name", required=True, help="Name of the team")
    parser.add_argument("-g", "--git_ids", required=False, help="Git IDs of the users present in git log as csv")
    parser.add_argument("-n", "--num_years", type=int, default=3, help="Number of years (default is 3)")

    args = parser.parse_args()
    repo_list = args.repos
    team_name = args.team_name
    git_ids = args.git_ids
    num_years = args.num_years

    validate_input(num_years, repo_list)

    output_path = run_model_team_git_parser(repo_list, git_ids, num_years, team_name)
    print("Please upload the output file to \033[94mhttps://app.modelteam.ai/org/teams\033[0m")


if __name__ == "__main__":
    main()
