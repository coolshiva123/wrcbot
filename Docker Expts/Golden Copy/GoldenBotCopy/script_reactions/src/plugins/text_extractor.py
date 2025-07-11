from errbot import BotPlugin, botcmd
import datetime
import time
import re

class TextExtractor(BotPlugin):
    """
    Plugin to extract all messages from a Slack thread and create a text file.
    
    Commands:
    - textract - Extract all messages in the current thread (including root) and create a text file
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = {}  # Cache for user display names

    def activate(self):
        super().activate()
        self.log.info("TextExtractor plugin activated")

    @botcmd
    def textract(self, msg, args):
        """
        Extract all messages in the current thread or message and create a text file.
        Usage: textract
        """
        try:
            import time
            self.log.info("⏳ Adding delay to avoid rate limiting...")
            time.sleep(5)  # Add a 5 second delay to help avoid rate limiting
            
            self.log.info("🚀 TEXTRACT COMMAND INVOKED")
            
            # Get message context
            channel, thread_ts = self._get_message_context(msg)
            
            if not channel:
                return "❌ Could not determine channel. This command only works in Slack channels."
            
            if not thread_ts:
                return "❌ Could not determine message context. Please try again or use this command in a thread."
            
            self.log.info(f"Extracting messages from thread {thread_ts} in channel {channel}")
            
            # Extract all messages from the thread
            all_messages = self._extract_thread_messages(channel, thread_ts)
            
            if not all_messages:
                return "❌ Could not extract thread messages. The thread might be empty or inaccessible."
            
            # Create formatted text content
            text_content = self._create_text_file_content(all_messages)
            
            # Upload the text file to Slack
            success = self._upload_text_file(channel, thread_ts, text_content)
            
            if success:
                message_type = "thread" if len(all_messages) > 1 else "message"
                return f"✅ {message_type.title()} extracted successfully! {len(all_messages)} message(s) saved to text file."
            else:
                return "❌ Failed to upload text file. Check logs for details."
                
        except Exception as e:
            self.log.error(f"Error in textract command: {e}")
            return f"❌ Error extracting thread: {str(e)}"

    def _get_message_context(self, msg):
        """Extract channel and thread context from the message."""
        try:
            channel = None
            thread_ts = None
            msg_ts = None
            
            # Check slack_event first (most reliable for threads)
            if (hasattr(msg, 'extras') and msg.extras and isinstance(msg.extras, dict) and 
                'slack_event' in msg.extras and isinstance(msg.extras['slack_event'], dict)):
                
                slack_event = msg.extras['slack_event']
                
                # Get channel from slack_event
                channel = slack_event.get('channel')
                
                # Get timestamps from slack_event
                raw_msg_ts = slack_event.get('ts')  # Current message timestamp
                raw_thread_ts = slack_event.get('thread_ts')  # Thread root timestamp (if in thread)
                
                # Validate timestamps
                msg_ts = self._validate_timestamp(raw_msg_ts)
                thread_ts = self._validate_timestamp(raw_thread_ts)
                
                # Determine which timestamp to use for thread extraction
                if thread_ts and msg_ts:
                    # This is a reply in a thread - use thread_ts to get the ENTIRE thread
                    self.log.info(f"✅ Message is a REPLY in thread {thread_ts} - will extract entire thread")
                elif msg_ts and not thread_ts:
                    # This is either a root message or standalone message
                    thread_ts = msg_ts  # Use message timestamp as thread root
                    self.log.info(f"✅ Message might be THREAD ROOT {thread_ts}")
            
            # Fallback to message object attributes for channel if needed
            if not channel:
                if hasattr(msg, 'to') and hasattr(msg.to, 'channelid'):
                    channel = msg.to.channelid
                elif hasattr(msg, 'to') and hasattr(msg.to, 'id'):
                    channel = msg.to.id
            
            # Final validation
            if not thread_ts and msg_ts:
                thread_ts = msg_ts
            
            self.log.info(f"✅ Context: channel={channel}, thread_ts={thread_ts}")
            return channel, thread_ts
            
        except Exception as e:
            self.log.error(f"Error extracting message context: {e}")
            return None, None

    def _validate_timestamp(self, ts_value):
        """Validate a timestamp value."""
        try:
            if not ts_value:
                return None
            
            ts_str = str(ts_value).strip()
            
            # Check if it looks like a Unix timestamp
            if '.' in ts_str:
                seconds_part = ts_str.split('.')[0]
            else:
                seconds_part = ts_str
            
            if seconds_part.isdigit() and len(seconds_part) >= 10:
                if '.' not in ts_str:
                    ts_str += '.000000'
                return ts_str
            return None
                
        except Exception:
            return None

    def _extract_thread_messages(self, channel, thread_ts):
        """Extract all messages from a thread."""
        try:
            # Get Slack client
            slack_client = None
            if hasattr(self, '_bot') and hasattr(self._bot, 'slack_web'):
                slack_client = self._bot.slack_web
            elif hasattr(self, '_bot') and hasattr(self._bot, 'sc'):
                slack_client = self._bot.sc
            
            if not slack_client:
                self.log.error("❌ Slack client not available")
                return None
            
            all_messages = []
            
            # Try conversations_replies to get all messages in the thread
            try:
                response = slack_client.conversations_replies(
                    channel=channel,
                    ts=thread_ts,
                    limit=200,
                    inclusive=True
                )
                
                if response and response.get('ok') and response.get('messages'):
                    all_messages = response['messages']
                    self.log.info(f"✅ Got {len(all_messages)} messages via conversations_replies")
                else:
                    self.log.warning(f"conversations_replies failed: {response.get('error', 'unknown') if response else 'no response'}")
            except Exception as e:
                self.log.warning(f"conversations_replies exception: {e}")
            
            # Fallback: try conversations_history with time window
            if not all_messages:
                try:
                    target_ts = float(thread_ts)
                    start_time = target_ts - 3600  # 1 hour before
                    end_time = target_ts + 3600    # 1 hour after
                    
                    response = slack_client.conversations_history(
                        channel=channel,
                        oldest=str(start_time),
                        latest=str(end_time),
                        limit=1000,
                        inclusive=True
                    )
                    
                    if response and response.get('ok') and response.get('messages'):
                        history_messages = response['messages']
                        
                        # Filter messages that belong to this thread
                        thread_messages = []
                        for msg in history_messages:
                            msg_ts = msg.get('ts')
                            msg_thread_ts = msg.get('thread_ts')
                            
                            # Include root message and all replies
                            if msg_ts == thread_ts or msg_thread_ts == thread_ts:
                                thread_messages.append(msg)
                        
                        if thread_messages:
                            all_messages = thread_messages
                            self.log.info(f"✅ Got {len(all_messages)} messages via history fallback")
                
                except Exception as e:
                    self.log.warning(f"History fallback exception: {e}")
            
            # Sort messages by timestamp
            if all_messages:
                all_messages.sort(key=lambda msg: float(msg.get('ts', 0)))
            
            return all_messages
            
        except Exception as e:
            self.log.error(f"Error extracting thread messages: {e}")
            return None

    def _create_text_file_content(self, messages):
        """Create formatted text content from the messages."""
        try:
            lines = []
            lines.append("SLACK THREAD EXTRACTION")
            lines.append("=" * 50)
            lines.append(f"Extracted on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            lines.append(f"Total messages: {len(messages)}")
            lines.append("=" * 50)
            lines.append("")
            
            for i, message in enumerate(messages, 1):
                # Get user information
                user_id = message.get('user')
                username = self._get_user_display_name(user_id) if user_id else "Unknown User"
                
                # Get timestamp
                ts = message.get('ts', '0')
                try:
                    timestamp = datetime.datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    timestamp = "Unknown Time"
                
                # Get message text
                text = message.get('text', '')
                formatted_text = self._clean_message_text(text)
                
                # Format message entry
                lines.append(f"[{i}] {username} - {timestamp}")
                lines.append("-" * 40)
                lines.append(formatted_text)
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.log.error(f"Error creating text file content: {e}")
            return f"Error creating text content: {str(e)}"

    def _get_user_display_name(self, user_id):
        """Get user display name with caching."""
        if not user_id:
            return "Unknown User"
        
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
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
        """Clean and format message text for the text file."""
        if not text:
            return "[No text content]"
        
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
            
            # Clean up special characters and formatting
            text = text.replace('\n', '\n    ')  # Indent new lines
            
            return text.strip()
            
        except Exception as e:
            self.log.warning(f"Error cleaning message text: {e}")
            return text

    def _upload_text_file(self, channel, thread_ts, content):
        """Upload the text content as a file to Slack."""
        try:
            slack_client = getattr(self._bot, 'slack_web', None)
            if not slack_client:
                self.log.error("Slack client not available for file upload")
                return False
            
            # Create filename with timestamp
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"thread_extract_{timestamp}.txt"
            
            # Try modern uploadV2 method first
            try:
                response = slack_client.files_upload_v2(
                    channel=channel,
                    file=content.encode('utf-8'),
                    filename=filename,
                    title=f"Thread Extract - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    thread_ts=thread_ts
                )
                
                if response and response.get('ok'):
                    self.log.info(f"✅ File uploaded successfully: {filename}")
                    return True
                else:
                    self.log.warning(f"Upload failed: {response.get('error', 'unknown error') if response else 'no response'}")
            except Exception as e:
                self.log.warning(f"Upload v2 failed: {e}")
            
            # Fallback: post as code block if file upload fails
            try:
                max_length = 3500
                if len(content) <= max_length:
                    message_text = f"📄 **{filename}**\n\n```\n{content}\n```"
                else:
                    truncated_content = content[:max_length]
                    message_text = f"📄 **{filename}** (truncated)\n\n```\n{truncated_content}\n...\n```"
                
                response = slack_client.chat_postMessage(
                    channel=channel,
                    text=message_text,
                    thread_ts=thread_ts
                )
                
                if response.get('ok'):
                    self.log.info("✅ Posted as code block message")
                    return True
                    
            except Exception as e:
                self.log.error(f"Fallback posting failed: {e}")
            
            return False
                
        except Exception as e:
            self.log.error(f"Critical error in file upload: {e}")
            return False
