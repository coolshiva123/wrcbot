# Errbot Configuration

import logging

# Bot identity
BOT_DATA_DIR = 'data'
BOT_EXTRA_PLUGIN_DIR = 'src/plugins'

# Slack connection settings (use environment variables in production)
BACKEND = 'Slack'
BOT_PREFIX = '!'
BOT_ADMINS = ['@youradmin']  # Replace with your Slack user ID
BOT_IDENTITY = {
    'token': 'your-slack-bot-token',
    'signing_secret': 'your-slack-signing-secret',
    'app_token': 'your-slack-app-token'
}

# Set logging level
BOT_LOG_LEVEL = logging.INFO

# Confluence settings for RAG
CONFLUENCE_URL = "https://your-confluence-instance.atlassian.net"
CONFLUENCE_USERNAME = "your-email@example.com"
CONFLUENCE_PASSWORD = "your-api-token"  # Use an API token, not your password

# LLM Settings
OLLAMA_URL = "http://ol:11434"  # URL to your Ollama service
OLLAMA_MODEL = "llama3"  # The model to use
