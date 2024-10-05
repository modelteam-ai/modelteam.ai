![modelteam.ai](images/modelteam_logo.jpg)

At **ModelTeam**, we develop proprietary Large Language Models (LLMs) to evaluate engineers’ skills and
capabilities by examining code and technical documentations. We use these models, learned from a training set of
millions of engineers, to develop a unique data assets that powers a vertical talent insight platform for software
engineers. Our platform helps teams identify and retain top talent and ensures the best engineers are matched to the
right roles, optimizing performance and success.

Our AI platform extracts insights from engineering team's day-to-day work products, including code and technical
documentation. Thereby, ModelTeam provides a comprehensive and accurate assessment of engineers' skills, expertise, and
coding quality.

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
- MacOS or Linux
- caffeine (for linux). caffeinate (for MacOS, built-in)
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

### 2 Build Team profile

- For this step, no internet access is required. Everything stays on your local machine
- Copy all the repositories you want to include in your profile to a single folder e.g. `~/modelteam/repos`
    - This can be any path, as long as they all are in a single folder. Same path should be used in the next step

```bash
# Clone / Copy all the repositories you want to include in your profile
# This can be any path, as long as they all are in a single folder
mkdir ~/modelteam/repos
cd ~/modelteam/repos
git clone <repo1>
git clone <repo2>
cp -r <repo3> .
...
...
```

- Build your team's profile. If your team is big, we recommend generating profiles only for the team members who are
  actively contributing to the repositories and are relevant to the team's skills.

```bash
# Generates your team profile. Takes a list of emails or team name and optionally number of years to consider
# Number of years is optional and defaults to 5 years. It's recommended to reduce it as per your needs
python build_my_team_profile.py -r <repos_path> [-e "<email1>,<email2>,..."] -t "team_name" [-n <number_of_years>]
# e.g. python build_my_team_profile.py -r ~/modelteam/repos -e user1@org.ai,user2@org.ai -t model_team -n 3
# e.g. python build_my_team_profile.py -r ~/modelteam/repos -t model_team -n 3
```

### 3. Upload

- Just upload the generated JSON file to create your team in modelteam.ai
