from errbot import BotPlugin, botcmd
import logging

# Slack blocks for the name collection form
BLOCKS_NAME_COLLECTION = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ":memo: Please enter your *Name* below"
        }
    },
    {
        "type": "input",
        "block_id": "name_input_block",
        "element": {
            "type": "plain_text_input",
            "action_id": "name_input_field",
            "placeholder": {
                "type": "plain_text",
                "text": "Enter your name here..."
            },
            "max_length": 100
        },
        "label": {
            "type": "plain_text",
            "text": "Your Name",
            "emoji": True
        }
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Submit Name",
                    "emoji": True
                },
                "style": "primary",
                "value": "submit_name",
                "action_id": "submit_name_button"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Cancel",
                    "emoji": True
                },
                "value": "cancel",
                "action_id": "cancel_name_button"
            }
        ]
    }
]

class SimpleNameCollector(BotPlugin):
    """A simple name collector plugin that uses direct Slack client access."""
    
    def activate(self):
        """Initialize the plugin and set up storage."""
        super().activate()
        if 'collected_names' not in self:
            self['collected_names'] = []
        self.log.info("SimpleNameCollector plugin activated with names storage")

    def _send_response_blocks(self, blocks=None, text="", channel=None, thread_ts=None):
        """Helper to send blocks or fallback text with proper channel formatting"""
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            self.log.warning("Slack client not available")
            return "Slack client not available"
        
        if not channel:
            self.log.warning("No channel provided for response")
            return "No channel available"
        
        # Ensure channel has proper format
        if not channel.startswith('#') and not channel.startswith('C'):
            if channel.startswith('<#') and channel.endswith('>'):
                # Extract channel ID from <#C1234567890|channel-name> format
                channel = channel[2:].split('|')[0].split('>')[0]
            
        try:
            if blocks:
                response = slack_client.chat_postMessage(
                    channel=channel,
                    blocks=blocks,
                    text=text,  # Fallback text
                    thread_ts=thread_ts
                )
            else:
                response = slack_client.chat_postMessage(
                    channel=channel,
                    text=text,
                    thread_ts=thread_ts
                )
            self.log.info(f"Successfully sent message to channel {channel}")
            return f"Message sent to {channel}"
        except Exception as e:
            self.log.error(f"Failed to send message to {channel}: {e}")
            return f"Failed to send message: {str(e)}"

    def _update_original_message(self, blocks=None, text="", channel=None, message_ts=None):
        """Helper to update/replace the original message (destroys the form)"""
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            self.log.warning("Slack client not available for message update")
            return False
        
        if not channel or not message_ts:
            self.log.warning("Channel or message timestamp missing for update")
            return False
            
        try:
            response = slack_client.chat_update(
                channel=channel,
                ts=message_ts,
                blocks=blocks or [],
                text=text
            )
            self.log.info(f"Successfully updated original message in channel {channel}")
            return True
        except Exception as e:
            self.log.error(f"Failed to update original message: {e}")
            return False

    def handle_block_action(self, action_id, value, payload, message):
        """Handle Slack block interactive actions for name collection form"""
        try:
            self.log.info(f"SimpleNameCollector handling block action: action_id={action_id}, value={value}")
            self.log.info(f"Full payload keys: {list(payload.keys()) if payload else 'None'}")
            
            if action_id == 'submit_name_button':  # Submit button
                self.log.info("Processing submit_name_button action")
                
                # Extract the input value from the form
                state_values = payload.get('state', {}).get('values', {})
                self.log.info(f"State values: {state_values}")
                
                name_input_block = state_values.get('name_input_block', {})
                name_input_field = name_input_block.get('name_input_field', {})
                user_name = name_input_field.get('value', '').strip()
                
                self.log.info(f"Extracted user name: '{user_name}'")
                
                if user_name:
                    # Store the name
                    user_id = payload.get('user', {}).get('id', 'Unknown')
                    slack_user_name = payload.get('user', {}).get('name', user_id)
                    
                    name_entry = {
                        'user_id': user_id,
                        'slack_user_name': slack_user_name,
                        'submitted_name': user_name
                    }
                    
                    current_names = self.get('collected_names', [])
                    
                    # Check if this user already submitted a name
                    existing_entry = None
                    for i, entry in enumerate(current_names):
                        if entry.get('user_id') == user_id:
                            existing_entry = i
                            break
                    
                    if existing_entry is not None:
                        # Update existing entry
                        current_names[existing_entry] = name_entry
                        action_text = "updated"
                    else:
                        # Add new entry
                        current_names.append(name_entry)
                        action_text = "added"
                    
                    self['collected_names'] = current_names
                    
                    self.log.info(f"Stored name for {slack_user_name}: {user_name}")
                    
                    # Get message info for updating the original form
                    channel = payload.get('channel', {}).get('id')
                    message_ts = payload.get('container', {}).get('message_ts')
                    thread_ts = payload.get('message', {}).get('thread_ts')
                    
                    # Create success blocks to replace the form
                    success_blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ **Success!** Hello **{user_name}**! Your name has been {action_text} to our collection. 🎉"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"📊 Total names in collection: *{len(current_names)}* | 🔄 Use `!collect_name` to submit another name"
                                }
                            ]
                        },
                        {
                            "type": "divider"
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "🗑️ *Form has been automatically removed after submission*"
                            }
                        }
                    ]
                    
                    # Update the original message (destroys the form)
                    form_updated = self._update_original_message(
                        blocks=success_blocks,
                        text=f"✅ Success! Hello {user_name}! Your name has been {action_text}.",
                        channel=channel,
                        message_ts=message_ts
                    )
                else:
                    # Send error for empty input and destroy form
                    channel = payload.get('channel', {}).get('id')
                    message_ts = payload.get('container', {}).get('message_ts')
                    thread_ts = payload.get('message', {}).get('thread_ts')
                    
                    error_blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "❌ **Error:** Please enter a valid name before submitting!"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "🔄 Use `!collect_name` to try again | 🗑️ *Form removed due to invalid submission*"
                                }
                            ]
                        }
                    ]
                    
                    # Update original message to show error and remove form
                    self._update_original_message(
                        blocks=error_blocks,
                        text="❌ Error: Please enter a valid name before submitting!",
                        channel=channel,
                        message_ts=message_ts
                    )
                    
            elif action_id == 'cancel_name_button':  # Cancel button
                self.log.info("Processing cancel_name_button action")
                
                channel = payload.get('channel', {}).get('id')
                message_ts = payload.get('container', {}).get('message_ts')
                thread_ts = payload.get('message', {}).get('thread_ts')
                
                cancel_blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "❌ **Cancelled** - Name collection form was cancelled."
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "🔄 Use `!collect_name` to start again | 🗑️ *Form has been removed*"
                            }
                        ]
                    }
                ]
                
                # Update original message to show cancellation and remove form
                self._update_original_message(
                    blocks=cancel_blocks,
                    text="❌ Cancelled - Name collection form was cancelled.",
                    channel=channel,
                    message_ts=message_ts
                )
            
            return True  # Indicate that we handled the action
            
        except Exception as e:
            self.log.error(f"Error handling block action in SimpleNameCollector: {e}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")
            
            # Try to send error message if possible
            try:
                channel = payload.get('channel', {}).get('id')
                thread_ts = payload.get('message', {}).get('thread_ts')
                if channel:
                    self._send_response_blocks(
                        text=f"❌ Error processing your submission: {str(e)}",
                        channel=channel,
                        thread_ts=thread_ts
                    )
            except:
                pass
            return False

    @botcmd
    def names_list(self, msg, args):
        """Display all collected names"""
        collected_names = self.get('collected_names', [])
        
        if not collected_names:
            return "📝 No names have been collected yet. Use `!collect_name` to start collecting names!"
        
        response = f"👥 **Collected Names ({len(collected_names)}):**\n\n"
        for i, entry in enumerate(collected_names, 1):
            submitted_name = entry.get('submitted_name', 'Unknown')
            slack_user = entry.get('slack_user_name', 'Unknown')
            response += f"{i}. **{submitted_name}** *(submitted by {slack_user})*\n"
        
        return response

    @botcmd  
    def collect_name(self, msg, args):
        """Show the name collection form using Slack blocks"""
        # Check if we have access to Slack client
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            return "❌ Slack client not available. This command only works in Slack."
        
        # Get channel and timestamp info from the message
        slack_event = msg.extras.get('slack_event', {})
        channel = slack_event.get('channel')
        ts = slack_event.get('ts')
        
        if not channel or not ts:
            return f"❌ Cannot find channel or timestamp for threading. msg.extras: {msg.extras}"
        
        try:
            # Send introduction message
            intro_text = "📝 **Name Collection Form**\nPlease fill out the form below to add your name to our collection!"
            
            slack_client.chat_postMessage(
                channel=channel,
                text=intro_text,
                thread_ts=ts,
                reply_broadcast=True
            )
            
            # Send the form blocks
            slack_client.chat_postMessage(
                channel=channel,
                blocks=BLOCKS_NAME_COLLECTION,
                text="Name collection form - please enter your name",
                thread_ts=ts,
                reply_broadcast=True
            )
            
            self.log.info(f"Sent name collection form to channel {channel}")
            return None  # Don't return anything since we sent the blocks
            
        except Exception as e:
            self.log.error(f"Error sending name collection form: {e}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ Error sending form: {str(e)}"

    @botcmd
    def clear_names(self, msg, args):
        """Clear all collected names (admin function)"""
        self['collected_names'] = []
        self.log.info("Cleared all collected names")
        return "🗑️ **Cleared** - All collected names have been removed from storage."
