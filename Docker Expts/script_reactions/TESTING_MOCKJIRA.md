# How to Test the MockJira Plugin

This document describes how to test the stateless MockJira plugin in your Slack workspace.

## 1. Create a Mock Jira Ticket
- **Post** a message in a Slack channel where the bot is present.
- **React** to the parent message (not a thread reply) with :jira:.
- **Expected:** The bot replies in a thread:
  > 📝 Created mock Jira ticket MOCKJIRA-xxxx for this message. Add replies in this thread to comment on the ticket.
- **Duplicate Test:** Remove and re-add :jira: to the same parent message.
- **Expected:** The bot replies:
  > ❗ Jira already exists for this message.
- **Edge:** React with :jira: on a thread reply.
- **Expected:** Nothing happens.

## 2. Add Comments to the Jira Ticket
- **Reply** in the thread with user-authored messages (not from the bot).
- **React** to a thread reply (not the parent) with :add2jira:.
- **Expected:**
  - If this is the first :add2jira: in the thread, the bot posts a Jira comment for each user-authored message in the thread up to and including the reacted message.
  - If there are previous :add2jira: reactions, only messages after the last such reaction (and up to the current one) are added as comments.
  - Bot-authored messages are ignored.
- **Edge:** React with :add2jira: on the parent message.
- **Expected:** Nothing happens.
- **Edge:** React with :add2jira: on a thread reply before a Jira ticket is created.
- **Expected:** The bot replies:
  > ❗ Create Jira first.

## 3. Put Jira In Review
- **React** to the parent message (the one with the Jira ticket) with :jirainreview:.
- **Expected:** The bot posts in the thread:
  > 🔄 MOCKJIRA-xxxx is now In Review (set by @user)

## 4. Resolve/Close the Jira Ticket
- **React** to the parent message with :jiracloseticket:.
- **Expected:** The bot posts in the thread:
  > ✅ MOCKJIRA-xxxx has been Resolved (set by @user)

## 5. General Edge Cases
- **Bot restarts:** All logic should still work, as ticket existence is determined by scanning the thread for the bot’s ticket creation message.
- **Multiple users:** Any user can trigger these actions; the bot should mention the user who performed the action.

## 6. What Should Not Happen
- No duplicate tickets for the same parent message.
- No comments added for bot-authored messages.
- No comments or status changes if the Jira ticket does not exist.

---

**Tip:**
Check the bot’s logs for any errors or debug info if something does not work as expected.
