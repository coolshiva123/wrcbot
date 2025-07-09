from errbot import BotPlugin, botcmd
import json
import datetime
import time
import random

class JiraReactionDetector(BotPlugin):
    """
    Plugin to handle Jira-related reactions.
    
    Supported Reactions:
    - :jira: - Creates mock MOCK-OPS tickets on root messages only
    - :jirainreview: - Puts existing tickets in review status on root messages only
    - :jiracloseticket: - Closes existing tickets on root messages only
    
    Features:
    - Strict message type detection (root vs reply)
    - Duplicate ticket prevention
    - Status change tracking with timestamps
    - Comprehensive error handling and logging
    """

    def activate(self):
        super().activate()
        self.log.info("JiraReactionDetector plugin activated")

    def _make_slack_api_call_with_retry(self, slack_client, method_name, max_retries=3, **kwargs):
        """
        Make a Slack API call with retry logic for rate limiting and transient errors.
        """
        for attempt in range(max_retries + 1):
            try:
                method = getattr(slack_client, method_name)
                response = method(**kwargs)
                
                if response.get('ok'):
                    return response
                elif response.get('error') == 'ratelimited':
                    retry_after = response.get('headers', {}).get('Retry-After', 30)
                    try:
                        retry_after = int(retry_after)
                    except Exception:
                        retry_after = 30
                    
                    self.log.warning(f"Rate limited on {method_name}, attempt {attempt + 1}/{max_retries + 1}. Waiting {retry_after} seconds...")
                    
                    if attempt < max_retries:
                        time.sleep(min(retry_after, 60))
                        continue
                    else:
                        self.log.error(f"Rate limiting persisted after {max_retries} retries for {method_name}")
                        return None
                else:
                    error_msg = response.get('error', 'Unknown error')
                    self.log.warning(f"Slack API error in {method_name}: {error_msg}")
                    return None
                    
            except Exception as e:
                self.log.warning(f"Exception in {method_name}, attempt {attempt + 1}/{max_retries + 1}: {e}")
                if attempt < max_retries:
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
            if reaction not in ['jira', 'jirainreview', 'jiracloseticket']:
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
                if is_reply:
                    response_text = "No Action triggered - :jira: will work in root messages only."
                else:
                    # Check if we've already created a ticket for this message
                    already_processed = self._check_if_already_processed(channel, timestamp)
                    
                    if already_processed:
                        response_text = "ℹ️ MOCK-OPS ticket already exists for this message. Check the thread above for details."
                    else:
                        # Create mock ticket for root messages
                        jira_ticket = self._create_mock_ops_ticket(channel, timestamp)
                        response_text = f"✅ MOCK-OPS ticket created: {jira_ticket['key']}\n📋 Summary: {jira_ticket['summary']}\n🔗 Link: {jira_ticket['url']}\n⏰ Created: {jira_ticket['created_time']}"
            elif reaction == 'jirainreview':
                if is_reply:
                    response_text = "No Action triggered - :jirainreview: will work in root messages only."
                else:
                    response_text = self._handle_jira_in_review(channel, timestamp, user_id)
            elif reaction == 'jiracloseticket':
                if is_reply:
                    response_text = "No Action triggered - :jiracloseticket: will work in root messages only."
                else:
                    response_text = self._handle_jira_close_ticket(channel, timestamp, user_id)
            
            # Send threaded response
            self._send_threaded_response(channel, timestamp, response_text)
            
            self.log.info(f"Successfully handled {reaction} reaction from user {user_id}")
            return True
            
        except Exception as e:
            self.log.error(f"Error handling {reaction} reaction: {e}")
            return False

    def _is_reply_message(self, channel, timestamp):
        """
        Use multiple strict approaches to determine if this is a reply message.
        """
        try:
            # Access the Slack client through the bot backend
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available, assuming root message")
                return False
            
            self.log.info(f"Checking message type for timestamp: {timestamp}")
            
            # Method 1: conversations_history with exact timestamp match
            try:
                target_ts = float(timestamp)
                
                response = self._make_slack_api_call_with_retry(
                    slack_client,
                    'conversations_history',
                    channel=channel,
                    latest=str(target_ts + 1),  # Time window to ensure we get the message
                    oldest=str(target_ts - 1),
                    limit=10,
                    inclusive=True
                )
                
                if response and response.get('messages'):
                    for msg in response['messages']:
                        if msg.get('ts') == timestamp:
                            # If message has thread_ts and it's different from its own ts,
                            # then it's a reply
                            has_thread_ts = 'thread_ts' in msg and msg['thread_ts'] != msg['ts']
                            self.log.info(f"Method 1 result: Message {timestamp} is_reply={has_thread_ts}")
                            return has_thread_ts
                else:
                    self.log.warning(f"Method 1: No messages returned from conversations_history for {timestamp}")
                    
            except Exception as e:
                self.log.warning(f"Method 1 failed in _is_reply_message: {e}")
            
            # Method 2: conversations_replies as a fallback
            try:
                self.log.info("Trying conversations_replies fallback...")
                
                thread_response = self._make_slack_api_call_with_retry(
                    slack_client,
                    'conversations_replies',
                    channel=channel,
                    ts=timestamp
                )
                
                if thread_response and thread_response.get('messages'):
                    messages = thread_response['messages']
                    
                    # If we get back multiple messages and our timestamp isn't the first,
                    # it's definitely a reply
                    if len(messages) > 1:
                        first_msg_ts = messages[0].get('ts')
                        if first_msg_ts != timestamp:
                            self.log.info(f"Method 2 result: Message {timestamp} is a reply (not first in thread)")
                            return True
                    
                    # Even if we're the only message or the first message,
                    # check for thread_ts
                    for msg in messages:
                        if msg.get('ts') == timestamp:
                            has_thread_ts = 'thread_ts' in msg and msg['thread_ts'] != msg['ts']
                            self.log.info(f"Method 2 result: Message {timestamp} is_reply={has_thread_ts}")
                            return has_thread_ts
                else:
                    self.log.warning(f"Method 2: No messages returned from conversations_replies for {timestamp}")
                    
            except Exception as e:
                self.log.warning(f"Method 2 failed in _is_reply_message: {e}")
            
            # Method 3: Last resort - try to get the parent message
            try:
                self.log.info("Trying to find parent message as last resort...")
                
                # If this is a reply, we should be able to find its parent
                # by looking at the thread_ts attribute
                thread_response = self._make_slack_api_call_with_retry(
                    slack_client,
                    'conversations_history',
                    channel=channel,
                    latest=str(float(timestamp) + 0.0001),
                    inclusive=True,
                    limit=5
                )
                
                if thread_response and thread_response.get('messages'):
                    for msg in thread_response['messages']:
                        if msg.get('ts') == timestamp:
                            # Final check: if this message has thread_ts and it's different
                            # from its own ts, it's a reply
                            thread_ts = msg.get('thread_ts')
                            if thread_ts and thread_ts != timestamp:
                                self.log.info(f"Method 3 result: Message {timestamp} is a reply to {thread_ts}")
                                return True
                            break
                    
                    self.log.info(f"Method 3 result: Message {timestamp} is a root message")
                    return False
                else:
                    self.log.warning(f"Method 3: Could not retrieve message {timestamp}")
                    
            except Exception as e:
                self.log.warning(f"Method 3 failed in _is_reply_message: {e}")
            
            # If all methods fail, assume it's a root message
            self.log.warning(f"All methods failed for message {timestamp}, assuming root message")
            return False
            
        except Exception as e:
            self.log.error(f"Critical error in _is_reply_message: {e}")
            return False

    def _send_threaded_response(self, channel, thread_ts, text):
        """
        Send a threaded response to the original message.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available for sending threaded response")
                return False
            
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
    
    def _create_mock_ops_ticket(self, channel, timestamp):
        """
        Create a mock MOCK-OPS ticket with 6-digit ticket number.
        """
        try:
            # Generate 6-digit random ticket number
            ticket_number = random.randint(100000, 999999)
            
            # Get the original message content for the Jira summary
            slack_client = getattr(self._bot, 'slack_web', None)
            message_content = "Slack Message"  # Default fallback
            
            if slack_client:
                try:
                    # Try to get the message content
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
                    self.log.warning(f"Could not fetch message content for MOCK-OPS summary: {e}")
            
            # Mock Jira ticket data
            jira_ticket = {
                'key': f'MOCK-OPS-{ticket_number}',
                'summary': f'Slack Issue: {message_content}',
                'url': f'https://yourcompany.atlassian.net/browse/MOCK-OPS-{ticket_number}',
                'status': 'Open',
                'priority': 'Medium',
                'created_from': f'Slack message {timestamp}',
                'created_time': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
            
            self.log.info(f"Mock MOCK-OPS ticket created: {jira_ticket['key']}")
            return jira_ticket
            
        except Exception as e:
            self.log.error(f"Error creating mock MOCK-OPS ticket: {e}")
            # Return fallback ticket
            return {
                'key': f'MOCK-OPS-{random.randint(100000, 999999)}',
                'summary': 'Slack Issue (Error retrieving details)',
                'url': 'https://yourcompany.atlassian.net/browse/MOCK-OPS-error',
                'status': 'Open',
                'priority': 'Medium',
                'created_from': f'Slack message {timestamp}',
                'created_time': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
    
    def _check_if_already_processed(self, channel, timestamp):
        """
        Check if a ticket has already been created for this message
        by looking for existing bot replies in the thread.
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
            
            self.log.info(f"Checking for existing MOCK-OPS tickets by bot user {bot_user_id} for message {timestamp}")
            
            # Get all thread replies
            thread_response = self._make_slack_api_call_with_retry(
                slack_client, 
                'conversations_replies',
                channel=channel,
                ts=timestamp
            )
            
            if thread_response and thread_response.get('messages'):
                messages = thread_response['messages']
                self.log.info(f"Found {len(messages)} messages in thread for timestamp {timestamp}")
                
                # Look through all replies for bot messages containing ticket info
                for i, message in enumerate(thread_response['messages']):
                    # Skip the original message
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
                    
                    self.log.info(f"Message {i}: user={message_user}, bot_id={message_bot_id}, is_our_bot={is_our_bot_message}")
                    
                    # Only check bot messages for ticket creation
                    if is_our_bot_message:
                        # Check if the message contains ticket creation indicators
                        create_indicators = [
                            '✅ MOCK-OPS ticket created:',
                            'MOCK-OPS-',
                            'ticket created:',
                            'browse/MOCK-OPS-'
                        ]
                        if any(indicator in message_text for indicator in create_indicators):
                            self.log.info(f"Found existing ticket creation message: {message_text[:100]}...")
                            return True
            else:
                self.log.warning(f"No thread messages found or API call failed for {timestamp}")
            
            self.log.info(f"No existing ticket found for message {timestamp}")
            return False
            
        except Exception as e:
            self.log.error(f"Error checking for duplicate tickets: {e}")
            # On error, assume not processed to avoid blocking legitimate requests
            return False
            
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
    
    def _handle_jira_in_review(self, channel, timestamp, user_id):
        """
        Handle :jirainreview: reaction to put a ticket in review status.
        Only works on root messages with existing tickets.
        """
        try:
            # First check if there's an existing ticket for this message
            ticket_info = self._find_existing_ticket(channel, timestamp)
            
            if not ticket_info:
                return "❌ No MOCK-OPS ticket found for this message. Please create a ticket with :jira: reaction first."
            
            # Mock updating the ticket status to "In Review"
            ticket_key = ticket_info.get('key', 'UNKNOWN-TICKET')
            update_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Create response with updated status
            response_text = f"🔄 MOCK-OPS ticket {ticket_key} status updated to *In Review*\n"\
                           f"👤 Changed by: <@{user_id}>\n"\
                           f"⏰ Updated: {update_time}\n"\
                           f"🔗 Link: {ticket_info.get('url', 'https://yourcompany.atlassian.net/browse/' + ticket_key)}"
            
            self.log.info(f"Updated ticket {ticket_key} to In Review status")
            return response_text
            
        except Exception as e:
            self.log.error(f"Error handling jirainreview reaction: {e}")
            return f"❌ Error updating ticket status: {str(e)}"
    
    def _handle_jira_close_ticket(self, channel, timestamp, user_id):
        """
        Handle :jiracloseticket: reaction to close a ticket.
        Only works on root messages with existing tickets.
        """
        try:
            # First check if there's an existing ticket for this message
            ticket_info = self._find_existing_ticket(channel, timestamp)
            
            if not ticket_info:
                return "❌ No MOCK-OPS ticket found for this message. Please create a ticket with :jira: reaction first."
            
            # Mock closing the ticket
            ticket_key = ticket_info.get('key', 'UNKNOWN-TICKET')
            close_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Create response with closed status
            response_text = f"✅ MOCK-OPS ticket {ticket_key} has been *Closed*\n"\
                           f"👤 Closed by: <@{user_id}>\n"\
                           f"⏰ Closed on: {close_time}\n"\
                           f"🔍 Resolution: Fixed\n"\
                           f"🔗 Link: {ticket_info.get('url', 'https://yourcompany.atlassian.net/browse/' + ticket_key)}"
            
            self.log.info(f"Closed ticket {ticket_key}")
            return response_text
            
        except Exception as e:
            self.log.error(f"Error handling jiracloseticket reaction: {e}")
            return f"❌ Error closing ticket: {str(e)}"
    
    def _find_existing_ticket(self, channel, timestamp):
        """
        Find an existing ticket in a thread by scanning bot messages.
        Returns ticket information if found, None otherwise.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available for finding existing ticket")
                return None
            
            # Get bot's user ID
            bot_user_id = self._get_bot_user_id()
            if not bot_user_id:
                self.log.warning("Could not determine bot user ID")
                return None
            
            # Get thread replies
            thread_response = self._make_slack_api_call_with_retry(
                slack_client, 
                'conversations_replies',
                channel=channel,
                ts=timestamp
            )
            
            if not thread_response or not thread_response.get('messages'):
                self.log.warning(f"No messages found in thread {timestamp}")
                return None
            
            # Look through messages for bot messages with ticket info
            for message in thread_response['messages']:
                # Skip the original message
                if message.get('ts') == timestamp:
                    continue
                
                message_user = message.get('user')
                message_bot_id = message.get('bot_id')
                message_text = message.get('text', '')
                
                # Check if it's from our bot
                is_our_bot_message = (
                    message_user == bot_user_id or 
                    (message_bot_id and hasattr(self._bot, '_bot_id') and message_bot_id == self._bot._bot_id)
                )
                
                if is_our_bot_message and 'MOCK-OPS-' in message_text and 'ticket created' in message_text.lower():
                    # Try to extract ticket info from message
                    ticket_info = {}
                    
                    # Extract key
                    import re
                    key_match = re.search(r'MOCK-OPS-\d+', message_text)
                    if key_match:
                        ticket_info['key'] = key_match.group(0)
                    else:
                        continue
                    
                    # Extract URL if present
                    url_match = re.search(r'https://[^\s]+', message_text)
                    if url_match:
                        ticket_info['url'] = url_match.group(0)
                    else:
                        ticket_info['url'] = f"https://yourcompany.atlassian.net/browse/{ticket_info['key']}"
                    
                    # Extract summary if present
                    summary_match = re.search(r'Summary: (.+?)[\n\r]', message_text)
                    if summary_match:
                        ticket_info['summary'] = summary_match.group(1)
                    else:
                        ticket_info['summary'] = "Unknown summary"
                    
                    self.log.info(f"Found existing ticket: {ticket_info['key']}")
                    return ticket_info
            
            self.log.info(f"No existing ticket found in thread {timestamp}")
            return None
            
        except Exception as e:
            self.log.error(f"Error finding existing ticket: {e}")
            return None
