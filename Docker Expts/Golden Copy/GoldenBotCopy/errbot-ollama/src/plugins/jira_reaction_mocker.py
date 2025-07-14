from errbot import BotPlugin
import datetime
import time
import re
import random

CLOSURE_FORM_BLOCKS = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ":memo: Enter the *Ticket Closure Summary*"
        }
    },
    {
        "type": "input",
        "block_id": "ticket_closure_input_block",
        "element": {
            "type": "plain_text_input",
            "action_id": "closure_input_action",
            "multiline": True,
            "placeholder": {
                "type": "plain_text",
                "text": "Enter closure summary..."
            }
        },
        "label": {
            "type": "plain_text",
            "text": "Summary",
            "emoji": True
        }
    },
    {
        "type": "actions",
        "block_id": "ticket_closure_actions_block",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Close Ticket",
                    "emoji": True
                },
                "value": "close_ticket",
                "action_id": "close_ticket_action",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Cancel",
                    "emoji": True
                },
                "value": "cancel",
                "action_id": "close_ticket_cancel"
            }
        ]
    }
]

REVIEW_FORM_BLOCKS = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ":mag: Enter the *Review Summary*"
        }
    },
    {
        "type": "input",
        "block_id": "review_summary_input_block",
        "element": {
            "type": "plain_text_input",
            "action_id": "review_input_action",
            "multiline": True,
            "placeholder": {
                "type": "plain_text",
                "text": "Enter review summary..."
            }
        },
        "label": {
            "type": "plain_text",
            "text": "Review Summary",
            "emoji": True
        }
    },
    {
        "type": "actions",
        "block_id": "review_summary_actions_block",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Mark In Review",
                    "emoji": True
                },
                "value": "mark_in_review",
                "action_id": "mark_in_review_action",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Cancel",
                    "emoji": True
                },
                "value": "cancel",
                "action_id": "review_cancel"
            }
        ]
    }
]


