from errbot import BotPlugin, botcmd
import logging
import random

class MockJira(BotPlugin):
    def activate(self):
        super().activate()
        # No persistence: do not initialize or use self['mock_jira_tickets']
        self.log.info("MockJira plugin activated (no persistence).")

    def _ticket_exists(self, channel, ts):
        # No persistence: always return False
        return False

    def _generate_jira_number(self):
        """Generate a random 4-6 digit Jira number as a string."""
        return str(random.randint(1000, 999999))

    def callback_reaction_added(self, event):
        """
        Handles :jira: and :add2jira: reactions.
        - :jira: on parent message: create ticket if not present (stateless, thread scan).
        - :add2jira: on thread reply: add as comment if ticket exists, else prompt to create Jira first.
        """
        reaction = event.get('reaction')
        item = event.get('item', {})
        channel = item.get('channel')
        message_ts = str(item.get('ts'))
        slack_client = getattr(self._bot, 'slack_web', None)
        user = event.get('user', 'unknown')
        if not slack_client or not channel or not message_ts:
            return False

        # Handle :jira: reaction (parent message)
        if reaction == 'jira':
            parent_ts = message_ts
            # Only allow on parent message (not thread reply)
            msg_info = slack_client.conversations_history(channel=channel, latest=parent_ts, inclusive=True, limit=1)
            messages = msg_info.get('messages', [])
            if not messages:
                return False
            message = messages[0]
            if 'thread_ts' in message and message['thread_ts'] != message['ts']:
                # This is a thread reply, do not create a ticket
                return False
            # Check thread for a bot-authored ticket creation message
            try:
                replies = slack_client.conversations_replies(channel=channel, ts=parent_ts)
                messages = replies.get('messages', [])
                for msg in messages:
                    # Check if message is from the bot and matches ticket creation pattern
                    if msg.get('bot_id') and 'Created mock Jira ticket' in msg.get('text', ''):
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=parent_ts,
                            text="❗ Jira already exists for this message."
                        )
                        self.log.info(f"Jira already exists for channel={channel}, ts={parent_ts} (found bot ticket message)")
                        return True
            except Exception as e:
                self.log.error(f"Failed to check thread for existing ticket: {e}")
            # Always use parent message's ts for ticket creation and duplicate check
            parent_ts = message_ts
            # Check if a ticket already exists for this parent message
            if self._ticket_exists(channel, parent_ts):
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=parent_ts,
                    text="❗ Jira already exists for this message."
                )
                self.log.info(f"Jira already exists for channel={channel}, ts={parent_ts}")
                return True
            # Fetch the message to check if it's a parent (not a thread reply)
            try:
                msg_info = slack_client.conversations_history(channel=channel, latest=parent_ts, inclusive=True, limit=1)
                messages = msg_info.get('messages', [])
                if not messages:
                    return False
                message = messages[0]
                if 'thread_ts' in message and message['thread_ts'] != message['ts']:
                    return False
                jira_number = self._generate_jira_number()
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=parent_ts,
                    text=f"📝 Created mock Jira ticket *MOCKJIRA-{jira_number}* for this message. Add replies in this thread to comment on the ticket."
                )
                return True
            except Exception as e:
                self.log.error(f"Failed to create mock Jira ticket: {e}")
                return False

        # Handle :add2jira: reaction (thread reply)
        if reaction == 'add2jira':
            try:
                # Get the message being reacted to
                item = event.get('item', {})
                channel = item.get('channel')
                message_ts = str(item.get('ts'))
                slack_client = getattr(self._bot, 'slack_web', None)
                if not slack_client or not channel or not message_ts:
                    return False
                msg_info = slack_client.conversations_history(channel=channel, latest=message_ts, inclusive=True, limit=1)
                messages = msg_info.get('messages', [])
                if not messages:
                    return False
                reacted_msg = messages[0]
                parent_ts = reacted_msg.get('thread_ts')
                if not parent_ts or parent_ts == message_ts:
                    # Not a thread reply (i.e., this is a parent message), ignore
                    return False
                # Scan thread for bot ticket creation message
                replies = slack_client.conversations_replies(channel=channel, ts=parent_ts)
                thread_messages = replies.get('messages', [])
                ticket_exists = False
                for msg in thread_messages:
                    if msg.get('bot_id') and 'Created mock Jira ticket' in msg.get('text', ''):
                        ticket_exists = True
                        break
                if not ticket_exists:
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=parent_ts,
                        text="❗ Create Jira first."
                    )
                    return True
                # Find all :add2jira: reactions in the thread
                add2jira_ts_list = []
                for msg in thread_messages:
                    reactions = msg.get('reactions', [])
                    for r in reactions:
                        if r.get('name') == 'add2jira':
                            add2jira_ts_list.append(msg['ts'])
                # Find the last :add2jira: ts before or at the current message
                last_add2jira_ts = None
                for ts in add2jira_ts_list:
                    if ts < message_ts:
                        last_add2jira_ts = ts
                # Collect user-authored messages after last :add2jira: (or all up to current if first)
                comments_to_add = []
                for msg in thread_messages:
                    # Ignore bot messages
                    if msg.get('bot_id'):
                        continue
                    # Only consider messages after last :add2jira: (or all up to current if first)
                    if last_add2jira_ts:
                        if msg['ts'] > last_add2jira_ts and msg['ts'] <= message_ts:
                            comments_to_add.append(msg)
                    else:
                        if msg['ts'] <= message_ts:
                            comments_to_add.append(msg)
                # Post each comment as a Jira comment
                for cmsg in comments_to_add:
                    user = cmsg.get('user', 'unknown')
                    text = cmsg.get('text', '')
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=parent_ts,
                        text=f"💬 *Jira comment by <@{user}>*: {text}"
                    )
                    self.log.info(f"Added Jira comment for parent_ts={parent_ts}: {text}")
                return True
            except Exception as e:
                self.log.error(f"Failed to add Jira comment: {e}")
                return False
        # Handle :jirainreview: reaction (parent message)
        if reaction == 'jirainreview':
            parent_ts = message_ts
            # Only allow on parent message (not thread reply)
            msg_info = slack_client.conversations_history(channel=channel, latest=parent_ts, inclusive=True, limit=1)
            messages = msg_info.get('messages', [])
            if not messages:
                return False
            message = messages[0]
            if 'thread_ts' in message and message['thread_ts'] != message['ts']:
                return False
            self.put_jira_in_review(channel, parent_ts, user)
            return True
        # Handle :jiracloseticket: reaction (parent message)
        if reaction == 'jiracloseticket':
            parent_ts = message_ts
            # Only allow on parent message (not thread reply)
            msg_info = slack_client.conversations_history(channel=channel, latest=parent_ts, inclusive=True, limit=1)
            messages = msg_info.get('messages', [])
            if not messages:
                return False
            message = messages[0]
            if 'thread_ts' in message and message['thread_ts'] != message['ts']:
                return False
            self.resolve_jira(channel, parent_ts, user)
            return True
        return False

    def callback_message(self, msg):
        # No-op: comments are only added via :add2jira: reaction in callback_reaction_added
        pass

    def _find_jira_ticket_number(self, thread_messages):
        """Extract the Jira ticket number from the bot's ticket creation message in the thread."""
        for msg in thread_messages:
            if msg.get('bot_id') and 'Created mock Jira ticket' in msg.get('text', ''):
                # Extract ticket number from message text
                import re
                m = re.search(r'MOCKJIRA-(\d+)', msg.get('text', ''))
                if m:
                    return m.group(0)
        return None

    def put_jira_in_review(self, channel, parent_ts, user):
        """Post a message in the thread marking the Jira as In Review."""
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            return
        replies = slack_client.conversations_replies(channel=channel, ts=parent_ts)
        thread_messages = replies.get('messages', [])
        ticket_number = self._find_jira_ticket_number(thread_messages)
        if ticket_number:
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=parent_ts,
                text=f"🔄 {ticket_number} is now *In Review* (set by <@{user}>)"
            )

    def resolve_jira(self, channel, parent_ts, user):
        """Post a message in the thread marking the Jira as Resolved."""
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            return
        replies = slack_client.conversations_replies(channel=channel, ts=parent_ts)
        thread_messages = replies.get('messages', [])
        ticket_number = self._find_jira_ticket_number(thread_messages)
        if ticket_number:
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=parent_ts,
                text=f"✅ {ticket_number} has been *Resolved* (set by <@{user}>)"
            )

    def add_jira_comment(self, channel, parent_ts, user, comment):
        """Add a comment to the Jira ticket (posts in thread)."""
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            return
        replies = slack_client.conversations_replies(channel=channel, ts=parent_ts)
        thread_messages = replies.get('messages', [])
        ticket_number = self._find_jira_ticket_number(thread_messages)
        if ticket_number:
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=parent_ts,
                text=f"💬 *Jira comment on {ticket_number} by <@{user}>*: {comment}"
            )
