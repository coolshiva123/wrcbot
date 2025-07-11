from errbot import BotPlugin
import datetime
import time
import re
import random


class JiraReactionMocker(BotPlugin):
    """
    Plugin to mock Jira ticket operations via Slack reactions.
    
    Reactions:
    - :jira: (root only) - Create a mock Jira ticket
    - :jirainreview: (root only) - Move ticket to "In Review" status  
    - :jiracloseticket: (root only) - Close the ticket
    - :add2jira: (replies only) - Add thread replies as comments to ticket
    
    Rate Limiting Configuration:
    - REACTION_DELAY: Delay after receiving a reaction (default: 2 seconds)
    - API_RETRY_DELAY: Delay between API retries (default: 10 seconds)
    """
    
    # Rate limiting configuration - easily adjustable
    REACTION_DELAY = 3  # Seconds to wait after receiving a reaction (increased)
    API_RETRY_DELAY = 10  # Seconds to wait between API retries (increased for rate limiting)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = {}  # Cache for user display names
        self._bot_user_id = None  # Cache for bot's user ID

    def activate(self):
        super().activate()
        self.log.info("JiraReactionMocker plugin activated")
        # Cache bot user ID on activation
        self._cache_bot_user_id()

    def _cache_bot_user_id(self):
        """Fetch and cache the bot's Slack user ID using the Slack API."""
        slack_client = self._get_slack_client()
        if not slack_client:
            self.log.warning("Slack client not available for bot user ID fetch")
            return
        try:
            auth_info = slack_client.auth_test()
            self._bot_user_id = auth_info.get('user_id')
            self.log.info(f"Fetched and cached bot user ID: {self._bot_user_id}")
        except Exception as e:
            self.log.error(f"Failed to fetch bot user ID: {e}")

    def callback_reaction_added(self, event):
        """Handle Slack reaction_added events."""
        try:
            self.log.info(f"🎯 Reaction added event: {event}")
            
            reaction = event.get('reaction')
            if reaction not in ['jira', 'jirainreview', 'jiracloseticket', 'add2jira']:
                return False
            
            # Add configurable delay to avoid rate limiting
            time.sleep(self.REACTION_DELAY)
            
            item = event.get('item', {})
            channel = item.get('channel')
            ts = item.get('ts')
            user_id = event.get('user')
            
            if not channel or not ts:
                self.log.warning("Missing channel or timestamp in reaction event")
                return False
            
            # Get message context to determine if it's root or reply
            message_info = self._get_message_info(channel, ts)
            if not message_info:
                self.log.error("Could not get message info")
                return False
            
            # Determine if this is a root message or reply
            # Check if the message has a thread_ts that's different from its own ts
            message_thread_ts = message_info.get('thread_ts')
            is_root = not message_thread_ts or message_thread_ts == ts
            
            # For thread identification, use the thread_ts if available, otherwise use the message ts
            thread_ts = message_thread_ts or ts
            
            self.log.info(f"Processing {reaction} reaction: is_root={is_root}, thread_ts={thread_ts}, message_ts={ts}")
            
            # If we couldn't determine thread context from message, try to infer from Slack API
            if not message_thread_ts and reaction in ['add2jira']:
                # For add2jira, we need to check if this message is actually in a thread
                thread_check = self._check_if_message_in_thread(channel, ts)
                if thread_check:
                    is_root = False
                    thread_ts = thread_check
                    self.log.info(f"Corrected thread detection: is_root={is_root}, thread_ts={thread_ts}")
            
            # Route to appropriate handler
            if reaction == 'jira':
                return self._handle_jira_create(channel, ts, thread_ts, is_root, user_id, message_info)
            elif reaction == 'jirainreview':
                return self._handle_jira_review(channel, ts, thread_ts, is_root, user_id)
            elif reaction == 'jiracloseticket':
                return self._handle_jira_close(channel, ts, thread_ts, is_root, user_id)
            elif reaction == 'add2jira':
                return self._handle_add2jira(channel, ts, thread_ts, is_root, user_id)
                
        except Exception as e:
            self.log.error(f"Error handling reaction_added: {e}")
            return False

    def _get_message_info(self, channel, ts):
        """Get message information from Slack API."""
        try:
            slack_client = self._get_slack_client()
            if not slack_client:
                return None
            
            # First try conversations_replies in case it's in a thread
            try:
                reply_response = slack_client.conversations_replies(
                    channel=channel,
                    ts=ts,
                    limit=1,
                    inclusive=True
                )
                
                if reply_response.get('ok') and reply_response.get('messages'):
                    # Find the exact message with matching timestamp
                    for msg in reply_response['messages']:
                        if msg.get('ts') == ts:
                            self.log.info(f"✅ Found message via conversations_replies")
                            return msg
            except Exception as e:
                self.log.warning(f"conversations_replies failed: {e}")
            
            # Fallback: try conversations_history with a time window
            try:
                target_ts = float(ts)
                # Use a small time window around the target timestamp
                start_time = str(target_ts - 1)  # 1 second before
                end_time = str(target_ts + 1)    # 1 second after
                
                response = slack_client.conversations_history(
                    channel=channel,
                    oldest=start_time,
                    latest=end_time,
                    inclusive=True,
                    limit=10
                )
                
                if response.get('ok') and response.get('messages'):
                    # Find the exact message with matching timestamp
                    for msg in response['messages']:
                        if msg.get('ts') == ts:
                            self.log.info(f"✅ Found message via conversations_history")
                            return msg
                    
                    self.log.warning(f"Message {ts} not found in history results")
                else:
                    self.log.warning(f"conversations_history failed: {response.get('error', 'unknown error') if response else 'no response'}")
            except Exception as e:
                self.log.warning(f"conversations_history failed: {e}")
            
            # Final fallback: create a minimal message object
            self.log.warning(f"Could not fetch message {ts} from API, creating minimal object")
            return {
                'ts': ts,
                'text': 'Message text unavailable',
                'user': 'unknown',
                'thread_ts': None  # We'll determine this from the reaction event context
            }
                
        except Exception as e:
            self.log.error(f"Error getting message info: {e}")
            return None

    def _check_if_message_in_thread(self, channel, ts):
        """Check if a message is part of a thread and return the thread root timestamp."""
        try:
            slack_client = self._get_slack_client()
            if not slack_client:
                return None
            
            # Get a broader conversation history to see thread context
            target_ts = float(ts)
            start_time = str(target_ts - 3600)  # Look 1 hour back
            end_time = str(target_ts + 60)      # Look 1 minute forward
            
            response = slack_client.conversations_history(
                channel=channel,
                oldest=start_time,
                latest=end_time,
                inclusive=True,
                limit=100
            )
            
            if response.get('ok') and response.get('messages'):
                for msg in response['messages']:
                    # Check if our target message appears as a thread reply
                    if msg.get('ts') == ts and msg.get('thread_ts'):
                        return msg.get('thread_ts')
                        
                    # Check if our target message has replies (making it a thread root)
                    if msg.get('ts') == ts and msg.get('reply_count', 0) > 0:
                        return ts  # It's a thread root
                        
                    # Check if there are messages that reference our ts as thread_ts
                    if msg.get('thread_ts') == ts:
                        return ts  # Our message is a thread root
                        
            return None
            
        except Exception as e:
            self.log.warning(f"Error checking thread context: {e}")
            return None

    def _get_slack_client(self):
        """Get Slack client from bot."""
        if hasattr(self._bot, 'slack_web'):
            return self._bot.slack_web
        elif hasattr(self._bot, 'sc'):
            return self._bot.sc
        else:
            self.log.error("No Slack client available")
            return None

    def _handle_jira_create(self, channel, ts, thread_ts, is_root, user_id, message_info):
        """Handle :jira: reaction - create mock ticket."""
        try:
            if not is_root:
                self._post_error_message(channel, ts, "❌ :jira: reaction can only be used on root messages, not replies.")
                return True
            
            # Check if ticket already exists for this thread
            thread_mapping_key = f"thread_to_ticket_{thread_ts}"
            existing_ticket_key = self.get(thread_mapping_key)
            
            if existing_ticket_key:
                existing_ticket = self.get(existing_ticket_key)
                if existing_ticket:
                    self._post_error_message(channel, ts, f"❌ JIRA ticket already exists for this thread: {existing_ticket['key']}")
                    return True
            
            # Create mock ticket
            ticket_id = self._generate_ticket_id()
            ticket_title = self._clean_message_text(message_info.get('text', 'Untitled'))
            
            # Limit title length
            if len(ticket_title) > 100:
                ticket_title = ticket_title[:97] + "..."
            
            jira_ticket_key = f'MOCK-OPS-{ticket_id}'
            ticket_data = {
                'key': jira_ticket_key,
                'title': ticket_title,
                'status': 'Open',
                'created_by': user_id,
                'created_at': datetime.datetime.now().isoformat(),
                'channel': channel,
                'thread_ts': thread_ts,
                'comments': [],
                'last_add2jira_ts': None
            }
            
            # Save ticket to storage using JIRA ticket key
            self[jira_ticket_key] = ticket_data
            # Create thread mapping for lookup
            self[thread_mapping_key] = jira_ticket_key
            
            # Post success message
            success_msg = (f"✅ MOCK-OPS ticket created: {ticket_data['key']}\n"
                          f"**Title:** {ticket_title}\n"
                          f"**Status:** Open\n"
                          f"**URL:** https://yourcompany.atlassian.net/browse/{ticket_data['key']}")
            
            self._post_success_message(channel, ts, success_msg)
            self.log.info(f"Created ticket {ticket_data['key']} for thread {thread_ts}")
            return True
            
        except Exception as e:
            self.log.error(f"Error creating JIRA ticket: {e}")
            self._post_error_message(channel, ts, f"❌ Error creating JIRA ticket: {str(e)}")
            return True

    def _handle_jira_review(self, channel, ts, thread_ts, is_root, user_id):
        """Handle :jirainreview: reaction - move ticket to review."""
        try:
            if not is_root:
                self._post_error_message(channel, ts, "❌ :jirainreview: reaction can only be used on root messages, not replies.")
                return True
            
            # Get existing ticket
            thread_mapping_key = f"thread_to_ticket_{thread_ts}"
            ticket_key = self.get(thread_mapping_key)
            
            if not ticket_key:
                self._post_error_message(channel, ts, "❌ No JIRA ticket found in this thread. Create one with :jira: reaction first.")
                return True
                
            ticket_data = self.get(ticket_key)
            if not ticket_data:
                self._post_error_message(channel, ts, "❌ JIRA ticket data not found.")
                return True
            
            if ticket_data['status'] == 'In Review':
                self._post_error_message(channel, ts, f"❌ Ticket {ticket_data['key']} is already in review.")
                return True
                
            if ticket_data['status'] == 'Closed':
                self._post_error_message(channel, ts, f"❌ Ticket {ticket_data['key']} is already closed.")
                return True
            
            # Update ticket status
            ticket_data['status'] = 'In Review'
            ticket_data['reviewed_by'] = user_id
            ticket_data['reviewed_at'] = datetime.datetime.now().isoformat()
            self[ticket_key] = ticket_data
            
            success_msg = (f"✅ JIRA ticket moved to review: {ticket_data['key']}\n"
                          f"**Status:** In Review\n"
                          f"**URL:** https://yourcompany.atlassian.net/browse/{ticket_data['key']}")
            
            self._post_success_message(channel, ts, success_msg)
            self.log.info(f"Moved ticket {ticket_data['key']} to In Review")
            return True
            
        except Exception as e:
            self.log.error(f"Error moving ticket to review: {e}")
            self._post_error_message(channel, ts, f"❌ Error moving ticket to review: {str(e)}")
            return True

    def _handle_jira_close(self, channel, ts, thread_ts, is_root, user_id):
        """Handle :jiraticketclose: reaction - close ticket."""
        try:
            if not is_root:
                self._post_error_message(channel, ts, "❌ :jiracloseticket: reaction can only be used on root messages, not replies.")
                return True
            
            # Get existing ticket
            thread_mapping_key = f"thread_to_ticket_{thread_ts}"
            ticket_key = self.get(thread_mapping_key)
            
            if not ticket_key:
                self._post_error_message(channel, ts, "❌ No JIRA ticket found in this thread. Create one with :jira: reaction first.")
                return True
                
            ticket_data = self.get(ticket_key)
            if not ticket_data:
                self._post_error_message(channel, ts, "❌ JIRA ticket data not found.")
                return True
            
            if ticket_data['status'] == 'Closed':
                self._post_error_message(channel, ts, f"❌ Ticket {ticket_data['key']} is already closed.")
                return True
            
            # Update ticket status
            ticket_data['status'] = 'Closed'
            ticket_data['closed_by'] = user_id
            ticket_data['closed_at'] = datetime.datetime.now().isoformat()
            self[ticket_key] = ticket_data
            
            success_msg = (f"✅ JIRA ticket closed: {ticket_data['key']}\n"
                          f"**Status:** *Closed*\n"
                          f"**URL:** https://yourcompany.atlassian.net/browse/{ticket_data['key']}")
            
            self._post_success_message(channel, ts, success_msg)
            self.log.info(f"Closed ticket {ticket_data['key']}")
            return True
            
        except Exception as e:
            self.log.error(f"Error closing ticket: {e}")
            self._post_error_message(channel, ts, f"❌ Error closing ticket: {str(e)}")
            return True

    def _handle_add2jira(self, channel, ts, thread_ts, is_root, user_id):
        """Handle :add2jira: reaction - add replies as comments."""
        try:
            if is_root:
                self._post_error_message(channel, ts, "❌ :add2jira: reaction can only be used on replies, not root messages.")
                return True
            
            # Get existing ticket
            thread_mapping_key = f"thread_to_ticket_{thread_ts}"
            ticket_key = self.get(thread_mapping_key)
            
            if not ticket_key:
                self._post_error_message(channel, ts, "❌ No JIRA ticket found in this thread. Create one with :jira: reaction first.")
                return True
                
            ticket_data = self.get(ticket_key)
            if not ticket_data:
                self._post_error_message(channel, ts, "❌ JIRA ticket data not found.")
                return True
            
            # Get all replies in the thread
            all_replies = self._get_thread_replies(channel, thread_ts)
            if all_replies is None:
                self._post_error_message(channel, ts, "❌ Could not retrieve thread replies. Check bot permissions or try again.")
                return True
            elif len(all_replies) == 0:
                self._post_error_message(channel, ts, "❌ No replies found in this thread to add as comments.")
                return True
            
            # Determine which replies to add as comments (excluding bot messages)
            last_add2jira_ts = ticket_data.get('last_add2jira_ts')
            if last_add2jira_ts:
                # Add replies since last add2jira up to current reaction
                new_replies = [msg for msg in all_replies 
                              if float(msg.get('ts', 0)) > float(last_add2jira_ts) 
                              and float(msg.get('ts', 0)) <= float(ts)
                              and msg.get('user') != self._bot_user_id]  # Exclude bot messages
            else:
                # Add all replies from thread start up to current reaction
                new_replies = [msg for msg in all_replies 
                              if float(msg.get('ts', 0)) <= float(ts)
                              and msg.get('user') != self._bot_user_id]  # Exclude bot messages
            
            if not new_replies:
                self._post_error_message(channel, ts, "❌ No new user comments to add to JIRA. Bot messages are excluded from comments.")
                return True
            
            # Format replies as comments
            comments = []
            for reply in new_replies:
                user_name = self._get_user_display_name(reply.get('user'))
                reply_text = self._clean_message_text(reply.get('text', ''))
                reply_ts = reply.get('ts', '')
                
                try:
                    timestamp = datetime.datetime.fromtimestamp(float(reply_ts)).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    timestamp = "Unknown time"
                
                comment = {
                    'author': user_name,
                    'text': reply_text,
                    'timestamp': timestamp,
                    'ts': reply_ts
                }
                comments.append(comment)
            
            # Update ticket with new comments
            ticket_data['comments'].extend(comments)
            ticket_data['last_add2jira_ts'] = ts
            self[ticket_key] = ticket_data
            
            # Create detailed comment summary
            comment_summary = []
            for i, comment in enumerate(comments, 1):
                comment_preview = comment['text'][:50] + "..." if len(comment['text']) > 50 else comment['text']
                comment_summary.append(f"{i}. **{comment['author']}**: {comment_preview}")
            
            success_msg = (f"✅ Added {len(comments)} user comments to JIRA ticket: {ticket_data['key']}\n"
                          f"**Total comments:** {len(ticket_data['comments'])}\n"
                          f"**URL:** https://yourcompany.atlassian.net/browse/{ticket_data['key']}\n\n"
                          f"**Comments added:**\n" + "\n".join(comment_summary))
            
            self._post_success_message(channel, ts, success_msg)
            
            # Also post the full comments as a threaded reply for reference
            if comments:
                full_comments_msg = f"📝 **Full JIRA Comments Added:**\n\n"
                for comment in comments:
                    full_comments_msg += f"**{comment['author']}** ({comment['timestamp']}):\n{comment['text']}\n\n"
                self._post_success_message(channel, ts, full_comments_msg)
            
            self.log.info(f"Added {len(comments)} comments to ticket {ticket_data['key']}")
            return True
            
        except Exception as e:
            self.log.error(f"Error adding comments to JIRA: {e}")
            self._post_error_message(channel, ts, f"❌ Error adding comments to JIRA: {str(e)}")
            return True

    def _get_thread_replies(self, channel, thread_ts):
        """Get all replies in a thread with fallback strategies."""
        try:
            slack_client = self._get_slack_client()
            if not slack_client:
                self.log.error("Slack client not available for getting thread replies")
                return None
            
            self.log.info(f"Getting thread replies for channel={channel}, thread_ts={thread_ts}")
            
            # Add initial delay to prevent rate limiting
            time.sleep(2)
            
            # Try with smaller limit first with exponential backoff
            attempt = 0
            for limit in [50, 20, 10]:
                attempt += 1
                try:
                    # Progressive delay for subsequent attempts
                    if attempt > 1:
                        delay = self.API_RETRY_DELAY * (attempt - 1)
                        self.log.info(f"Waiting {delay} seconds before attempt {attempt} with limit={limit}")
                        time.sleep(delay)
                        
                    self.log.info(f"Trying conversations_replies with limit={limit} (attempt {attempt})")
                    response = slack_client.conversations_replies(
                        channel=channel,
                        ts=thread_ts,
                        limit=limit,
                        inclusive=True
                    )
                    
                    self.log.info(f"conversations_replies response: ok={response.get('ok')}, error={response.get('error')}")
                    
                    if response.get('ok') and response.get('messages'):
                        # Filter out the root message, return only replies
                        messages = response['messages']
                        replies = [msg for msg in messages if msg.get('ts') != thread_ts]
                        self.log.info(f"Found {len(replies)} replies in thread (limit={limit})")
                        return replies
                    elif response.get('error'):
                        error_type = response.get('error')
                        self.log.warning(f"API error with limit {limit}: {error_type}")
                        if error_type in ['rate_limited', 'ratelimited']:
                            self.log.info(f"Rate limited, waiting {self.API_RETRY_DELAY} seconds before next attempt")
                            time.sleep(self.API_RETRY_DELAY)  # Wait before trying smaller limit
                            continue
                        elif limit == 10:  # Last attempt failed
                            self.log.error(f"All attempts failed. Final error: {error_type}")
                            return None
                    else:
                        self.log.warning(f"No messages returned with limit {limit}")
                        break  # No point trying smaller limits
                        
                except Exception as api_error:
                    error_msg = str(api_error)
                    self.log.error(f"Exception with limit {limit}: {api_error}")
                    
                    # Check if this is a rate limiting error
                    if 'ratelimited' in error_msg.lower() or 'rate_limited' in error_msg.lower():
                        self.log.info(f"Rate limiting exception detected, waiting {self.API_RETRY_DELAY} seconds before next attempt")
                        time.sleep(self.API_RETRY_DELAY)
                    
                    if limit == 10:  # Last attempt
                        return None
                    continue
            
            return None
                
        except Exception as e:
            self.log.error(f"Error getting thread replies: {e}")
            return None

    def _get_user_display_name(self, user_id):
        """Get user display name with caching."""
        if not user_id:
            return "Unknown User"
        
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        try:
            slack_client = self._get_slack_client()
            if not slack_client:
                self.user_cache[user_id] = f"User {user_id}"
                return self.user_cache[user_id]
            
            response = slack_client.users_info(user=user_id)
            
            if response.get('ok') and response.get('user'):
                user_info = response['user']
                display_name = (
                    user_info.get('profile', {}).get('display_name') or 
                    user_info.get('real_name') or 
                    user_info.get('name') or 
                    f"User {user_id}"
                )
                self.user_cache[user_id] = display_name
            else:
                self.user_cache[user_id] = f"User {user_id}"
                
        except Exception as e:
            self.log.warning(f"Error fetching user info for {user_id}: {e}")
            self.user_cache[user_id] = f"User {user_id}"
        
        return self.user_cache[user_id]

    def _clean_message_text(self, text):
        """Clean and format message text."""
        if not text:
            return "Untitled"
        
        try:
            # Replace user mentions with readable format
            def replace_user_mention(match):
                user_id = match.group(1)
                username = self._get_user_display_name(user_id)
                return f"@{username}"
            
            text = re.sub(r'<@(U[0-9A-Z]{8,})>', replace_user_mention, text)
            
            # Replace channel mentions
            text = re.sub(r'<#C[0-9A-Z]{8,}\|([^>]+)>', r'#\1', text)
            
            # Clean up links
            text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'\2 (\1)', text)
            text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
            
            # Remove excessive whitespace and newlines
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text or "Untitled"
            
        except Exception as e:
            self.log.warning(f"Error cleaning message text: {e}")
            return text or "Untitled"

    def _generate_ticket_id(self):
        """Generate a mock ticket ID."""
        return random.randint(100000, 999999)

    def _post_error_message(self, channel, thread_ts, message):
        """Post error message to thread."""
        try:
            slack_client = self._get_slack_client()
            if slack_client:
                slack_client.chat_postMessage(
                    channel=channel,
                    text=message,
                    thread_ts=thread_ts
                )
        except Exception as e:
            self.log.error(f"Error posting error message: {e}")

    def _post_success_message(self, channel, thread_ts, message):
        """Post success message to thread."""
        try:
            slack_client = self._get_slack_client()
            if slack_client:
                slack_client.chat_postMessage(
                    channel=channel,
                    text=message,
                    thread_ts=thread_ts
                )
        except Exception as e:
            self.log.error(f"Error posting success message: {e}")
