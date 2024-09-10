set -e
source mdltm/bin/activate
#!/bin/bash

usage() {
  echo "Usage: $0 -r <repo_path> -t <team_name> [-e <email_ids_as_csv>] [-n <num_years>]"
  echo "e.g. $0 -r /home/user/repos -e user1@org.ai,user2@org.ai -t model_team -n 3"
  echo "If email_ids are not provided, profiles will be generated for all users in the repos"
  echo "Default num_years is 5"
  exit 1
}

input_path=""
email_id_csv=""
team_name=""
num_years=5

while getopts "r:e:t:n:" opt; do
  case $opt in
    r) input_path="$OPTARG" ;;
    e) email_id_csv="$OPTARG" ;;
    t) team_name="$OPTARG" ;;
    n) num_years="$OPTARG" ;;
    *) usage ;;
  esac
done

# Check if input_path is provided
if [ -z "$input_path" ]; then
  usage
fi

if [ -z "$team_name" ]; then
  usage
fi

if ! [[ "$num_years" =~ ^[0-9]+$ ]]; then
  echo "num_years should be a number"
  usage
fi


curr_dir=$(pwd)
curr_date=$(date +"%Y-%m-%d")
output_path="$curr_dir/model_team_profile/$curr_date"
echo "Creating ModelTeam profile in $output_path directory"
if [ -n "$email_id_csv" ]; then
  HF_HUB_OFFLINE=1 caffeinate python3 -m ModelTeamGitParser --input_path "$input_path" --output_path "$output_path" --config config.ini --user_emails "$email_id_csv" --num_years $num_years --team_name "$team_name" --compress_output
else
  HF_HUB_OFFLINE=1 caffeinate python3 -m ModelTeamGitParser --input_path "$input_path" --output_path "$output_path" --config config.ini --num_years $num_years --team_name "$team_name" --compress_output
fi
echo "$output_path" > model_team_profile_path.txt
echo "ModelTeam profile created in $output_path directory"
