sudo docker build -t modelteam-docker .
nohup sudo docker run \
  -v "$PWD":/home/modelteam/app \
  -v "$HOME/repos":/home/modelteam/repos \
  modelteam-docker > docker.log 2>&1 &
