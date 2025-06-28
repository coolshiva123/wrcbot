FROM python:3.11-bullseye

# Set the working directory
WORKDIR /errbot

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY src/ ./src/

# Command to run the bot
CMD ["errbot", "-c", "src/config.py"]

# Keeps the container running in the background
#CMD ["tail", "-f", "/dev/null"]