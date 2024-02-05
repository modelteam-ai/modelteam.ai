config_file=$1
python -m venv mdltm
source mdltm/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python download_models.py --config $config_file
echo "ModelTeam setup complete"

