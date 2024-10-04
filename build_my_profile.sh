set -e
source mdltm/bin/activate
usage() {
  echo "Usage: $0 -r <repo_path> [-e <email_id] [-n <num_years>]"
  echo "e.g. $0 -r /home/user/repos -e user@org.ai -n 5"
  echo "Default num_years is 5"
  exit 1
}

input_path=""
email_id=""
num_years=5

while getopts "r:e:n:" opt; do
  case $opt in
  r) input_path="$OPTARG" ;;
  e) email_id="$OPTARG" ;;
  n) num_years="$OPTARG" ;;
  *) usage ;;
  esac
done

if [ -z "$input_path" ]; then
  usage
fi

if [ -z "$email_id" ]; then
  usage
fi

if ! [[ "$num_years" =~ ^[0-9]+$ ]]; then
  echo "num_years should be a number"
  usage
fi

if [[ "$email_id" == *","* ]]; then
  echo "Please provide only one email id"
  usage
fi

if [ ! -d "$input_path" ]; then
  echo "Input path does not exist"
  usage
fi

rm -f model_team_profile/model_team_profile_path.txt
curr_dir=$(pwd)
curr_date=$(date +"%Y-%m-%d")
# sanitize emailid for file path
email_path=$(echo "$email_id" | sed 's/@/_/g' | sed 's/\./_/g')
output_path="$curr_dir/model_team_profile/$email_path/$curr_date"
mkdir -p "$output_path"
echo "Creating ModelTeam profile in $output_path directory"
HF_HUB_OFFLINE=1 caffeinate python3 -m ModelTeamGitParser --input_path "$input_path" --output_path "$output_path" --config config.ini --user_emails "$email_id" --num_years $num_years
echo "$output_path" > model_team_profile/model_team_profile_path.txt
echo "ModelTeam profile created in $output_path directory"
