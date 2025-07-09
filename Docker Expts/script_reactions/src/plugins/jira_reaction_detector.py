from errbot import BotPlugin, botcmd
import json
import datetime
import time
import random

class JiraReactionDetector(BotPlugin):
    """
    Plugin to handle Jira-related reactions.
    Version: 2.1 - Enhanced Reply Detection
    
    Supported Reactions:
    - :jira: - Creates mock MOCK-OPS tickets on root messages only
    - :jirainreview: - Puts existing tickets in review status on root messages only
    - :jiracloseticket: - Closes existing tickets on root messages only
    - :add2jira: - Echoes back the message content of the reply message
    
    Features:
    - Simplified and robust reply/root message detection using thread_ts field
    - Duplicate ticket prevention with status tracking
    - Enhanced debugging with emoji indicators
    - Comprehensive error handling and permission checking
    - Status change tracking with timestamps
    
    Key Logic:
    - Root messages: No thread_ts OR thread_ts == message ts
    - Reply messages: thread_ts != message ts
    """

    def activate(self):
        super().activate()
        self.log.info("JiraReactionDetector plugin activated")

    def _make_slack_api_call_with_retry(self, slack_client, method_name, max_retries=3, **kwargs):
        """
        Make a Slack API call with retry logic for rate limiting and transient errors.
        Also checks for permission-related errors.
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
                elif response.get('error') == 'missing_scope':
                    # Special handling for permission errors
                    self.log.error(f"PERMISSION ERROR in {method_name}: Bot token is missing required OAuth scopes.")
                    self.log.error("Please check PERMISSION_CHECK_README.md and update your bot token permissions.")
                    return {
                        'ok': False,
                        'error': 'missing_scope',
                        'needed': response.get('needed', 'unknown_scope'),
                        'provided': response.get('provided', [])
                    }
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
            if reaction not in ['jira', 'jirainreview', 'jiracloseticket', 'add2jira']:
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
            elif reaction == 'add2jira':
                # Enhanced debugging for add2jira
                self.log.info(f"🔍 Processing add2jira reaction on message {timestamp}")
                
                is_reply_result = self._is_reply_message(channel, timestamp)
                self.log.info(f"🎯 Reply detection result: {is_reply_result}")
                
                if is_reply_result:
                    self.log.info(f"✅ Confirmed as REPLY - calling _summarize_thread_replies")
                    response_text = self._summarize_thread_replies(channel, timestamp)
                else:
                    self.log.info(f"❌ Confirmed as ROOT - no action taken")
                    response_text = "No action needed on root message. Please use :add2jira: reaction on reply messages only."
            
            # Send threaded response
            self._send_threaded_response(channel, timestamp, response_text)
            
            self.log.info(f"Successfully handled {reaction} reaction from user {user_id}")
            return True
            
        except Exception as e:
            self.log.error(f"Error handling {reaction} reaction: {e}")
            return False

    def _is_reply_message(self, channel, timestamp):
        """
        Simplified and robust method to determine if this is a reply message.
        The key insight: If a message has thread_ts that differs from its own ts, it's a reply.
        """
        try:
            # Access the Slack client through the bot backend
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available, assuming root message")
                return False
            
            self.log.info(f"Checking message type for timestamp: {timestamp}")
            
            # Primary method: Get the message directly and check thread_ts field
            try:
                target_ts = float(timestamp)
                self.log.info(f"Getting message directly with conversations_history")
                
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
                            msg_thread_ts = msg.get('thread_ts')
                            msg_ts = msg.get('ts')
                            
                            self.log.info(f"Found message - ts: {msg_ts}, thread_ts: {msg_thread_ts}")
                            
                            # CRITICAL LOGIC: If thread_ts exists and differs from message ts, it's a reply
                            if msg_thread_ts and msg_thread_ts != msg_ts:
                                self.log.info(f"✅ REPLY DETECTED: thread_ts ({msg_thread_ts}) != message ts ({msg_ts})")
                                return True
                            else:
                                self.log.info(f"❌ ROOT MESSAGE: No thread_ts or thread_ts == message ts")
                                return False
                                
                self.log.warning("Message not found in conversations_history, trying fallback")
                    
            except Exception as e:
                self.log.warning(f"Primary method failed: {e}")
            
            # Fallback method: Try conversations_replies to see if we can find the message
            try:
                self.log.info("Fallback: Trying conversations_replies to find message in potential threads")
                
                # Get recent messages to find potential thread roots
                recent_response = self._make_slack_api_call_with_retry(
                    slack_client,
                    'conversations_history',
                    channel=channel,
                    limit=30
                )
                
                if recent_response and recent_response.get('messages'):
                    for potential_root in recent_response['messages']:
                        # Skip if this is our target message
                        if potential_root.get('ts') == timestamp:
                            self.log.info(f"Found our target message in recent history as root")
                            return False
                            
                        # Check if this message has replies
                        if potential_root.get('reply_count', 0) > 0:
                            root_ts = potential_root.get('ts')
                            
                            # Get thread and check if our message is in it
                            thread_response = self._make_slack_api_call_with_retry(
                                slack_client,
                                'conversations_replies',
                                channel=channel,
                                ts=root_ts
                            )
                            
                            if thread_response and thread_response.get('messages'):
                                for msg in thread_response['messages']:
                                    if msg.get('ts') == timestamp:
                                        self.log.info(f"✅ REPLY DETECTED: Found message in thread starting at {root_ts}")
                                        return True
                                        
            except Exception as e:
                self.log.warning(f"Fallback method failed: {e}")
            
            # Default: assume root message if we can't determine otherwise
            self.log.info(f"Could not definitively determine message type - defaulting to ROOT for {timestamp}")
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
    
    def _handle_add_to_jira(self, channel, timestamp, user_id):
        """
        Handle :add2jira: reaction to add a comment to an existing ticket.
        Only works on reply messages, not on root messages.
        """
        try:
            # For reply messages, we need to find the root message and then find its ticket
            thread_root = self._get_thread_root(channel, timestamp)
            if not thread_root or thread_root == timestamp:
                return "❌ This is not a reply message. The :add2jira: reaction only works on replies to add comments to tickets."
                
            # First check if there's an existing ticket for the root message
            ticket_info = self._find_existing_ticket(channel, thread_root)
            
            if not ticket_info:
                return "❌ No MOCK-OPS ticket found for the parent message. Please create a ticket with :jira: reaction on the root message first."
            
            # Get the content of the reply message to use as the comment
            message_content = self._get_message_content(channel, timestamp)
            if not message_content:
                message_content = "No message content could be retrieved"
            
            # Mock adding a comment to the ticket
            ticket_key = ticket_info.get('key', 'UNKNOWN-TICKET')
            comment_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Create response for successful comment addition
            response_text = f"💬 Comment added to MOCK-OPS ticket {ticket_key}\n"\
                           f"👤 Added by: <@{user_id}>\n"\
                           f"⏰ Added on: {comment_time}\n"\
                           f"📝 Comment: \"{message_content[:100]}{'...' if len(message_content) > 100 else ''}\"\n"\
                           f"🔗 Link: {ticket_info.get('url', 'https://yourcompany.atlassian.net/browse/' + ticket_key)}"
            
            self.log.info(f"Added comment to ticket {ticket_key}")
            return response_text
            
        except Exception as e:
            self.log.error(f"Error handling add2jira reaction: {e}")
            return f"❌ Error adding comment to ticket: {str(e)}"
    
    def _get_thread_root(self, channel, timestamp):
        """
        Get the root timestamp of the thread for a given message.
        Returns the timestamp if it's already a root message.
        """
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("Slack client not available for thread root detection")
                return timestamp  # Safe fallback
            
            self.log.info(f"Getting thread root for message: {timestamp}")
            
            # First, try conversations.replies with the current timestamp
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
                        self.log.info(f"Found thread root: {root_timestamp} for message: {timestamp}")
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
                                self.log.info(f"Found thread root: {thread_ts} for message: {timestamp}")
                                return thread_ts
                            else:
                                self.log.info(f"Message {timestamp} is already the root message")
                                return timestamp  # This is already the root
            except Exception as e:
                self.log.warning(f"conversations.history fallback failed: {e}")
            
            # Final fallback: assume it's a root message
            self.log.warning(f"Could not determine thread root for {timestamp}, assuming it's the root")
            return timestamp
            
        except Exception as e:
            self.log.error(f"Error getting thread root: {e}")
            return timestamp  # Safe fallback
    
    def _get_message_content(self, channel, timestamp):
        """
        Get the content of a specific message.
        Includes improved error handling for permission issues and enhanced debugging.
        """
        try:
            self.log.info(f"📥 _get_message_content called with channel={channel}, timestamp={timestamp}")
            
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("❌ Slack client not available for getting message content")
                return "Message content unavailable"
            
            # Try to get the message content directly first
            target_ts = float(timestamp)
            self.log.info(f"🔍 Trying conversations_history with target_ts={target_ts}")
            
            response = self._make_slack_api_call_with_retry(
                slack_client,
                'conversations_history',
                channel=channel,
                latest=str(target_ts + 1),
                oldest=str(target_ts - 1),
                limit=10,
                inclusive=True
            )
            
            self.log.info(f"📡 conversations_history response received: {response is not None}")
            if response:
                self.log.info(f"✓ Response ok: {response.get('ok')}")
                if response.get('messages'):
                    self.log.info(f"📨 Found {len(response.get('messages'))} messages")
                    for i, msg in enumerate(response.get('messages')):
                        msg_ts = msg.get('ts')
                        msg_preview = msg.get('text', '')[:50]
                        self.log.info(f"📝 Message {i}: ts={msg_ts}, text_preview='{msg_preview}...'")
                        if msg_ts == timestamp:
                            self.log.info(f"🎯 FOUND TARGET MESSAGE!")
            
            # Check for permission errors
            if response and isinstance(response, dict) and response.get('error') == 'missing_scope':
                needed_scopes = response.get('needed', 'conversations:history')
                self.log.error(f"🔒 Permission error: Missing required scopes: {needed_scopes}")
                return f"Permission error: Missing required scopes: {needed_scopes}"
            
            if response and response.get('messages'):
                for msg in response['messages']:
                    if msg.get('ts') == timestamp:
                        message_text = msg.get('text', 'No message content')
                        self.log.info(f"✅ Found matching message with text: {message_text}")
                        return message_text
            
            self.log.warning("⚠️ Message not found in conversations_history, trying thread fallback")
            
            # Fallback: try to get from thread using a different approach
            # Instead of getting thread root first, try conversations_replies directly
            self.log.info(f"🔄 Trying conversations_replies directly with timestamp={timestamp}")
            
            direct_thread_response = self._make_slack_api_call_with_retry(
                slack_client,
                'conversations_replies',
                channel=channel,
                ts=timestamp
            )
            
            self.log.info(f"📡 Direct conversations_replies response received: {direct_thread_response is not None}")
            if direct_thread_response:
                self.log.info(f"✓ Response ok: {direct_thread_response.get('ok')}")
                if direct_thread_response.get('messages'):
                    self.log.info(f"📨 Found {len(direct_thread_response.get('messages'))} messages in direct thread call")
            
            # Check for permission errors again
            if direct_thread_response and isinstance(direct_thread_response, dict) and direct_thread_response.get('error') == 'missing_scope':
                needed_scopes = direct_thread_response.get('needed', 'conversations:replies')
                self.log.error(f"🔒 Permission error: Missing required scopes: {needed_scopes}")
                return f"Permission error: Missing required scopes: {needed_scopes}"
            
            if direct_thread_response and direct_thread_response.get('messages'):
                for msg in direct_thread_response['messages']:
                    if msg.get('ts') == timestamp:
                        message_text = msg.get('text', 'No message content')
                        self.log.info(f"✅ Found matching message in direct thread call with text: {message_text}")
                        return message_text
            
            self.log.warning("❌ Message not found in direct conversations_replies either")
            return "Message content could not be retrieved"
            
        except Exception as e:
            self.log.error(f"💥 Error getting message content: {e}")
            return "Error retrieving message content"
    
    def _summarize_thread_replies(self, channel, timestamp):
        """
        Simple handler for :add2jira: reaction that echoes back the message content.
        Includes permission error detection and enhanced debugging.
        """
        try:
            self.log.info(f"🔄 _summarize_thread_replies called with channel={channel}, timestamp={timestamp}")
            
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.warning("❌ Slack client not available for message retrieval")
                return "Unable to retrieve message - Slack client unavailable"
            
            # Get the message content
            self.log.info("📨 About to call _get_message_content")
            message_content = self._get_message_content(channel, timestamp)
            self.log.info(f"📋 _get_message_content returned: {message_content}")
            
            if message_content and message_content not in ["Message content could not be retrieved", "Error retrieving message content"]:
                self.log.info(f"✅ Successfully retrieved message content: {message_content[:100]}...")
                return f"Recorded the message: {message_content}"
            elif "missing_scope" in str(message_content):
                # Special handling for permission errors
                self.log.error("🔒 Permission error detected in message content retrieval")
                return "⚠️ PERMISSION ERROR: The bot lacks required permissions to read message content. Please check the bot's Slack token scopes and ensure 'conversations:history' and 'conversations:replies' are enabled."
            else:
                self.log.warning(f"⚠️ Could not retrieve message content for {timestamp}")
                return "Could not record the message. Message content could not be retrieved."
            
        except Exception as e:
            self.log.error(f"💥 Error processing message content: {e}")
            if "missing_scope" in str(e) or "not_allowed_token_type" in str(e):
                return "⚠️ PERMISSION ERROR: The bot lacks required permissions. Please update the bot's Slack token scopes."
            return f"Error processing message: {str(e)}"
