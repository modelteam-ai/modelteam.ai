import argparse
import os
import re
import sys
from datetime import datetime

from setup_utils import get_python_bin, run_command


def usage():
    print("Usage: build_my_profile.py -r <repo_path> [-e <email_id>] [-n <num_years>]")
    print("e.g. build_my_profile.py -r /home/user/repos -e user@org.ai -n 5")
    print("Default num_years is 5")
    sys.exit(1)


def sanitize_email(email):
    """Sanitize email for use in file paths."""
    return email.replace('@', '_').replace('.', '_')


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


def run_model_team_git_parser(input_path, output_path, email_id, num_years, config_file="config.ini"):
    """Run the ModelTeamGitParser script with the appropriate arguments."""
    python_bin = get_python_bin(create_venv=False)
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


def main():
    parser = argparse.ArgumentParser(description="Create a ModelTeam profile.")
    parser.add_argument("-r", "--repo_path", required=True, help="Path to the repository")
    parser.add_argument("-e", "--email_id", required=True, help="Email ID for the user")
    parser.add_argument("-n", "--num_years", type=int, default=5, help="Number of years (default is 5)")

    args = parser.parse_args()
    input_path = args.repo_path
    email_id = args.email_id
    num_years = args.num_years

    # Validate inputs
    validate_input(input_path, email_id, num_years)

    # Current working directory and date
    curr_dir = os.getcwd()
    curr_date = datetime.now().strftime("%Y-%m-%d")

    # Sanitize the email ID for the output path
    email_path = sanitize_email(email_id)
    output_path = os.path.join(curr_dir, "model_team_profile", email_path, curr_date)

    # Create the output directory
    os.makedirs(output_path, exist_ok=True)
    print(f"Creating ModelTeam profile in {output_path} directory")

    # Remove the existing model_team_profile_path.txt if it exists
    profile_path_file = os.path.join(curr_dir, "model_team_profile", "model_team_profile_path.txt")
    if os.path.exists(profile_path_file):
        os.remove(profile_path_file)

    # Run the ModelTeamGitParser
    run_model_team_git_parser(input_path, output_path, email_id, num_years)

    # Write the output path to model_team_profile_path.txt
    with open(profile_path_file, "w") as f:
        f.write(output_path)

    print(f"ModelTeam profile created in {output_path} directory")


if __name__ == "__main__":
    main()
