# Use a base image with Python 3.12
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y git cron && \
    apt-get clean

RUN useradd -ms /bin/bash modelteam

# Set working directory and user
USER modelteam
WORKDIR /home/modelteam/app

# Copy files and install dependencies
COPY --chown=modelteam:modelteam . /home/modelteam/app

# Switch to root for cron setup
USER root

RUN echo "0 0 * * 0 su - modelteam -c 'cd /home/modelteam/app/ && python3 setup.py && python3 process_teams.py -r /home/modelteam/repos -c api_config.ini' >> cron.log 2>&1" > /etc/cron.d/weeklyjob

# Correct permissions and apply cron job for modelteam
RUN chmod 0644 /etc/cron.d/weeklyjob && \
    crontab /etc/cron.d/weeklyjob

RUN touch cron.log && chown modelteam:modelteam cron.log
RUN git config --global safe.directory '*'

VOLUME ["/home/modelteam/repos"]

CMD ["sh", "-c", "cron && tail -f cron.log"]

