<div align="center">
  <img src="images/modelteam_logo_blk.png" alt="modelteam">
</div>

**[ModelTeam](https://modelteam.ai)** is a cutting-edge AI-powered platform revolutionizing how engineers can validate &
showcase their skills.
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
- Typescript
- Java
- Go
- C
- C++
- PHP
- Ruby
- C#
- Rust
- Scala
- Swift
- Kotlin
- Lua
- Dart
- Elixir

## Prerequisites

- Python 3.9 or higher
- Pip
- Python-venv (if not included in Python installation)
- Git (command line)
- Turn off sleep mode so the script can run without interruptions
    - Optional: caffeine (for linux)
- [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170) (
  for Windows)
- Minimum 8GB RAM
- ~15GB free disk space
- You should have made contributions for a **minimum period of 3 months**.

## Getting Started

[![Build your Modelteam profile](images/engVideo.png)](https://www.youtube.com/watch?v=GqwijKCqfRE)

**For Enterprises to Generate profiles for your team, refer to [Team Profile Generation](README_org.md)**

- Run the following commands to generate your profile.
    - **IMPORTANT: Run this in a night-time or when you are not using the computer as it will take some time and consume
      a lot of resources**
    - Our AI models run locally on your machine and does not send any data outside your machine.
    - Generates PDF profile for your personal use and a JSON file for creating your modelteam.ai verified profile

### 1. Setup

- Run [setup.py](setup.py) script to download the dependencies and models to your local machine
- This will create a virtual environment and install all the dependencies. It will not affect your system python.

```
mkdir ~/modelteam
cd ~/modelteam
git clone https://github.com/modelteam-ai/modelteam.ai.git
cd modelteam.ai
python3 setup.py
```

### 2 Generate your skill stats

- For this step, no internet access is required. Everything stays on your local machine

#### 2.1 Repo List

- Clone the repo to your local machine and add the full paths to a text file, one line for each repo. e.g.
  `/Users/xyz/repo_list.txt`. This file will be used later as input.
    - Alternatively, if all your repos are in a single directory, you can pass the directory path directly.
      - It won't work if repos are in subdirectories (e.g. /Users/xyz/repos/work/repo1, /Users/xyz/repos/personal/repo2 etc.)
      - In this case, you need to create a file with the list of repo paths

> $ cat /Users/xyz/repo_list.txt<br>
> /Users/xyz/backend<br>
> /Users/xyz/frontend<br>
> /Users/xyz/api

Or

> $ ls /Users/xyz/repos/<br>
> backend<br>
> frontend<br>
> api

#### 2.2 Git Email ID

`git_email_id` should be the id you have in
your git commits.
- You can get this by using `git log` command as shown below
- Text between <> is the git_email_id e.g. Author: XYZ <**userXYZ@org.ai**>

``` 
git log | grep username | head
```
> `git log | grep XYZ | head -3`
> `Author: XYZ <userXYZ@org.ai>`<br>
> `Author: XYZ <1234567+XYZ@users.noreply.github.com>`<br>
> `Author: XYZ <userXYZ@org.ai>`<br>

#### 2.3 Generate Stats

- Run [gen_git_stats.py](gen_git_stats.py) to generate your skill stats.
- Number of years is optional and defaults to 5 years. It's recommended to change it to number of years you want to look
  back in git history
- repo_list can be a file with list of repos or a directory containing all the repos

```
python3 gen_git_stats.py -r <repo_list> -g <git_email_id> [-n <number_of_years_to_look_back>]
```

**Examples**

```
python3 gen_git_stats.py -r /Users/xyz/repo_list.txt -g userXYZ@org.ai -n 5
```

```
python3 gen_git_stats.py -r /Users/xyz/repos/ -g 1234567+XYZ@users.noreply.github.com -n 5
```

- If you have multiple git email ids, you need to run the entire flow (except for setup.py) for each git email id
  separately
- **To Force re-run the job, delete the folder `model_team_profile/<git_email_id>` and run the script again**

### 3. Upload

- Verify the generated skill stats file and edit it using [sign_my_file.py](sign_my_file.py) (Don't edit the JSON file
  directly)
    - Remove any unwanted/confidential skills
    - Sign the JSON file using the key
        - If you don't have a key, create an experience with the git email id in https://app.modelteam.ai/experience.
          The key will be generated for you
- Upload the file(mt_metrics_yyyy-mm-dd_*****.json.gz) back to your experience in the UI
- Our AI models will analyze the data and generate a profile for you (<30 minutes)
- If you are using linux server without GUI, use --cli_mode

```
python3 sign_my_file.py -k <key> -g <git_email_id> [--cli_mode]
```

**Examples**

Mac/Windows

```
python3 sign_my_file.py -k 2b7e151628aed2a6abf7158809cf4f3c -g userXYZ@org.ai
```

Linux

```
python3 sign_my_file.py -k 2b7e151628aed2a6abf7158809cf4f3c -g 1234567+XYZ@users.noreply.github.com --cli_mode
```

