import os

BACKEND = 'Slack'
BOT_IDENTITY = {
    'token': os.environ.get('SLACK_TOKEN')
}
BOT_DATA_DIR = '/data'
BOT_LOG_LEVEL = 'INFO'
BOT_ADMINS = ('awsterraform30',)