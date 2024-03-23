set -e
source mdltm/bin/activate
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <input_path> <email_id>"
  exit 1
fi

input_path=$1
email_id=$2

python3 -m ModelTeamGitParser --input_path $input_path --output_path model_team_profile --config config.ini --user_email $email_id &
pid=$!
# prevent sleeping in mac
caffeinate -w $pid
wait $pid
curr_dir=$(pwd)
echo "ModelTeam profile created in $curr_dir/model_team_profile directory"
