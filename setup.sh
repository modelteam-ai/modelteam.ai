set -e
echo "Getting latest ModelTeam code"
git pull
echo "Setting Virtual Environment and installing dependencies"
python3 -m venv mdltm
source mdltm/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
echo "Downloading models"
python3 download_models.py --config config.ini
echo "ModelTeam setup complete"

