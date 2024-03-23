# modelteam.ai

Generate your modelteam profile with AI verified skills.

## Prerequisites

- Python 3.6 or higher
- Pip
- MacOS or Linux
- Minimum 8GB RAM

## Getting Started

- Create a folder `modelteam` and navigate to it. (Th)
- Create `modelteam/repos` folder
- Clone all the repositories you want to include in your profile to `modelteam/repos`
- Run the following command to generate your profile
    - Generates PDF profile for your personal use and a JSON file for uploading to your modelteam.ai profile

```bash
cd ~/modelteam
git clone https://github.com/modelteam-ai/modelteam.ai.git
cd modelteam.ai
# Generates venv and installs dependencies. Downloads all the AI models
./setup.sh config.ini
# Beyond this step, internet access is not required
# Generates your profile
./build_my_profile.sh ~/modelteam/repos config.ini
```