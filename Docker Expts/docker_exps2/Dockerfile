FROM python:3.11-bullseye
RUN mkdir -p /errbot/data; apt-get update && apt-get install -y \
    net-tools \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /errbot
# Copy the requirements file
COPY requirements.txt ./
# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy the application code
COPY src/ ./src/
# Expose the port for Errbot
EXPOSE 3141
# Command to run the bot
CMD ["errbot", "-c", "src/config.py"]
