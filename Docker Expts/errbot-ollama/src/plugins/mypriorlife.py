from errbot import BotPlugin, botcmd
import logging

BLOCKS_PRIORLIFE = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ":mag: What were you in *Prior Life*"
        }
    },
    {
        "type": "input",
        "block_id": "prior_life_input_block",
        "element": {
            "type": "plain_text_input",
            "action_id": "plain_text_input-action",
            "placeholder": {
                "type": "plain_text",
                "text": "Enter your prior life here..."
            }
        },
        "label": {
            "type": "plain_text",
            "text": "Your Prior Life",
            "emoji": True
        }
    },
    {
        "type": "actions",
        "block_id": "prior_life_actions_block",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Submit",
                    "emoji": True
                },
                "value": "click_me_123",
                "action_id": "actionId-0",
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
                "action_id": "actionId-cancel"
            }
        ]
    }
]

class MyPriorLife(BotPlugin):
    def activate(self):
        super().activate()
        if 'collected_prior_lives' not in self:
            self['collected_prior_lives'] = []
        self.log.info("MyPriorLife plugin activated with prior lives storage")
        # Fetch and cache bot user ID for reaction handling
        slack_client = getattr(self._bot, 'slack_web', None)
        self._bot_user_id = None
        if slack_client:
            try:
                auth_info = slack_client.auth_test()
                self._bot_user_id = auth_info.get('user_id')
                self.log.info(f"Cached bot user ID: {self._bot_user_id}")
            except Exception as e:
                self.log.error(f"Failed to fetch bot user ID: {e}")

    def _cache_bot_user_id(self):
        """Fetch and cache the bot's Slack user ID using the Slack API."""
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            self.log.warning("Slack client not available for bot user ID fetch")
            return
        try:
            auth_info = slack_client.auth_test()
            self._bot_user_id = auth_info.get('user_id')
            self.log.info(f"Fetched and cached bot user ID: {self._bot_user_id}")
        except Exception as e:
            self.log.error(f"Failed to fetch bot user ID: {e}")

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
                channel = channel[2:].split('|')[0].split('>')[0]
            
        self.log.info(f"Sending message to channel: {channel}, thread_ts: {thread_ts}")
        self.log.info(f"Message text: {text}")
        
        try:
            if blocks:
                response = slack_client.chat_postMessage(
                    channel=channel,
                    blocks=blocks,
                    text=text,
                    thread_ts=thread_ts
                )
            else:
                response = slack_client.chat_postMessage(
                    channel=channel,
                    text=text,
                    thread_ts=thread_ts
                )
            self.log.info(f"Successfully sent message to channel {channel}")
            self.log.info(f"Slack API response: {response}")
            return f"Message sent to {channel}"
        except Exception as e:
            self.log.error(f"Failed to send message to {channel}: {e}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")
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
        """Handle Slack block interactive actions for prior life form"""
        try:
            self.log.info("=" * 50)
            self.log.info("🔥 MYPRIORLIFE HANDLE_BLOCK_ACTION CALLED!")
            self.log.info(f"MyPriorLife handling block action: action_id={action_id}, value={value}")
            self.log.info(f"Payload keys: {list(payload.keys()) if payload else 'None'}")
            self.log.info(f"Full payload: {payload}")
            self.log.info("=" * 50)
            
            if action_id == 'actionId-0':  # Submit button
                self.log.info("✅ Processing actionId-0 (Submit button)")
                # Extract the input value
                state_values = payload.get('state', {}).get('values', {})
                self.log.info(f"State values: {state_values}")
                input_value = None
                
                for block_id, block_data in state_values.items():
                    self.log.info(f"Processing block_id: {block_id}, block_data: {block_data}")
                    for element_id, element_data in block_data.items():
                        self.log.info(f"Processing element_id: {element_id}, element_data: {element_data}")
                        if element_id == 'plain_text_input-action':
                            input_value = element_data.get('value', '').strip()
                            self.log.info(f"Found input value: '{input_value}'")
                            break
                    if input_value:
                        break
                
                if input_value:
                    # Store the prior life response
                    user_id = payload.get('user', {}).get('id', 'Unknown')
                    user_name = payload.get('user', {}).get('name', user_id)
                    
                    prior_life_entry = {
                        'user_id': user_id,
                        'user_name': user_name,
                        'prior_life': input_value
                    }
                    
                    current_prior_lives = self.get('collected_prior_lives', [])
                    current_prior_lives.append(prior_life_entry)
                    self['collected_prior_lives'] = current_prior_lives
                    
                    self.log.info(f"Stored prior life for {user_name}: {input_value}")
                    
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
                                "text": f"🎭 **Prior Life Submitted!** {user_name} was a **{input_value}** in their prior life! ✨"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"📊 Total prior lives collected: *{len(current_prior_lives)}* | 🔄 Use `!mypriorlife` to submit another"
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
                        text=f"🎭 Prior Life Submitted! {user_name} was a {input_value} in their prior life!",
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
                                "text": "❌ **Error:** Please enter your prior life before submitting!"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "🔄 Use `!mypriorlife` to try again | 🗑️ *Form removed due to invalid submission*"
                                }
                            ]
                        }
                    ]
                    
                    # Update original message to show error and remove form
                    self._update_original_message(
                        blocks=error_blocks,
                        text="❌ Error: Please enter your prior life before submitting!",
                        channel=channel,
                        message_ts=message_ts
                    )
            
            elif action_id == 'actionId-cancel':  # Cancel button
                self.log.info("✅ Processing actionId-cancel (Cancel button)")
                channel = payload.get('channel', {}).get('id')
                message_ts = payload.get('container', {}).get('message_ts')
                thread_ts = payload.get('message', {}).get('thread_ts')
                
                cancel_blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "❌ **Cancelled** - Prior life form was cancelled."
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "🔄 Use `!mypriorlife` to start again | 🗑️ *Form has been removed*"
                            }
                        ]
                    }
                ]
                
                # Update original message to show cancellation and remove form
                self._update_original_message(
                    blocks=cancel_blocks,
                    text="❌ Cancelled - Prior life form was cancelled.",
                    channel=channel,
                    message_ts=message_ts
                )
            
            else:
                self.log.info(f"Unknown action_id: {action_id}")
            
            return True  # Indicate that we handled the action
            
        except Exception as e:
            self.log.error(f"Error handling block action in MyPriorLife: {e}")
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
    def plc(self, msg, args):
        """Display collected prior life responses"""
        collected_prior_lives = self.get('collected_prior_lives', [])
        
        if not collected_prior_lives:
            return "No prior life responses have been collected yet."
        
        response = "📜 **Collected Prior Life Responses:**\n\n"
        for i, entry in enumerate(collected_prior_lives, 1):
            user_name = entry.get('user_name', 'Unknown')
            prior_life = entry.get('prior_life', 'Unknown')
            response += f"{i}. **{user_name}**: {prior_life}\n"
        
        return response

    @botcmd
    def plclear(self, msg, args):
        """Clear all collected prior life responses"""
        self['collected_prior_lives'] = []
        return "✅ All prior life responses have been cleared."
    
    @botcmd
    def pltest(self, msg, args):
        """Test command to verify the plugin is working and show debug info"""
        slack_client = getattr(self._bot, 'slack_web', None)
        
        extension_loaded = False
        for plugin in self._bot.plugin_manager.get_all_active_plugins():
            if plugin.__class__.__name__ == 'SlackV3BlocksExtension':
                extension_loaded = True
                break
        
        debug_info = [
            f"Plugin Status: Active",
            f"Slack Client Available: {'Yes' if slack_client else 'No'}",
            f"SlackV3BlocksExtension Loaded: {'Yes' if extension_loaded else 'No'}",
            f"Stored Prior Lives: {len(self.get('collected_prior_lives', []))}",
            f"Bot Type: {type(self._bot)}",
            f"Available Plugins: {[p.__class__.__name__ for p in self._bot.plugin_manager.get_all_active_plugins()]}",
            f"Message Extras: {msg.extras if hasattr(msg, 'extras') else 'N/A'}"
        ]
        
        return "🔧 **MyPriorLife Plugin Debug Info:**\n" + "\n".join(debug_info)
    
    @botcmd  
    def plmanualtest(self, msg, args):
        """Manually test the block action handler"""
        self.log.info("Manual test of handle_block_action called")
        
        fake_payload = {
            'type': 'block_actions',
            'user': {'id': 'U123TEST', 'name': 'TestUser'},
            'channel': {'id': 'C123TEST'},
            'message': {'thread_ts': '1234567890.123'},
            'state': {
                'values': {
                    'prior_life_input_block': {
                        'plain_text_input-action': {
                            'value': 'Test Prior Life Value'
                        }
                    }
                }
            }
        }
        
        try:
            result = self.handle_block_action('actionId-0', 'click_me_123', fake_payload, msg)
            return f"✅ Manual test completed. Result: {result}"
        except Exception as e:
            self.log.error(f"Manual test failed: {e}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ Manual test failed: {str(e)}"

    @botcmd
    def mypriorlife(self, msg, args):
        """Responds with 'In My Prior Life I was a Cat ! Now I am a Bot!' and shows the form"""
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            return "Slack client not available. This message is only for slack."
        
        slack_event = msg.extras.get('slack_event', {})
        channel = slack_event.get('channel')
        ts = slack_event.get('ts')
        
        if not channel or not ts:
            return f"Cannot find channel or timestamp for threading. msg.extras: {msg.extras}"
        
        return_msg = "In My Prior Life I was a Cat ! Now I am a Bot!"
        
        try:
            slack_client.chat_postMessage(
                channel=channel,
                text=return_msg,
                thread_ts=ts,
                reply_broadcast=True
            )
            slack_client.chat_postMessage(
                channel=channel,
                blocks=BLOCKS_PRIORLIFE,
                text="What was your prior life?",
                thread_ts=ts,
                reply_broadcast=True
            )
            self.log.info(f"Sent prior life form to channel {channel}")
            return None
        except Exception as e:
            self.log.error(f"Error sending prior life form: {e}")
            return f"Error sending form: {str(e)}"

    def callback_reaction_added(self, event):
        """
        Respond to :pl: reaction on any message sent by the bot.
        """
        if event.get('reaction') == 'pl':
            item = event.get('item', {})
            channel = item.get('channel')
            message_ts = item.get('ts')
            slack_client = getattr(self._bot, 'slack_web', None)
            # Use cached bot user ID, fetch if not set
            bot_user_id = getattr(self, '_bot_user_id', None)
            if not bot_user_id and slack_client:
                try:
                    auth_info = slack_client.auth_test()
                    bot_user_id = auth_info.get('user_id')
                    self._bot_user_id = bot_user_id
                    self.log.info(f"Fetched bot user ID at runtime: {bot_user_id}")
                except Exception as e:
                    self.log.error(f"Failed to fetch bot user ID at runtime: {e}")
            item_user = event.get('item_user')

            self.log.info(f"DEBUG: callback_reaction_added: bot_user_id={bot_user_id}, item_user={item_user}, channel={channel}, message_ts={message_ts}")

            if channel and message_ts and slack_client and bot_user_id:
                if item_user == bot_user_id:
                    try:
                        slack_client.chat_postMessage(
                            channel=channel,
                            text="Thanks for liking this function.",
                            thread_ts=message_ts
                        )
                    except Exception as e:
                        self.log.error(f"Failed to send thanks for :pl: reaction: {e}")
                    return True  # Always return True if you handled the event
        return False  # Explicitly return False if not handled