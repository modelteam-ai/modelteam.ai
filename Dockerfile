# Use a base image with Python 3.12
FROM python:3.12-slim

# Install git and cron
RUN apt-get update && \
    apt-get install -y git cron && \
    apt-get clean

# Create non-root user 'modelteam'
RUN useradd -ms /bin/bash modelteam

# Set working directory and user
USER modelteam
WORKDIR /home/modelteam/app

# Copy files and install dependencies
COPY --chown=modelteam:modelteam . /home/modelteam/app
RUN python setup.py

# Switch to root for cron setup
USER root

# Add cron job (escape inner quotes properly)
RUN echo "0 0 * * 0 su - modelteam -c 'python3 /home/modelteam/app/gen_team_git_stats.py -r /home/modelteam/repos -t modelteam' >> /var/log/cron.log 2>&1" > /etc/cron.d/weeklyjob

# Correct permissions and apply cron job for modelteam
RUN chmod 0644 /etc/cron.d/weeklyjob && \
    crontab /etc/cron.d/weeklyjob

# Create log file with appropriate permissions
RUN touch /var/log/cron.log && chown modelteam:modelteam /var/log/cron.log

# Declare volume for external mount
VOLUME ["/home/modelteam/repos"]

# Start cron and tail the log
CMD ["sh", "-c", "cron && tail -f /var/log/cron.log"]

