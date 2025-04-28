# Setup Instructions

## Prerequisites
- `git`
- `docker`

## Hardware Requirements
- 8–16 GB RAM
- 2–4 CPU cores
- 40 GB Disk Space

## Steps

1. Clone the repository:

    ```bash
    git clone https://github.com/modelteam-ai/modelteam.ai.git
    ```

2. Get your API keys from [ModelTeam Account Settings](https://app.modelteam.ai/org/account) and update the file called `api_config.ini`.

3. Clone all Git repositories following this folder structure:

    > Each team has its own folder under `~/repos`.  
    > (Even if you are the only one in the team, you should still create a team folder.)

    ```
    ~/repos
      ├── team1
      │    ├── t1-repo1
      │    └── t1-repo2
      ├── team2
      │    ├── t2-repo1
      │    └── t2-repo2
      ├── team3
      └── ...
      └── teamN
    ```
