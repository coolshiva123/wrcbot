# Jira Reaction Detector - Troubleshooting Guide

## Plugin Overview

The Jira Reaction Detector plugin handles Slack emoji reactions to simulate Jira ticket workflows:

- `:jira:` - Creates mock MOCK-OPS tickets (root messages only)
- `:jirainreview:` - Moves tickets to review status (root messages only)  
- `:jiracloseticket:` - Closes existing tickets (root messages only)
- `:add2jira:` - Echoes back message content (reply messages only)

## Recent Fixes & Improvements

### v2.1 - Enhanced Reply Detection (Latest)

**Problem Solved:** The bot was incorrectly identifying replies as root messages, causing `:add2jira:` to not work on replies.

**Key Changes:**
- Simplified reply detection logic to focus on the `thread_ts` field
- Enhanced debugging with emoji indicators in logs
- Added test script to verify message structure logic
- Improved error handling and user feedback

**How Reply Detection Works:**
1. **Root Messages:** Either have no `thread_ts` field OR `thread_ts` equals the message's own `ts`
2. **Reply Messages:** Always have `thread_ts` that differs from the message's `ts`

### Debugging Features

**Enhanced Logging:** Look for these emoji indicators in the logs:
- 🔍 Processing reaction
- ✅ Reply detected / ❌ Root message detected  
- 📨 Message retrieval attempts
- 🎯 Target message found
- 💥 Errors
- 🔒 Permission issues

**Debug Script:** Run `test_reply_detection.py` to understand message structures:
```bash
cd /path/to/src/
python3 test_reply_detection.py
```

## Common Issues & Solutions

### Issue 1: `:add2jira:` Not Working on Replies

**Symptoms:**
- Using `:add2jira:` on a reply message shows "No action needed on root message"
- Bot logs show "❌ ROOT MESSAGE" for what should be a reply

**Solution:**
Check the bot logs for the reply detection process. The simplified logic should now correctly identify replies based on `thread_ts` vs `ts` comparison.

### Issue 2: Permission Errors

**Symptoms:**
- Messages about missing OAuth scopes
- "Permission error: Missing required scopes" in responses

**Solution:**
1. Run the permission checker: `python3 check_slack_permissions.py`
2. Follow the steps in `PERMISSION_CHECK_README.md`
3. Ensure these scopes are enabled:
   - `channels:history`
   - `conversations:history` 
   - `conversations:replies`
   - `reactions:read`

### Issue 3: Duplicate Tickets

**Symptoms:**
- Multiple MOCK-OPS tickets for the same root message

**Solution:**
- The plugin now prevents duplicates by tracking processed messages
- If you see this message: "MOCK-OPS ticket already exists for this message"

### Issue 4: Bot Not Responding to Reactions

**Symptoms:**
- No response when adding supported reactions

**Troubleshooting Steps:**
1. Check bot is running and connected to Slack
2. Verify SlackV3ReactionsExtension is loaded
3. Check bot has permission to read reactions
4. Look for error messages in bot logs

## Testing Your Setup

### Quick Test Sequence:

1. **Test Root Message Detection:**
   - Post a new message in a channel
   - Add `:jira:` reaction → Should create MOCK-OPS ticket
   - Add `:add2jira:` reaction → Should say "No action needed on root message"

2. **Test Reply Detection:**
   - Reply to the message from step 1
   - Add `:add2jira:` reaction → Should echo back the reply content
   - Add `:jira:` reaction → Should say "No Action triggered - :jira: will work in root messages only"

3. **Test Status Changes:**
   - On the original root message, add `:jirainreview:` → Should move ticket to review
   - Add `:jiracloseticket:` → Should close the ticket

## Log Analysis Tips

**Look for these log patterns to understand what's happening:**

```
🔍 Processing add2jira reaction on message 1234567890.123456
🎯 Reply detection result: True
✅ Confirmed as REPLY - calling _summarize_thread_replies
📨 About to call _get_message_content
🎯 FOUND TARGET MESSAGE!
✅ Successfully retrieved message content: Hello, this is a test reply...
```

vs

```
🔍 Processing add2jira reaction on message 1234567890.123456  
🎯 Reply detection result: False
❌ Confirmed as ROOT - no action taken
```

## File Locations

- Main plugin: `src/plugins/jira_reaction_detector.py`
- Plugin config: `src/plugins/jira_reaction_detector.plug`
- Permission checker: `src/check_slack_permissions.py`
- Test script: `src/test_reply_detection.py`
- Permission guide: `src/PERMISSION_CHECK_README.md`

## Support

If issues persist after following this guide:

1. Enable debug logging in your bot configuration
2. Capture the full log output for a failed reaction
3. Run the test script to verify message structure understanding
4. Check the permission checker results

The enhanced debugging should now clearly show whether messages are correctly identified as root vs reply messages.
