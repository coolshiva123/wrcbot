from errbot import BotPlugin, botcmd
import json
import random
import datetime
import re
import time

class JiraReactionHandler(BotPlugin):
    """
    Plugin to handle Jira-related reactions and respond with threaded messages.
    
    Supported Reactions:
    - :jira: - Creates mock Jira tickets on root messages only
    - :jirainreview: - Puts existing Jira tickets in review status on root messages only
    
    Features:
    - Duplicate prevention for ticket creation
    - Smart message type detection (root vs reply)
    - Status change tracking with timestamps
    - Comprehensive error handling and validation
    """

    def activate(self):
        super().activate()
        self.log.info("JiraReactionHandler plugin activated")

    def _make_slack_api_call_with_retry(self, slack_client, method_name, max_retries=3, **kwargs):
        """
        Make a Slack API call with retry logic for rate limiting and transient errors.
        
        Args:
            slack_client: The Slack client instance
            method_name: Name of the method to call (e.g., 'conversations_history')
            max_retries: Maximum number of retry attempts
            **kwargs: Arguments to pass to the API method
            
        Returns:
            API response or None if all retries failed
        """
        for attempt in range(max_retries + 1):
            try:
                # Get the method from the client
                method = getattr(slack_client, method_name)
                response = method(**kwargs)
                
                if response.get('ok'):
                    return response
                elif response.get('error') == 'ratelimited':
                    # Handle rate limiting
                    retry_after = response.get('headers', {}).get('Retry-After', 30)
                    if isinstance(retry_after, str):
                        try:
                            retry_after = int(retry_after)
                        except ValueError:
                            retry_after = 30
                    
                    self.log.warning(f"Rate limited on {method_name}, attempt {attempt + 1}/{max_retries + 1}. Waiting {retry_after} seconds...")
                    
                    if attempt < max_retries:
                        time.sleep(min(retry_after, 60))  # Cap wait time at 60 seconds
                        continue
                    else:
                        self.log.error(f"Rate limiting persisted after {max_retries} retries for {method_name}")
                        return None
                else:
                    # Other API errors
                    error_msg = response.get('error', 'Unknown error')
                    self.log.warning(f"Slack API error in {method_name}: {error_msg}")
                    return None
                    
            except Exception as e:
                self.log.warning(f"Exception in {method_name}, attempt {attempt + 1}/{max_retries + 1}: {e}")
                if attempt < max_retries:
                    # Exponential backoff for exceptions
                    wait_time = min(2 ** attempt, 30)
                    time.sleep(wait_time)
                    continue
                else:
                    self.log.error(f"All retries failed for {method_name}: {e}")
                    return None
        
        return None

    def callback_reaction_added(self, event):
        """
        Handle reaction_added events from Slack.
        This method is called by the SlackV3ReactionsExtension.
        """
        try:
            reaction = event.get('reaction')
            if reaction not in ['jira', 'jirainreview']:
                return False
            
            self.log.info(f"Handling {reaction} reaction: {json.dumps(event, indent=2)}")
            
            # Get event details
            user_id = event.get('user')
            item = event.get('item', {})
            channel = item.get('channel')
            timestamp = item.get('ts')
            
            if not all([user_id, channel, timestamp]):
                self.log.error("Missing required event data")
                return False
            
            # Determine if this is a root message or a reply
            is_reply = self._is_reply_message(channel, timestamp)
            
            # Handle different reactions
            if reaction == 'jira':
                response_text = self._handle_jira_create(channel, timestamp, is_reply)
            elif reaction == 'jirainreview':
                response_text = self._handle_jira_in_review(channel, timestamp, is_reply, user_id)
            
            thread_ts = timestamp  # Respond to the same message
            
            # Send threaded response
            self._send_threaded_response(channel, thread_ts, response_text)
            
            self.log.info(f"Successfully handled {reaction} reaction from user {user_id}")
            return True
            
        except Exception as e:
            self.log.error(f"Error handling {reaction} reaction: {e}")
            return False

    def _is_reply_message(self, channel, timestamp):
        """
        Try multiple approaches to determine if this is a reply message.
        Returns False as safe fallback if API calls fail.
        """
        try:
            # Access the Slack client through the bot backend
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available, assuming root message")
                return False  # Safe fallback: treat as root message
            
            # Method 1: Try to get the message using conversations.history with exact timestamp match
            self.log.info(f"Checking message at timestamp: {timestamp}")
            
            try:
                # Convert timestamp to float for comparison
                target_ts = float(timestamp)
                
                # Use retry wrapper for conversations.history
                response = self._make_slack_api_call_with_retry(
                    slack_client,
                    'conversations_history',
                    channel=channel,
                    latest=str(target_ts + 1),
                    oldest=str(target_ts - 1),
                    limit=10,
                    inclusive=True
                )
                
                if response and response.get('messages'):
                    for msg in response['messages']:
                        if msg.get('ts') == timestamp:
                            has_thread_ts = 'thread_ts' in msg and msg['thread_ts'] != msg['ts']
                            self.log.info(f"Message {timestamp} thread_ts check: {has_thread_ts}")
                            return has_thread_ts
                else:
                    self.log.warning(f"No messages returned from conversations.history for {timestamp}")
                    
            except Exception as e:
                self.log.warning(f"Method 1 failed in _is_reply_message: {e}")
            
            # Method 2: Try conversations.replies as a fallback
            try:
                self.log.info("Trying conversations.replies fallback...")
                
                # Use retry wrapper for conversations.replies
                thread_response = self._make_slack_api_call_with_retry(
                    slack_client,
                    'conversations_replies',
                    channel=channel,
                    ts=timestamp
                )
                
                if thread_response and thread_response.get('messages'):
                    messages = thread_response['messages']
                    # If we get back multiple messages and our timestamp isn't the first, it's a reply
                    if len(messages) > 1 and messages[0].get('ts') != timestamp:
                        self.log.info(f"Message {timestamp} identified as reply via conversations.replies")
                        return True
                    elif len(messages) == 1:
                        # Single message - could be root or reply, check for thread_ts
                        msg = messages[0]
                        has_thread_ts = 'thread_ts' in msg and msg['thread_ts'] != msg['ts']
                        self.log.info(f"Single message {timestamp} thread_ts check: {has_thread_ts}")
                        return has_thread_ts
                else:
                    self.log.warning(f"No messages returned from conversations.replies for {timestamp}")
                    
            except Exception as e:
                self.log.warning(f"Method 2 failed in _is_reply_message: {e}")
            
            # Safe fallback: if all API calls fail, assume it's a root message
            self.log.warning(f"All methods failed for message {timestamp}, assuming root message")
            return False
            
        except Exception as e:
            self.log.error(f"Critical error in _is_reply_message: {e}")
            return False  # Safe fallback

    def _send_threaded_response(self, channel, thread_ts, text):
        """
        Send a threaded response to the original message.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available for sending threaded response")
                return False
            
            # Use retry wrapper for chat.postMessage
            response = self._make_slack_api_call_with_retry(
                slack_client,
                'chat_postMessage',
                channel=channel,
                thread_ts=thread_ts,
                text=text,
                unfurl_links=False,
                unfurl_media=False
            )
            
            if response:
                self.log.info(f"Successfully sent threaded response to {thread_ts}")
                return True
            else:
                self.log.error(f"Failed to send threaded response to {thread_ts}")
                return False
                
        except Exception as e:
            self.log.error(f"Error sending threaded response: {e}")
            return False

    def _create_mock_jira_ticket(self, channel, timestamp):
        """
        Create a mock Jira ticket with 4-digit ticket number.
        In a real implementation, this would integrate with actual Jira API.
        """
        try:
            # Generate 4-digit random ticket number
            ticket_number = random.randint(1000, 9999)
            
            # Get the original message content for the Jira summary
            slack_client = getattr(self._bot, 'slack_web', None)
            message_content = "Slack Message"  # Default fallback
            
            if slack_client:
                try:
                    # Try to get the message content using retry wrapper
                    target_ts = float(timestamp)
                    response = self._make_slack_api_call_with_retry(
                        slack_client,
                        'conversations_history',
                        channel=channel,
                        latest=str(target_ts + 1),
                        oldest=str(target_ts - 1),
                        limit=10,
                        inclusive=True
                    )
                    
                    if response and response.get('messages'):
                        for msg in response['messages']:
                            if msg.get('ts') == timestamp:
                                message_content = msg.get('text', 'Slack Message')[:50]  # Truncate to 50 chars
                                if len(msg.get('text', '')) > 50:
                                    message_content += "..."
                                break
                except Exception as e:
                    self.log.warning(f"Could not fetch message content for Jira summary: {e}")
            
            # Mock Jira ticket data
            jira_ticket = {
                'key': f'PROJ-{ticket_number}',
                'summary': f'Slack Issue: {message_content}',
                'url': f'https://yourcompany.atlassian.net/browse/PROJ-{ticket_number}',
                'status': 'Open',
                'priority': 'Medium',
                'created_from': f'Slack message {timestamp}'
            }
            
            self.log.info(f"Mock Jira ticket created: {jira_ticket['key']}")
            return jira_ticket
            
        except Exception as e:
            self.log.error(f"Error creating mock Jira ticket: {e}")
            # Return fallback ticket
            return {
                'key': f'PROJ-{random.randint(1000, 9999)}',
                'summary': 'Slack Issue (Error retrieving details)',
                'url': 'https://yourcompany.atlassian.net/browse/PROJ-error',
                'status': 'Open',
                'priority': 'Medium',
                'created_from': f'Slack message {timestamp}'
            }

    def callback_reaction_removed(self, event):
        """
        Handle reaction_removed events. 
        Currently just logs the event, but could be extended for cleanup actions.
        """
        try:
            reaction = event.get('reaction')
            if reaction not in ['jira', 'jirainreview']:
                return False
                
            self.log.info(f"{reaction} reaction removed: {json.dumps(event, indent=2)}")
            return True
            
        except Exception as e:
            self.log.error(f"Error handling {reaction} reaction removal: {e}")
            return False

    def _check_if_already_processed(self, channel, timestamp):
        """
        Check if the bot has already created a Jira ticket for this message
        by looking for existing bot replies in the thread.
        This is completely stateless - relies only on message history.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available for duplicate check")
                return False
            
            # Get the bot's user ID to identify our own messages
            bot_user_id = self._get_bot_user_id()
            if not bot_user_id:
                self.log.warning("Could not determine bot user ID")
                return False
            
            self.log.info(f"Checking for existing Jira tickets by bot user {bot_user_id} for message {timestamp}")
            
            # Use retry wrapper for conversations.replies to check thread history
            thread_response = self._make_slack_api_call_with_retry(
                slack_client, 
                'conversations_replies',
                channel=channel,
                ts=timestamp
            )
            
            if thread_response and thread_response.get('messages'):
                messages = thread_response['messages']
                self.log.info(f"Found {len(messages)} messages in thread for timestamp {timestamp}")
                
                # Look through all replies for bot messages containing Jira ticket info
                for i, message in enumerate(thread_response['messages']):
                    # Skip the original message (index 0)
                    if message.get('ts') == timestamp:
                        self.log.info(f"Skipping root message at index {i}")
                        continue
                    
                    # Check if this is a bot message
                    message_user = message.get('user')
                    message_bot_id = message.get('bot_id')
                    message_text = message.get('text', '')
                    
                    # Check if it's from our bot (either by user_id or bot_id)
                    is_our_bot_message = (
                        message_user == bot_user_id or 
                        (message_bot_id and hasattr(self._bot, '_bot_id') and message_bot_id == self._bot._bot_id)
                    )
                    
                    self.log.info(f"Message {i}: user={message_user}, bot_id={message_bot_id}, is_our_bot={is_our_bot_message}, text_preview={message_text[:50]}...")
                    
                    # Only check bot messages for Jira ticket creation (same as _find_jira_ticket_in_thread)
                    if is_our_bot_message:
                        # Check if the message contains Jira ticket creation indicators
                        create_indicators = [
                            '✅ Jira ticket created:',
                            'PROJ-',
                            'Jira ticket created',
                            'ticket created:',
                            'browse/PROJ-'
                        ]
                        if any(indicator in message_text for indicator in create_indicators):
                            self.log.info(f"Found existing Jira ticket creation message: {message_text[:100]}...")
                            return True
            else:
                self.log.warning(f"No thread messages found or API call failed for {timestamp}")
            
            self.log.info(f"No existing Jira ticket found for message {timestamp}")
            return False
            
        except Exception as e:
            self.log.error(f"Error checking for duplicate Jira tickets: {e}")
            # On error, assume it's not processed to avoid blocking legitimate requests
            return False

    def _find_jira_ticket_in_thread(self, channel, thread_root):
        """
        Specifically look for Jira tickets in a thread by scanning bot messages only.
        Since Jira ticket creation is always done by the bot, we only need to check bot messages.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available for Jira ticket search")
                return False
            
            self.log.info(f"Scanning thread {thread_root} for existing Jira tickets (bot messages only)...")
            
            # Get all thread replies
            thread_response = self._make_slack_api_call_with_retry(
                slack_client, 
                'conversations_replies',
                channel=channel,
                ts=thread_root
            )
            
            if not thread_response or not thread_response.get('messages'):
                self.log.warning(f"No messages found in thread {thread_root}")
                return False
            
            messages = thread_response['messages']
            self.log.info(f"Scanning {len(messages)} messages in thread {thread_root}")
            
            # Get bot user ID for identifying our messages
            bot_user_id = self._get_bot_user_id()
            
            # Look through messages for bot messages with Jira ticket indicators
            for i, message in enumerate(messages):
                message_user = message.get('user')
                message_bot_id = message.get('bot_id')
                message_text = message.get('text', '')
                message_ts = message.get('ts', '')
                
                # Check if it's from our bot (either by user_id or bot_id)
                is_our_bot_message = (
                    message_user == bot_user_id or 
                    (message_bot_id and hasattr(self._bot, '_bot_id') and message_bot_id == self._bot._bot_id)
                )
                
                self.log.info(f"Message {i} (ts: {message_ts}): user={message_user}, bot_id={message_bot_id}, is_our_bot={is_our_bot_message}")
                
                # Only check bot messages for Jira ticket creation
                if is_our_bot_message:
                    self.log.info(f"Bot message {i} text preview: {message_text[:100]}...")
                    
                    # Look for Jira ticket creation indicators in bot messages
                    jira_indicators = [
                        '✅ Jira ticket created:',
                        'PROJ-',
                        'Jira ticket created',
                        'ticket created:',
                        'browse/PROJ-'
                    ]
                    
                    if any(indicator in message_text for indicator in jira_indicators):
                        self.log.info(f"Found Jira ticket indicator in bot message {i}: {message_text[:150]}...")
                        return True
            
            self.log.info(f"No Jira ticket found in thread {thread_root}")
            return False
            
        except Exception as e:
            self.log.error(f"Error scanning thread for Jira tickets: {e}")
            return False

    def _handle_jira_create(self, channel, timestamp, is_reply):
        """
        Handle :jira: reaction for ticket creation.
        """
        if is_reply:
            return "❌ You can't create Jira tickets on reply threads. Please react to the root message instead."
        
        # Check if we've already created a Jira ticket for this message
        already_processed = self._check_if_already_processed(channel, timestamp)
        
        if already_processed:
            return "ℹ️ Jira ticket already exists for this message. Check the thread above for details."
        else:
            # Create mock Jira ticket for root messages
            jira_ticket = self._create_mock_jira_ticket(channel, timestamp)
            
            # Record the creation time
            created_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            return f"✅ Jira ticket created: {jira_ticket['key']}\n📋 Summary: {jira_ticket['summary']}\n🔗 Link: {jira_ticket['url']}\n⏰ Created: {created_time}"

    def _get_thread_root(self, channel, timestamp):
        """
        Get the root timestamp of the thread for a given message.
        Returns the timestamp if it's already a root message.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available for thread root detection")
                return timestamp
            
            self.log.info(f"Getting thread root for message: {timestamp}")
            
            # First, try conversations.replies with the current timestamp
            # This will work if the timestamp is already a root, or if it's a reply
            try:
                thread_response = self._make_slack_api_call_with_retry(
                    slack_client,
                    'conversations_replies',
                    channel=channel,
                    ts=timestamp
                )
                
                if thread_response and thread_response.get('messages'):
                    messages = thread_response['messages']
                    if len(messages) > 0:
                        # The first message in replies is always the root
                        root_timestamp = messages[0].get('ts')
                        self.log.info(f"Found thread root via conversations.replies: {root_timestamp} for message: {timestamp}")
                        return root_timestamp
            except Exception as e:
                self.log.warning(f"conversations.replies method failed: {e}")
            
            # Fallback: Try to get the message details using conversations.history
            try:
                target_ts = float(timestamp)
                response = self._make_slack_api_call_with_retry(
                    slack_client,
                    'conversations_history',
                    channel=channel,
                    latest=str(target_ts + 1),
                    oldest=str(target_ts - 1),
                    limit=10,
                    inclusive=True
                )
                
                if response and response.get('messages'):
                    for msg in response['messages']:
                        if msg.get('ts') == timestamp:
                            # If this message has a thread_ts that's different from its own ts, 
                            # then thread_ts is the root
                            thread_ts = msg.get('thread_ts')
                            if thread_ts and thread_ts != timestamp:
                                self.log.info(f"Found thread root via conversations.history: {thread_ts} for message: {timestamp}")
                                return thread_ts
                            else:
                                self.log.info(f"Message {timestamp} is already the root message")
                                return timestamp  # This is already the root
                else:
                    self.log.warning(f"Could not fetch message details for {timestamp}")
            except Exception as e:
                self.log.warning(f"conversations.history fallback failed: {e}")
            
            # Final fallback: assume it's a root message
            self.log.warning(f"Could not determine thread root for {timestamp}, assuming it's the root")
            return timestamp
            
        except Exception as e:
            self.log.error(f"Error getting thread root: {e}")
            return timestamp  # Safe fallback

    def _get_bot_user_id(self):
        """
        Get the bot's user ID using various fallback methods.
        """
        try:
            # Try multiple methods to get bot user ID
            bot_user_id = getattr(self._bot, 'bot_identifier', None)
            if hasattr(bot_user_id, 'userid'):
                return bot_user_id.userid
            elif hasattr(self._bot, '_bot_user_id'):
                return self._bot._bot_user_id
            else:
                # Fallback: try to get from Slack API
                slack_client = getattr(self._bot, 'slack_web', None)
                if slack_client:
                    auth_response = self._make_slack_api_call_with_retry(slack_client, 'auth_test')
                    if auth_response:
                        return auth_response.get('user_id')
            
            self.log.warning("Could not determine bot user ID")
            return None
            
        except Exception as e:
            self.log.error(f"Error getting bot user ID: {e}")
            return None

    def _debug_thread_contents(self, channel, thread_root):
        """
        Debug function to dump all thread contents for troubleshooting.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available for debug")
                return
            
            self.log.info(f"=== DEBUG: Dumping all contents of thread {thread_root} ===")
            
            # Get all thread replies
            thread_response = self._make_slack_api_call_with_retry(
                slack_client, 
                'conversations_replies',
                channel=channel,
                ts=thread_root
            )
            
            if thread_response and thread_response.get('messages'):
                messages = thread_response['messages']
                self.log.info(f"Total messages in thread: {len(messages)}")
                
                for i, message in enumerate(messages):
                    msg_ts = message.get('ts', 'NO_TS')
                    msg_user = message.get('user', 'NO_USER')
                    msg_bot_id = message.get('bot_id', 'NO_BOT_ID')
                    msg_text = message.get('text', 'NO_TEXT')
                    msg_subtype = message.get('subtype', 'NO_SUBTYPE')
                    
                    self.log.info(f"Message {i}:")
                    self.log.info(f"  TS: {msg_ts}")
                    self.log.info(f"  User: {msg_user}")
                    self.log.info(f"  Bot ID: {msg_bot_id}")
                    self.log.info(f"  Subtype: {msg_subtype}")
                    self.log.info(f"  Text: {msg_text}")
                    self.log.info(f"  ---")
            else:
                self.log.warning("No messages found in thread or API call failed")
            
            self.log.info(f"=== END DEBUG DUMP ===")
            
        except Exception as e:
            self.log.error(f"Error in debug thread contents: {e}")

    def _format_replies_for_display(self, reply_messages):
        """
        Format thread replies for display in the Slack response.
        Creates a readable summary of all the replies.
        """
        try:
            if not reply_messages:
                return "No replies to display"
            
            formatted_lines = []
            for i, msg in enumerate(reply_messages):
                user_id = msg.get('user', 'Unknown User')
                text = msg.get('text', '')
                timestamp = msg.get('ts', '')
                
                # Convert timestamp to readable format
                try:
                    msg_time = datetime.datetime.fromtimestamp(float(timestamp)).strftime('%H:%M:%S')
                except:
                    msg_time = '??:??:??'
                
                # Determine if it's a bot or user message
                message_bot_id = msg.get('bot_id')
                if message_bot_id:
                    user_display = f"[BOT:{message_bot_id}]"
                else:
                    user_display = f"<@{user_id}>"
                
                # Truncate long messages
                display_text = text[:100]
                if len(text) > 100:
                    display_text += "..."
                
                formatted_lines.append(f"{i+1}. [{msg_time}] {user_display}: {display_text}")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            self.log.error(f"Error formatting replies for display: {e}")
            return "Error formatting replies"
    
    def _simple_thread_test(self, channel, thread_root):
        """
        Simple debug method to test thread reply fetching.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.error("No Slack client available")
                return []
            
            self.log.info(f"Simple test: fetching thread {thread_root} in channel {channel}")
            
            response = self._make_slack_api_call_with_retry(
                slack_client,
                'conversations_replies',
                channel=channel,
                ts=thread_root
            )
            
            if not response:
                self.log.error("No response from conversations.replies")
                return []
            
            messages = response.get('messages', [])
            self.log.info(f"Simple test found {len(messages)} total messages")
            
            # Log each message
            for i, msg in enumerate(messages):
                user = msg.get('user', 'unknown')
                text = msg.get('text', '')[:100] + '...' if len(msg.get('text', '')) > 100 else msg.get('text', '')
                ts = msg.get('ts')
                self.log.info(f"  Message {i}: user={user}, ts={ts}, text='{text}'")
            
            # Return only replies (skip root message)
            replies = messages[1:] if len(messages) > 1 else []
            self.log.info(f"Simple test returning {len(replies)} replies")
            return replies
            
        except Exception as e:
            self.log.error(f"Simple thread test failed: {e}")
            return []
    
    @botcmd
    def debug_thread(self, msg, args):
        """
        Debug command to test thread detection and reply collection.
        Usage: !debug_thread <channel_id> <thread_root_timestamp>
        """
        try:
            parts = args.strip().split()
            if len(parts) != 2:
                return "Usage: !debug_thread <channel_id> <thread_root_timestamp>"
            
            channel, thread_root = parts
            
            self.log.info(f"Debug thread command: channel={channel}, thread_root={thread_root}")
            
            # Test simple thread fetching
            replies = self._simple_thread_test(channel, thread_root)
            
            if not replies:
                return f"No replies found in thread {thread_root}"
            
            # Format the replies for display
            reply_summary = self._format_replies_for_display(replies[:5])  # Limit to first 5 for testing
            
            return f"Found {len(replies)} replies in thread:\n{reply_summary}"
            
        except Exception as e:
            self.log.error(f"Error in debug_thread command: {e}")
            return f"Error testing thread: {e}"
