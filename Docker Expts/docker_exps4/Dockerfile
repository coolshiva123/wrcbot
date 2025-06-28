FROM python:3.12-bullseye
WORKDIR /errbot
RUN mkdir -p ./data;mkdir -p./plugins; apt-get update && apt-get install -y \
    net-tools \
    vim \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./ 
COPY config.py ./
COPY plugins ./plugins/
RUN pip install --no-cache-dir -r requirements.txt
