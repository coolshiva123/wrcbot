FROM python:3.11-slim

RUN pip install errbot errbot-backend-slack

COPY config.py /errbot/config.py

RUN mkdir -p /data

WORKDIR /errbot

CMD ["errbot", "-c", "config.py"]