set -e
source mdltm/bin/activate
num_years=10
# Check if the number of arguments is correct (2 or 3)
if [ "$#" -ne 2 ] && [ "$#" -ne 3 ]; then
  echo "Usage: $0 <input_path> <email_id> [<num_years>]"
  echo "Default value of num_years is 10"
  exit 1
fi
input_path=$1
email_id=$2
if [ "$#" -eq 3 ]; then
  num_years=$3
fi

HF_HUB_OFFLINE=1 python3 -m ModelTeamGitParser --input_path $input_path --output_path model_team_profile --config config.ini --user_email $email_id --num_years $num_years &
pid=$!
# prevent sleeping in mac
caffeinate -w $pid
wait $pid
curr_dir=$(pwd)
echo "ModelTeam profile created in $curr_dir/model_team_profile directory"
