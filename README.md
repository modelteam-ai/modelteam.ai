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
- [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170) (for Windows)
- Minimum 8GB RAM
- ~15GB free disk space
- You should have made contributions for a **minimum period of 3 months**.

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
- Add full local paths of your git repos to a text file. 1 line for each repo. e.g. `~/repo_list.txt` 

```bash
# Clone all your repositories that you want to include in your profile if it's not already cloned
$ cat ~/repo_list.txt
/Users/obuli/modelteam.ai/shastraw.ai
/Users/obuli/modelteam.ai/shastraw.server
/Users/obuli/repos/modelteam.ai
```

- Build your profile
- `email` should be the id/email you have in your git commits.

```bash
# Generates your profile. Takes email used in git commits and optionally number of years to consider
# Number of years is optional and defaults to 5 years. It's recommended to change it to number of years you want to look back in git history
python build_my_profile.py -l <repo_list_file_name> -e <email> [-n <number_of_years_to_look_back>]
# e.g. python build_my_profile.py -l ~/repo_list.txt -e user@org.ai -n 5
```

### 3. Upload

- Verify the generated profile and edit it using `sign_my_profile.py` (Don't edit the JSON file directly)
    - Remove any unwanted/confidential skills
    - Encrypt the JSON file using the provided key
        - Key will be emailed to you when you sign up
        - This helps us to verify that you own the email address
- Upload the file(mt_profile_*****.enc.gz) to your account in [modelteam.ai](https://app.modelteam.ai/jobs)

```bash
# If you are using linux server without GUI, use --cli_mode
python sign_my_profile.py -k <key> -e <email> [--cli_mode]
# e.g. python sign_my_profile.py -k 2b7e151628aed2a6abf7158809cf4f3c -e user@org.ai # For MacOS/Windows
# e.g. python sign_my_profile.py -k 2b7e151628aed2a6abf7158809cf4f3c -e user@org.ai --cli_mode # For Linux
```