class JiraReactionMocker(BotPlugin):
    """
    Plugin to mock Jira ticket operations via Slack reactions.
    
    Reactions: :jira: (create), :jirainreview: (review), :jiracloseticket: (close), :add2jira: (add comments)
    """
    
    # Rate limiting configuration
    REACTION_DELAY = 3
    API_RETRY_DELAY = 10

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
            
            # Try conversations_replies first
            try:
                response = slack_client.conversations_replies(channel=channel, ts=ts, limit=1, inclusive=True)
                if response.get('ok') and response.get('messages'):
                    for msg in response['messages']:
                        if msg.get('ts') == ts:
                            self.log.info("✅ Found message via conversations_replies")
                            return msg
            except Exception:
                pass
            
            # Fallback: conversations_history
            try:
                target_ts = float(ts)
                response = slack_client.conversations_history(
                    channel=channel, oldest=str(target_ts - 1), latest=str(target_ts + 1), 
                    inclusive=True, limit=10
                )
                if response.get('ok') and response.get('messages'):
                    for msg in response['messages']:
                        if msg.get('ts') == ts:
                            self.log.info("✅ Found message via conversations_history")
                            return msg
            except Exception:
                pass
            
            # Minimal fallback
            return {'ts': ts, 'text': 'Message text unavailable', 'user': 'unknown', 'thread_ts': None}
                
        except Exception as e:
            self.log.error(f"Error getting message info: {e}")
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
                self._post_error_message(channel, ts, "❌ :jira: reaction can only be used on root messages.")
                return True
            
            # Check if ticket already exists for this thread
            thread_mapping_key = f"thread_to_ticket_{thread_ts}"
            existing_ticket_key = self.get(thread_mapping_key)
            
            if existing_ticket_key:
                existing_ticket = self.get(existing_ticket_key)
                if existing_ticket:
                    self._post_error_message(channel, ts, f"❌ Ticket already exists: {existing_ticket['key']}")
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
            
            # Post concise success message
            success_msg = f"✅ Created: {ticket_data['key']} - {ticket_title[:50]}{'...' if len(ticket_title) > 50 else ''}"
            self._post_success_message(channel, ts, success_msg)
            self.log.info(f"Created ticket {ticket_data['key']} for thread {thread_ts}")
            return True
            
        except Exception as e:
            self.log.error(f"Error creating JIRA ticket: {e}")
            self._post_error_message(channel, ts, f"❌ Error creating JIRA ticket: {str(e)}")
            return True

    def _handle_jira_review(self, channel, ts, thread_ts, is_root, user_id):
        """Handle :jirainreview: reaction - show review form and mark ticket in review."""
        try:
            if not is_root:
                self._post_error_message(channel, ts, "❌ :jirainreview: can only be used on root messages.")
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
            
            if ticket_data['status'] in ['In Review', 'Closed']:
                self._post_error_message(channel, ts, f"❌ {ticket_data['key']} is already {ticket_data['status'].lower()}.")
                return True
            
            # Show the review form
            review_blocks = REVIEW_FORM_BLOCKS.copy()
            review_blocks.insert(0, {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Marking ticket In Review:* {ticket_data['key']}"
                }
            })
            
            response = self._send_blocks(blocks=review_blocks, text="Enter review summary", channel=channel, thread_ts=ts)
            if not response:
                self._post_error_message(channel, ts, "❌ Failed to show review form")
                return True
                
            self.log.info(f"Showed review form for {ticket_data['key']}")
            return True
            
        except Exception as e:
            self.log.error(f"Error handling jira review: {e}")
            return False

    def _handle_jira_close(self, channel, ts, thread_ts, is_root, user_id):
        """Handle :jiraticketclose: reaction - show closure form and close ticket."""
        try:
            if not is_root:
                self._post_error_message(channel, ts, "❌ :jiracloseticket: can only be used on root messages.")
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
                self._post_error_message(channel, ts, f"❌ {ticket_data['key']} is already closed.")
                return True
            
            # Show the closure form
            closure_blocks = CLOSURE_FORM_BLOCKS.copy()
            # Add ticket context
            closure_blocks.insert(0, {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Closing ticket:* {ticket_data['key']}"
                }
            })
            
            response = self._send_blocks(blocks=closure_blocks, text="Enter closure summary", channel=channel, thread_ts=ts)
            if not response:
                self._post_error_message(channel, ts, "❌ Failed to show closure form")
                return True
                
            self.log.info(f"Showed closure form for {ticket_data['key']}")
            return True
            
        except Exception as e:
            self.log.error(f"Error handling jira close: {e}")
            return False
            return True
            
        except Exception as e:
            self.log.error(f"Error closing ticket: {e}")
            self._post_error_message(channel, ts, f"❌ Error closing ticket: {str(e)}")
            return True

    def _handle_add2jira(self, channel, ts, thread_ts, is_root, user_id):
        """Handle :add2jira: reaction - add replies as comments."""
        try:
            if is_root:
                self._post_error_message(channel, ts, "❌ :add2jira: can only be used on replies.")
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
                self._post_error_message(channel, ts, "❌ No new comments to add (bot messages excluded).")
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
            
            # Create concise summary
            success_msg = f"✅ Added {len(comments)} comments to {ticket_data['key']}"
            self._post_success_message(channel, ts, success_msg)
            
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
                return None
            
            time.sleep(2)  # Rate limiting delay
            
            # Try with exponential backoff
            attempt = 0
            for limit in [50, 20, 10]:
                attempt += 1
                try:
                    if attempt > 1:
                        delay = self.API_RETRY_DELAY * (attempt - 1)
                        time.sleep(delay)
                        
                    response = slack_client.conversations_replies(
                        channel=channel, ts=thread_ts, limit=limit, inclusive=True
                    )
                    
                    if response.get('ok') and response.get('messages'):
                        messages = response['messages']
                        replies = [msg for msg in messages if msg.get('ts') != thread_ts]
                        return replies
                    elif response.get('error'):
                        error_type = response.get('error')
                        if error_type in ['rate_limited', 'ratelimited']:
                            time.sleep(self.API_RETRY_DELAY)
                            continue
                        elif limit == 10:
                            return None
                    else:
                        break
                        
                except Exception as api_error:
                    if 'ratelimited' in str(api_error).lower():
                        time.sleep(self.API_RETRY_DELAY)
                    if limit == 10:
                        return None
                    continue
            
            return None
                
        except Exception:
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

    def _send_blocks(self, blocks=None, text="", channel=None, thread_ts=None):
        """Helper to send blocks with proper channel formatting"""
        slack_client = self._get_slack_client()
        if not slack_client:
            self.log.warning("Slack client not available")
            return None
        
        try:
            response = slack_client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=text,
                thread_ts=thread_ts
            )
            self.log.info(f"Successfully sent blocks message")
            return response
        except Exception as e:
            self.log.error(f"Failed to send blocks: {e}")
            return None
    
    def _update_message(self, blocks=None, text="", channel=None, ts=None):
        """Helper to update/replace a message"""
        slack_client = self._get_slack_client()
        if not slack_client:
            self.log.warning("Slack client not available")
            return False
        
        try:
            slack_client.chat_update(
                channel=channel,
                ts=ts,
                blocks=blocks or [],
                text=text
            )
            return True
        except Exception as e:
            self.log.error(f"Failed to update message: {e}")
            return False

    def handle_block_action(self, action_id, value, payload, message):
        """Handle block actions for ticket closure and review forms"""
        try:
            self.log.info(f"Handling block action: action_id={action_id}")
            
            if action_id not in [
                'close_ticket_action', 'close_ticket_cancel',
                'mark_in_review_action', 'review_cancel']:
                return
            
            channel = payload.get('channel', {}).get('id')
            message_ts = payload.get('container', {}).get('message_ts')
            
            # Get thread_ts from payload for block submissions
            thread_ts = payload.get('message', {}).get('thread_ts')
            if not thread_ts:
                if hasattr(message, 'thread_ts'):
                    thread_ts = message.thread_ts
                elif isinstance(message, dict):
                    thread_ts = message.get('thread_ts')
                if not thread_ts:
                    thread_ts = message_ts
            self.log.info(f"Processing block action with thread_ts={thread_ts}, message_ts={message_ts}")
            user_id = payload.get('user', {}).get('id')
            
            if action_id == 'close_ticket_cancel' or action_id == 'review_cancel':
                # Remove the form
                self._update_message(blocks=[], text="Action cancelled", channel=channel, ts=message_ts)
                return
            
            if action_id == 'close_ticket_action':
                # Get the closure summary
                state_values = payload.get('state', {}).get('values', {})
                closure_summary = None
                
                for block_data in state_values.values():
                    if 'closure_input_action' in block_data:
                        closure_summary = block_data['closure_input_action'].get('value', '').strip()
                        break
                
                if not closure_summary:
                    self._update_message(
                        blocks=[],
                        text="❌ Closure summary cannot be empty",
                        channel=channel,
                        ts=message_ts
                    )
                    return
                
                # Get ticket data
                thread_mapping_key = f"thread_to_ticket_{thread_ts}"
                ticket_key = self.get(thread_mapping_key)
                
                if not ticket_key:
                    self._update_message(
                        blocks=[],
                        text="❌ No JIRA ticket found in this thread",
                        channel=channel,
                        ts=message_ts
                    )
                    return
                
                ticket_data = self.get(ticket_key)
                if not ticket_data:
                    self._update_message(
                        blocks=[],
                        text="❌ JIRA ticket data not found",
                        channel=channel,
                        ts=message_ts
                    )
                    return
                
                if ticket_data['status'] == 'Closed':
                    self._update_message(
                        blocks=[],
                        text=f"❌ {ticket_data['key']} is already closed",
                        channel=channel,
                        ts=message_ts
                    )
                    return
                
                # Update ticket with closure info
                ticket_data['status'] = 'Closed'
                ticket_data['closed_by'] = user_id
                ticket_data['closed_at'] = datetime.datetime.now().isoformat()
                ticket_data['closure_summary'] = closure_summary
                self[ticket_key] = ticket_data
                
                # Update the message to show mock JIRA closure and summary
                user_name = self._get_user_display_name(user_id)
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                success_msg = (
                    f"✅ {ticket_data['key']} → Closed\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"*JIRA Ticket Closure*\n"
                    f"• *Ticket:* {ticket_data['key']}\n"
                    f"• *Title:* {ticket_data['title']}\n"
                    f"• *Closed by:* @{user_name}\n"
                    f"• *Closed at:* {current_time}\n"
                    f"• *Closure Summary:*\n{closure_summary}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                self._update_message(blocks=[], text=success_msg, channel=channel, ts=message_ts)
                self.log.info(f"Closed ticket {ticket_data['key']} with summary")
                
                return
            
            if action_id == 'mark_in_review_action':
                # Get the review summary
                state_values = payload.get('state', {}).get('values', {})
                review_summary = None
                for block_data in state_values.values():
                    if 'review_input_action' in block_data:
                        review_summary = block_data['review_input_action'].get('value', '').strip()
                        break
                
                if not review_summary:
                    self._update_message(
                        blocks=[],
                        text="❌ Review summary cannot be empty",
                        channel=channel,
                        ts=message_ts
                    )
                    return
                
                # Get ticket data
                thread_mapping_key = f"thread_to_ticket_{thread_ts}"
                ticket_key = self.get(thread_mapping_key)
                
                if not ticket_key:
                    self._update_message(
                        blocks=[],
                        text="❌ No JIRA ticket found in this thread",
                        channel=channel,
                        ts=message_ts
                    )
                    return
                
                ticket_data = self.get(ticket_key)
                if not ticket_data:
                    self._update_message(
                        blocks=[],
                        text="❌ JIRA ticket data not found",
                        channel=channel,
                        ts=message_ts
                    )
                    return
                
                if ticket_data['status'] in ['In Review', 'Closed']:
                    self._update_message(
                        blocks=[],
                        text=f"❌ {ticket_data['key']} is already {ticket_data['status'].lower()}",
                        channel=channel,
                        ts=message_ts
                    )
                    return
                
                # Update ticket with review info
                ticket_data['status'] = 'In Review'
                ticket_data['reviewed_by'] = user_id
                ticket_data['reviewed_at'] = datetime.datetime.now().isoformat()
                ticket_data['review_summary'] = review_summary
                self[ticket_key] = ticket_data
                
                # Update the message to show mock JIRA review and summary
                user_name = self._get_user_display_name(user_id)
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                success_msg = (
                    f"🔄 {ticket_data['key']} → In Review\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"*JIRA Ticket Review*\n"
                    f"• *Ticket:* {ticket_data['key']}\n"
                    f"• *Title:* {ticket_data['title']}\n"
                    f"• *Reviewed by:* @{user_name}\n"
                    f"• *Reviewed at:* {current_time}\n"
                    f"• *Review Summary:*\n{review_summary}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                self._update_message(blocks=[], text=success_msg, channel=channel, ts=message_ts)
                self.log.info(f"Marked ticket {ticket_data['key']} as In Review with summary")
                return

        except Exception as e:
            self.log.error(f"Error handling block action: {e}")
            return False
