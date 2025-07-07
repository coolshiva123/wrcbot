# MockJira Plugin: Channel and User Restriction Strategy

This document describes the approach for restricting where the MockJira plugin can operate and who can perform privileged actions (such as putting a Jira ticket in review or resolving it).

## 1. Channel Restrictions

**Goal:** Only allow the bot to operate in a specific set of channels.

**How to Implement:**
- Maintain a list of allowed channel IDs or names in the plugin configuration (e.g., `ALLOWED_CHANNELS = ['C12345', 'C67890']`).
- In every event handler (e.g., `callback_reaction_added`), check if the event’s channel is in `ALLOWED_CHANNELS`.
- If not, ignore the event.

**Management:**
- Allow admins to update the allowed channel list via a command or config file.
- Optionally, log or notify if the bot is used in a disallowed channel.

## 2. User Restrictions for Jira Review/Close

**Goal:** Only allow certain users to use :jirainreview: and :jiracloseticket: reactions.

**How to Implement:**
- Maintain a list of allowed user IDs or Slack usernames (e.g., `JIRA_ADMIN_USERS = ['U12345', 'U67890']`).
- When handling :jirainreview: or :jiracloseticket: reactions, check if the event’s user is in `JIRA_ADMIN_USERS`.
- If not, ignore the event and optionally notify the user they lack permission.

**Management:**
- Allow bot admins to update the allowed user list via a command or config file.
- Optionally, allow channel-specific admin lists.

## 3. Where to Reference These Restrictions
- In every relevant event handler (e.g., `callback_reaction_added`, `callback_message`, or command handler), check the channel and user against these lists before taking action.
- Example (pseudocode):
  ```python
  def callback_reaction_added(self, event):
      channel = event['item']['channel']
      user = event['user']
      if channel not in ALLOWED_CHANNELS:
          return False
      if event['reaction'] in ['jirainreview', 'jiracloseticket'] and user not in JIRA_ADMIN_USERS:
          return False
      # ...rest of your logic...
  ```

## 4. Documentation and Maintenance
- Document the allowed channels and user permissions in your project’s README or a dedicated admin guide.
- Make it clear to users which channels and users are authorized.
- Optionally, provide admin commands for runtime updates.

---

**Summary Table:**

| Feature                | Restriction Type | How to Enforce                |
|------------------------|------------------|-------------------------------|
| Bot usage              | Channel          | Check channel in handler      |
| Jira review/close      | User             | Check user in handler         |
| Admin config commands  | User             | Restrict to bot admins        |

---

This approach ensures that the MockJira plugin only operates where and for whom it is intended, improving security and reducing noise in your Slack workspace.
