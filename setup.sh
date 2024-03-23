set -e
python3 -m venv mdltm
source mdltm/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
python3 download_models.py --config config.ini
echo "ModelTeam setup complete"

