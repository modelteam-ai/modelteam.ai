![modelteam.ai](images/modelteam_logo.jpg)

**ModelTeam** is a cutting-edge AI-powered platform revolutionizing how organizations hire and manage their engineering
talent. By precisely matching talents with responsibilities based on skill sets, ModelTeam optimizes the fit and
efficiency of engineering teams.

Our AI platform extracts insights from engineers' work products, including code and technical documentation.
These insights drive recruiting, talent calibration, training, and talent reallocation.

ModelTeam is built on a robust foundation of training data from over a million engineers' contributions to open-source
projects, spanning 50 thousand skills and 9 programming languages. Leveraging this extensive training data, ModelTeam
evaluates engineers' expertise across various skill domains, assesses coding quality, and ranks them among their peers,
ensuring your organization has the best talent in the right roles.

## Prerequisites

- Python 3.7 or higher
- Pip
- Python-venv (if not included in Python installation)
- Git (command line)
- MacOS or Linux
- Minimum 8GB RAM
- ~15GB free disk space

## Getting Started

![Getting Started](images/getting_started.png)

- Create a folder `modelteam` and navigate to it. (Th)
- Create `modelteam/repos` folder
- Clone all the repositories you want to include in your profile to `modelteam/repos`
- Run the following command to generate your profile
    - Generates PDF profile for your personal use and a JSON file for creating your modelteam.ai verified profile

```bash
mkdir modelteam;cd modelteam
git clone https://github.com/modelteam-ai/modelteam.ai.git
cd modelteam.ai
# Generates venv and installs dependencies. Downloads all the AI models
./setup.sh
# Beyond this step, internet access is not required
# Generates your profile
./build_my_profile.sh modelteam/repos <email>
# Verify the generated profile and remove any unwanted/confidential information
./edit_and_sign.sh modelteam/model_team_profile/<email>.json
# Upload the signed profile to modelteam.ai
```