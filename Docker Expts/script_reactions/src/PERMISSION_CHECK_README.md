# Slack Bot Permission Checker Tool

This script checks the permissions of your Slack bot token to help diagnose permission-related issues.

## What It Checks:
- Basic authentication
- Access to channels
- Ability to read message history
- Ability to read thread replies
- Permission to send messages
- Permission to read and add reactions

## How to Run:

```bash
cd /Users/shivaramakrishnan.g/codebases/mypersonal/wrcbot/Docker Expts/script_reactions/src/
python check_slack_permissions.py
```

## How to Fix Permission Issues:

If the script identifies missing permissions, follow these steps:

1. Go to https://api.slack.com/apps and select your bot application
2. Click on 'OAuth & Permissions' in the sidebar
3. Under 'Bot Token Scopes', add the following scopes:
   - channels:history
   - groups:history
   - im:history
   - mpim:history
   - conversations:history
   - conversations:replies
   - reactions:read
   - chat:write
4. Click 'Save Changes' and reinstall your app to your workspace
5. Copy the new Bot User OAuth Token and update it in your config.py file

## Required Scopes for Thread Reading

The most important scopes for the Jira Reaction Detector are:
- `conversations:history` - Allows reading message history
- `conversations:replies` - Allows reading thread replies
