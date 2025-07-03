import os

BACKEND = 'SlackV3'
BOT_DATA_DIR = '/errbot/data'
BOT_EXTRA_PLUGIN_DIR = '/errbot/src/plugins'
BOT_LOG_FILE = '/errbot/errbot.log'
BOT_EXTRA_BACKEND_DIR = '/opt/errbot/backend'
BOT_LOG_LEVEL = 'DEBUG'

# Read sensitive configs from environment variables
BOT_ADMINS = tuple(admin.strip() for admin in os.getenv('BOT_ADMINS', '').split(',') if admin.strip())
BOT_IDENTITY = {
    'token': os.getenv('SLACK_TOKEN', ''),
    'signing_secret': os.getenv('SLACK_SIGNING_SECRET', ''),
    'app_token': os.getenv('SLACK_APP_TOKEN', '')
}
BOT_PREFIX = os.getenv('BOT_PREFIX', '!')
