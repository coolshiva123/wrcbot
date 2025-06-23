Errbot and its plugins are not yet fully compatible with Python 3.13’s new SQLite/threading behavior.
Downgrade to Python 3.12 (recommended for now):

brew install python@3.12
python3.12 -m venv errbot-env
source errbot-env/bin/activate
pip install errbot errbot-backend-slackv3
errbot --init
Configure Config.py
start errbot -c config.py




