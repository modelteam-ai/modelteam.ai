python -m venv mdltm
source mdltm/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python download_models.py --config config.ini
echo "ModelTeam setup complete"

