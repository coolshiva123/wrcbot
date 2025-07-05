BACKEND='SlackV3'
BOT_DATA_DIR = '/errbot/data'
BOT_EXTRA_PLUGIN_DIR = '/errbot/src/plugins'
BOT_LOG_FILE = '/errbot/errbot.log'
BOT_EXTRA_BACKEND_DIR = '/opt/errbot/backend'
BOT_LOG_LEVEL = 'DEBUG'
BOT_ADMINS = ('@awsterraform30',)  # Replace with your username if needed
BOT_IDENTITY = {
    'token': '',
    'signing_secret': '',
    'app_token': ''  # Replace with your bot's app token
}
BOT_PREFIX = '<@U0922H0H00N>'  # Replace with your bot's user ID
BOT_EXTRA_STORAGE_PLUGINS_DIR='/errbot/src/storageplugins/'
STORAGE = 'Redis'
STORAGE_CONFIG = {
     'host': 'localhost',
     'port': 6379,
     'db': 0,
}