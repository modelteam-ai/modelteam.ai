set -e
source mdltm/bin/activate
num_years=5
if [ "$#" -ne 2 ] && [ "$#" -ne 3 ]; then
  echo "Usage: $0 <input_path> <email_id|csv_of_email_ids> [<num_years>]"
  echo "Default value of num_years is 5"
  exit 1
fi
input_path=$1
email_id=$2
if [ "$#" -eq 3 ]; then
  num_years=$3
fi
curr_dir=$(pwd)
curr_date=$(date +"%Y-%m-%d")
output_path="$curr_dir/model_team_profile/$curr_date"
echo "Creating ModelTeam profile in $output_path directory"
HF_HUB_OFFLINE=1 caffeinate python3 -m ModelTeamGitParser --input_path "$input_path" --output_path "$output_path" --config config.ini --user_emails $email_id --num_years $num_years
echo "$output_path" > model_team_profile_path.txt
echo "ModelTeam profile created in $output_path directory"
