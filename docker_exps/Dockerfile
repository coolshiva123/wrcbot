FROM python:3.11-slim

# Install Errbot
RUN pip install errbot[slack]

# Copy your config.py and (optionally) plugins
COPY config.py /errbot/config.py

WORKDIR /errbot

# Set the Slack token as an environment variable (for testing)
# ENV SLACK_TOKEN=your-slack-token

CMD ["errbot", "-c", "config.py"]