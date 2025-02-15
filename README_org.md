<div align="center">
  <img src="images/sampleProfile.png" alt="modelteam">
</div>

# ModelTeam: AI-Powered Skill Validation for Engineers

**[ModelTeam](https://modelteam.ai)** is an AI-driven platform that helps engineers validate and showcase their skills.
By analyzing real-world coding contributions, ModelTeam provides insights into expertise and code quality. Our platform helps teams identify and retain top talent and ensures the best engineers are matched to the
right roles, optimizing performance and success.

[View Sample Profile](https://app.modelteam.ai/profile?id=1da842a06520c30722ff3efb96d67a482cd689e6d43b87c882d4b690975a7c31)

ModelTeam is trained on contributions from over a million engineers across multiple open-source projects, supporting
analysis in **15+ programming languages**.

## Security & Privacy

Your code and data remain **on your local machine**. The AI models run locally, ensuring no data is transferred
externally. The generated profile contains only metadata and predicted skills, with an option to remove specific skills
before uploading.

## Supported Languages

Python, JavaScript, TypeScript, Java, Go, C, C++, PHP, Ruby, C#, Rust, Scala, Swift, Kotlin, Lua, Dart, Elixir

---

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

### 1. Install ModelTeam Locally

```
mkdir ~/modelteam && cd ~/modelteam
git clone https://github.com/modelteam-ai/modelteam.ai.git
cd modelteam.ai
python3 setup.py
```

This script:

- Sets up a **virtual environment**
- Installs **dependencies**
- Downloads **AI models**

### 2 Extract Skills from Your Code

- For this step, no internet access is required. Everything stays on your local machine
- `python3 gen_team_git_stats.py -r <repo_list> [-g "<gitemail1>,<gitemail2>,..."] -t "<team_name>" [-n <number_of_years>]`

#### Defining Your Repositories

- Clone the repos to your local machine and add the full paths to a text file, one line for each repo. e.g.

> $ cat /Users/xyz/repo_list.txt<br>
> /Users/xyz/backend<br>
> /Users/xyz/frontend<br>
> /Users/xyz/api

- Alternatively, if all your repos are in a single directory, you can pass the directory path directly.
    - It won't work if repos are in subdirectories (e.g. /Users/xyz/repos/work/repo1, /Users/xyz/repos/personal/repo2
      etc.)
    - In this case, you need to create a file with the list of repo paths as shown above

> $ ls /Users/xyz/repos/<br>
> backend<br>
> frontend<br>
> api


#### Finding Your Git Email ID (Optional, if you want to generate profile only for specific individuals)

- `git_email_id` should be the id you have in your git commits.
    - You can get this by using `git log` command as shown below

``` 
git log | grep username | head
```
> `git log | grep XYZ | head -3`
> `Author: XYZ <userXYZ@org.ai>`<br>
> `Author: XYZ <1234567+XYZ@users.noreply.github.com>`<br>
> `Author: XYZ <userXYZ@org.ai>`<br>

- Use the git email id inside `<...>` in the above output

#### Running the Skill Extraction Script

```
python3 gen_team_git_stats.py -r <repo_list> [-g "<gitemail1>,<gitemail2>,..."] -t "<team_name>" [-n <number_of_years>]
```
- Extract Team stats using [gen_team_git_stats.py](gen_team_git_stats.py). If your team is big, we recommend generating
  profiles only for the team members who are actively contributing to the repositories and are relevant to the team's skills.
- Generates your team profile. Takes a list of git email ids or team name and optionally number of years to consider
- Number of years is optional and defaults to 3 years. It's recommended to reduce it as per your needs

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

