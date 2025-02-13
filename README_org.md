<div align="center">
  <img src="images/modelteam_logo_blk.png" alt="modelteam">
</div>

At **[ModelTeam](https://modelteam.ai)**, we develop proprietary Large Language Models (LLMs) to evaluate engineers’
skills and
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
- You should have made contributions for a minimum period of 3 months.

### Compute Needs

- If your team is under 10, your laptop or small server should be sufficient.
- If your team is larger, you may need a server with more resources. We recommend using a server with at least 32GB RAM
  and 8 cores.
- Following is sample runtime. ~10 hours for analyzing ~1M lines of code. (32GB machine with 8 cores).

```mono
+---------------------------------+-------------+
| Metric                          |       Value |
|---------------------------------+-------------|
| Time taken                      | 566 minutes |
| Kinds of files analyzed         |          go |
| Number of repositories analyzed |           1 |
| Number of months analyzed       |          37 |
| Number of lines analyzed        |      949114 |
| Number of skills extracted      |          89 |
+---------------------------------+-------------+
```

## Getting Started

[![Build your Team profile](images/orgVideo.png)](https://www.youtube.com/watch?v=JDGxgT9rwo0)

**For Individuals to Generate their profiles, refer to [Profile Generation](README.md)**
- Create an account in [ModelTeam](https://app.modelteam.ai/org/)
- Run the following commands to generate your profile
    - Our AI models run locally on your machine and does not send any data outside your machine.
    - Generates a JSON file for creating your modelteam.ai verified profile

### 1. Setup

- Run [setup.py](setup.py) to download the dependencies and models to your local machine
- This will create a virtual environment and install all the dependencies. It will not affect your system python.

```
mkdir ~/modelteam
cd ~/modelteam
git clone https://github.com/modelteam-ai/modelteam.ai.git
cd modelteam.ai
python3 setup.py
```

### 2 Generating Team Stats

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

#### 2.2 Git Email ID (Optional, if you want to generate profile only for specific individuals)

- `git_email_id` should be the id you have in your git commits.
    - You can get this by using `git log` command as shown below
    - Text between <> is the git_email_id e.g. Author: XYZ <**userXYZ@org.ai**>

``` 
git log | grep username | head
```
> `git log | grep XYZ | head -3`
> `Author: XYZ <userXYZ@org.ai>`<br>
> `Author: XYZ <1234567+XYZ@users.noreply.github.com>`<br>
> `Author: XYZ <userXYZ@org.ai>`<br>

#### 2.3 Extract Team stats

- Extract Team stats using [gen_team_git_stats.py](gen_team_git_stats.py). If your team is big, we recommend generating
  profiles only for the team members who are actively contributing to the repositories and are relevant to the team's skills.
- Generates your team profile. Takes a list of git email ids or team name and optionally number of years to consider
- Number of years is optional and defaults to 3 years. It's recommended to reduce it as per your needs
- repo_list can be a file with list of repos or a directory containing all the repos

```
python3 gen_team_git_stats.py -r <repo_list> [-g "<gitemail1>,<gitemail2>,..."] -t "<team_name>" [-n <number_of_years>]
```

**Examples**

```
python3 gen_team_git_stats.py -r ~/repo_list.txt -g "user1@org.ai,user2@org.ai" -t model_team -n 3
```

```
python3 gen_team_git_stats.py -r /Users/xyz/repos/ -t model_team -n 3
```

- **To Force re-run the job, delete the folder `model_team_profile/<team_name>` and run the script again**

### 3. Upload

- Just upload the generated JSON file to create your team in https://app.modelteam.ai/org/teams
- Our AI models will analyze the data and generate a profile for your team (<30 minutes)

