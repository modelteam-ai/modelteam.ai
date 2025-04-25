import argparse
import datetime
import os
import re
import sys

import requests

from modelteam_utils.constants import MT_PROFILE_JSON
from setup_utils import run_model_team_git_parser


def usage():
    print("Usage: process_teams.py -r <repo_dir> -c config_file [-n <num_years>]")
    print("e.g. process_teams.py -r /home/user/repos -n 3 -c config.txt")
    print("Default num_years is 3")
    sys.exit(1)


def validate_input(num_years, repo_list, config):
    """Validate the command line inputs."""
    if repo_list and not os.path.isdir(repo_list):
        print("Repo list does not exist")
        usage()

    if not re.match(r"^[0-9]+$", str(num_years)):
        print("num_years should be a number")
        usage()

    if not os.path.exists(config):
        print("Config file does not exist")
        usage()


def load_config(config):
    """Load the configuration file and return the org_hash and api_key."""
    org_hash = None
    api_key = None
    with open(config, 'r') as f:
        for line in f:
            if line.startswith("org_id"):
                org_hash = line.split("=")[1].strip()
            elif line.startswith("api_key"):
                api_key = line.split("=")[1].strip()
    return org_hash, api_key


def upload_profile(org_hash, api_key, team_name, merged_json_path):
    url = "http://127.0.0.1:5000/api/v1/org/team/teambot"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "org_hash": org_hash,
        "team_name": team_name
    }
    with open(merged_json_path, "rb") as f:
        files = {
            "file": ("mt_profile.json.gz", f, "application/gzip")
        }
        response = requests.put(url, headers=headers, data=data, files=files)

    if response.status_code in (200, 201):
        print("✅ Profile uploaded successfully.")
        print("Response:", response.json())
    else:
        print("❌ Failed to upload profile.")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create a modelteam profile.")
    parser.add_argument("-r", "--repos", required=True,
                        help="Path to directory containing git folders")
    parser.add_argument("-n", "--num_years", type=int, default=3, help="Number of years (default is 3)")
    parser.add_argument("-c", "--config", required=True)

    args = parser.parse_args()
    repo_list = args.repos
    num_years = args.num_years
    config = args.config
    org_hash, api_key = load_config(config)
    validate_input(num_years, repo_list, config)
    teams = os.listdir(repo_list)
    filtered_teams = [team for team in teams if os.path.isdir(os.path.join(repo_list, team))]
    if len(filtered_teams) == 0:
        print("No git folders found in the directory")
        usage()
    for team in filtered_teams:
        team_path = os.path.join(repo_list, team)
        output_path = run_model_team_git_parser(team_path, None, num_years, False, team)
        end_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        end_date = datetime.datetime.fromtimestamp(end_ts, tz=datetime.timezone.utc).strftime('%Y-%m-%d')
        merged_json = os.path.join(output_path, MT_PROFILE_JSON)
        merged_json = f"{merged_json}_{end_date}.gz"
        upload_profile(org_hash, api_key, team, merged_json)


if __name__ == "__main__":
    main()
