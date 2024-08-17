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

## Supported Languages

- Python
- Javascript
- Java
- Go
- C
- C++
- PHP
- Ruby
- C#

## Prerequisites

- Python 3.7 or higher
- Pip
- Python-venv (if not included in Python installation)
- Git (command line)
- MacOS or Linux
- caffeine (for linux). caffeinate (for MacOS, built-in)
- Minimum 8GB RAM
- ~15GB free disk space
- You should have made contributions for a minimum period of 6 months.
- Your email address should match the email address used in your git commits
  - We are working on supporting noreply email addresses

## Getting Started

![Getting Started](images/getting_started.png)

- Create a folder `modelteam` and navigate to it.
- Create `modelteam/repos` folder
- Clone all the repositories you want to include in your profile to `modelteam/repos`
- Run the following command to generate your profile
    - **IMPORTANT: Run this in a night-time or when you are not using the computer as it will take some time and consume
      a lot of resources**
    - Generates PDF profile for your personal use and a JSON file for creating your modelteam.ai verified profile
### 1. Setup
- Clone the modelteam.ai repository
- Run the setup script to download the dependencies and models to your local machine
```bash
mkdir modelteam;cd modelteam
# Clone / Copy all the repositories you want to include in your profile
# This can be any path, as long as they all are in a single folder
mkdir repos;cd repos
git clone <repo1>
git clone <repo2>
cp -r <repo3> .
...
...
cd ..
# Get the modelteam.ai code
git clone https://github.com/modelteam-ai/modelteam.ai.git
cd modelteam.ai
# Generates venv and installs dependencies. It will download all the AI models
./setup.sh
```
### 2 Build your profile
- For this step, no internet access is required. Everything stays on your local machine
- Scans all the repositories in the `repos` folder and generates a JSON file with your profile
#### 2.a. For Individuals
```bash
# Generates your profile. Takes email used in git commits and optionally number of years to consider
# Number of years is optional and defaults to 5 years. It's recommended to change it to your years of experience
./build_my_profile.sh -r <repos_path> -e <email> [-n <number_of_years>]
# e.g. ./build_my_profile.sh -r /home/user/repos -e user@org.ai -n 5
```
#### 2.b. For Organizations
```bash
# Generates your team profile. Takes a list of emails or team name and optionally number of years to consider
# Number of years is optional and defaults to 5 years. It's recommended to reduce it as per your needs
./build_team_profile.sh -r <repos_path> -e "<email1>,<email2>,..." -t "team_name" [-n <number_of_years>]
# e.g. ./build_team_profile.sh -r /home/user/repos -e user1@org.ai,user2@org.ai -t model_team -n 3
```

### 3. Verify & Upload
- Verify the generated profile and remove any unwanted/confidential information
- Encrypt the JSON file using the provided key and upload it to your account in modelteam.ai
  - Key will be emailed to you
```bash
# If you are using linux server without GUI, use --cli_mode
./edit_and_sign.sh <key> [--cli_mode]
# e.g. ./edit_and_sign.sh 2b7e151628aed2a6abf7158809cf4f3c --cli_mode
# e.g. ./edit_and_sign.sh 2b7e151628aed2a6abf7158809cf4f3c  # For MacOS
```
