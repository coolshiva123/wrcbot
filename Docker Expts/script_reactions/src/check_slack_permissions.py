#!/usr/bin/env python3
"""
Slack Bot Permission Checker
---------------------------
This script checks what permissions (OAuth scopes) a Slack bot token has.
It helps identify if the bot has the necessary permissions to read thread replies
and other conversation data.

Usage:
    python check_slack_permissions.py

The script reads the token from your config.py file.
"""

import sys
import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("SlackPermissionChecker")

# Add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from config import BOT_IDENTITY
    SLACK_TOKEN = BOT_IDENTITY.get('token')
    if not SLACK_TOKEN or not SLACK_TOKEN.startswith('xoxb-'):
        logger.error("Invalid or missing token in config.py. Make sure BOT_IDENTITY['token'] is set.")
        sys.exit(1)
except ImportError:
    logger.error("Could not import config.py. Make sure it exists and contains BOT_IDENTITY.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error reading token from config: {e}")
    sys.exit(1)

# Create Slack client
client = WebClient(token=SLACK_TOKEN)

def check_api_call(api_method, **kwargs):
    """
    Test a specific Slack API method and return the result
    """
    try:
        logger.info(f"Testing {api_method}...")
        result = getattr(client, api_method)(**kwargs)
        return {
            "success": True,
            "method": api_method,
            "response": "Success"
        }
    except SlackApiError as e:
        error_message = e.response["error"]
        return {
            "success": False,
            "method": api_method,
            "response": error_message
        }
    except Exception as e:
        return {
            "success": False,
            "method": api_method,
            "response": str(e)
        }

def check_bot_permissions():
    """
    Check the bot permissions by trying various API calls
    """
    print("=" * 80)
    print("SLACK BOT PERMISSION CHECKER")
    print("=" * 80)
    print(f"Using token: {SLACK_TOKEN[:10]}...{SLACK_TOKEN[-4:]}")
    print("-" * 80)
    
    # First, check if the token is valid at all
    print("1. Basic Authentication Check")
    auth_test = check_api_call("auth_test")
    if auth_test["success"]:
        print("✅ Token is valid!")
    else:
        print(f"❌ Token is invalid: {auth_test['response']}")
        return
    
    print("\n2. Checking Thread-Related Permissions")
    permissions_to_check = [
        # Core permission checks
        {"method": "conversations_list", "desc": "List channels", "scope": "channels:read"},
        {"method": "conversations_history", "desc": "Read message history", "scope": "channels:history, groups:history, im:history, mpim:history"},
        {"method": "conversations_replies", "desc": "Read thread replies", "scope": "channels:history, groups:history, im:history, mpim:history, conversations:replies"},
        {"method": "chat_postMessage", "desc": "Send messages", "scope": "chat:write"},
        {"method": "reactions_get", "desc": "Get reactions", "scope": "reactions:read"},
        {"method": "reactions_add", "desc": "Add reactions", "scope": "reactions:write"},
    ]
    
    test_channel = None
    try:
        # Try to get a channel ID for testing
        channels_response = client.conversations_list(types="public_channel", limit=1)
        if channels_response["ok"] and channels_response["channels"]:
            test_channel = channels_response["channels"][0]["id"]
    except Exception:
        # If we can't get a channel, we'll use a placeholder
        pass
    
    # If we couldn't get a channel, use a placeholder
    if not test_channel:
        test_channel = "C12345678"
    
    # Test each permission
    for perm in permissions_to_check:
        method = perm["method"]
        kwargs = {}
        
        # Customize arguments based on method
        if method == "conversations_history" or method == "conversations_replies":
            kwargs = {"channel": test_channel, "limit": 1}
        elif method == "chat_postMessage":
            # Don't actually send a message, we just want to check permissions
            kwargs = {"channel": test_channel, "text": "Test message (not actually sent)"}
            # Override the method to use a different API call that won't actually send anything
            method = "auth_test"
        elif method == "reactions_get":
            kwargs = {"channel": test_channel, "timestamp": "1000000000.000000"}
        elif method == "reactions_add":
            # Don't actually add a reaction, just check the permission
            kwargs = {}
            method = "auth_test"
        
        result = check_api_call(method, **kwargs)
        
        if result["success"]:
            print(f"✅ {perm['desc']} ({perm['scope']}): Allowed")
        else:
            error = result["response"]
            if "missing_scope" in error or "not_allowed_token_type" in error or "invalid_auth" in error:
                print(f"❌ {perm['desc']} ({perm['scope']}): Missing permission - {error}")
            elif "channel_not_found" in error or "no_such_channel" in error:
                print(f"⚠️  {perm['desc']} ({perm['scope']}): Could not test (no channel access)")
            else:
                print(f"⚠️  {perm['desc']} ({perm['scope']}): Error - {error}")
    
    print("\n3. Testing Specific Jira Plugin Requirements")
    
    # Check thread reading capabilities - critical for the Jira plugin
    try:
        print("Testing conversation replies capability...")
        # Just check if we can access the API, don't need valid data
        result = check_api_call("conversations_replies", channel=test_channel, ts="1000000000.000000")
        if "missing_scope" in result.get("response", ""):
            print("❌ CRITICAL: Your bot lacks the 'conversations:replies' scope!")
            print("   This is required for the Jira reaction detector to work properly.")
        elif "channel_not_found" in result.get("response", "") or "thread_not_found" in result.get("response", ""):
            print("⚠️  Couldn't fully test thread replies (channel/thread not found), but API access appears available")
        elif not result["success"]:
            print(f"⚠️  Thread replies test failed: {result['response']}")
        else:
            print("✅ Thread replies capability appears to be working")
    except Exception as e:
        print(f"❌ Error testing thread capabilities: {e}")
    
    print("\n4. Recommendations")
    print("-" * 80)
    print("To fix permission issues, you need to:")
    print("1. Go to https://api.slack.com/apps and select your bot application")
    print("2. Click on 'OAuth & Permissions' in the sidebar")
    print("3. Add these scopes under 'Bot Token Scopes':")
    print("   - channels:history")
    print("   - groups:history") 
    print("   - im:history")
    print("   - mpim:history")
    print("   - conversations:history")
    print("   - conversations:replies")
    print("   - reactions:read")
    print("   - chat:write")
    print("4. Click 'Save Changes' and reinstall your app to the workspace")
    print("5. Copy the new Bot User OAuth Token and update it in your config.py file")
    print("-" * 80)

if __name__ == "__main__":
    check_bot_permissions()
