<div align="center">
  <img src="images/modelteam_logo_blk.png" alt="modelteam">
</div>

**[ModelTeam](https://modelteam.ai)** is a cutting-edge AI-powered platform revolutionizing how engineers can validate & showcase their skills.
Our AI platform extracts insights from engineers' day-to-day work products, including code and technical documentation.
Thereby, ModelTeam provides a comprehensive and accurate assessment of engineers' skills, expertise, and coding quality.

ModelTeam is built on a robust foundation of training data from over a million engineers' contributions to open-source
projects, spanning 9 programming languages.

## Confidentiality & Security

We understand the importance of confidentiality and security of your code and data. ModelTeam.ai does not transfer any
of the code or data out of your local machine. Models and AI algorithms are downloaded to your local machine and the
code is executed locally.

The generated profile contains only the metadata and predicted skills. Even some of those skills can be removed before
uploading to modelteam.ai.

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
- Turn off sleep mode so the script can run without interruptions
    - Optional: caffeine (for linux)
- Visual C++ Redistributable (for Windows)
- Minimum 8GB RAM
- ~15GB free disk space
- You should have made contributions for a minimum period of 3 months.

## Getting Started

![Getting Started](images/getting_started.png)

- Run the following commands to generate your profile
    - **IMPORTANT: Run this in a night-time or when you are not using the computer as it will take some time and consume
      a lot of resources**
    - Our AI models run locally on your machine and does not send any data outside your machine.
    - Generates PDF profile for your personal use and a JSON file for creating your modelteam.ai verified profile

### 1. Setup

- Run the setup script to download the dependencies and models to your local machine

```bash
mkdir ~/modelteam
cd ~/modelteam
# Get the modelteam.ai code
git clone https://github.com/modelteam-ai/modelteam.ai.git
cd modelteam.ai
# Generates venv and installs dependencies. It will download all the AI models
python setup.py
```

### 2 Build your profile

- For this step, no internet access is required. Everything stays on your local machine
- Copy all the repositories you want to include in your profile to a single folder e.g. `~/modelteam/repos`
    - **This can be any path**, as long as they all are in a single folder. Same path should be used in the next step

```bash
# Clone / Copy all the repositories you want to include in your profile
# This can be any path, as long as they all are in a single folder
mkdir ~/modelteam/repos
cd ~/modelteam/repos
git clone <repo1>
git clone <repo2>
# These should be copies of cloned repos, downloading just source code won't work
cp -r <repo3> .
...
...
```

- Build your profile
- `email` should be the id/email you have in your git commits.

```bash
# Generates your profile. Takes email used in git commits and optionally number of years to consider
# Number of years is optional and defaults to 5 years. It's recommended to change it to your years of experience
python build_my_profile.py -r <repos_path> -e <email> [-n <number_of_years>]
# e.g. python build_my_profile.py -r ~/modelteam/repos -e user@org.ai -n 5
```

### 3. Upload

- Verify the generated profile and edit it using `sign_my_profile.py` (Don't edit the JSON file directly)
    - Remove any unwanted/confidential skills
    - Encrypt the JSON file using the provided key
        - Key will be emailed to you when you sign up
        - This helps us to verify that you own the email address
- Upload the file to your account in [modelteam.ai](https://app.modelteam.ai)

```bash
# If you are using linux server without GUI, use --cli_mode
python sign_my_profile.py --key <key> [--cli_mode]
# e.g. python sign_my_profile.py --key 2b7e151628aed2a6abf7158809cf4f3c --cli_mode
# e.g. python sign_my_profile.py --key 2b7e151628aed2a6abf7158809cf4f3c  # For MacOS
```
