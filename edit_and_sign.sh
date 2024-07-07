set -e
source mdltm/bin/activate
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <key>"
  echo "Key would have been sent to you by the ModelTeam"
  exit 1
fi
input_path=$(cat model_team_profile_path.txt)
output_path="$input_path-signed"
python3 -m edit_and_sign.py --profile_json "$input_path/mt_profile.json" --user_key "$1" --output_path "$output_path"
echo "ModelTeam profile Saved in $output_path directory"
