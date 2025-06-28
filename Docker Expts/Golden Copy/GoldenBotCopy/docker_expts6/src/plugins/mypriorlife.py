
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
		"block_id": "prior_life_input_block",  # Added explicit block_id
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
		"block_id": "prior_life_actions_block",  # Added explicit block_id
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
				"style": "primary"  # Make it more visible
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
            
        self.log.info(f"Sending message to channel: {channel}, thread_ts: {thread_ts}")
        self.log.info(f"Message text: {text}")
        
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
            self.log.info(f"Slack API response: {response}")
            return f"Message sent to {channel}"
        except Exception as e:
            self.log.error(f"Failed to send message to {channel}: {e}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")
            return f"Failed to send message: {str(e)}"

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
                    
                    # Send confirmation with more visibility
                    channel = payload.get('channel', {}).get('id')
                    thread_ts = payload.get('message', {}).get('thread_ts')
                    
                    confirmation_text = f"✅ Thanks {user_name}! Your prior life as '{input_value}' has been recorded."
                    
                    # Try to send response both in thread and as a visible message
                    self.log.info(f"Sending confirmation: {confirmation_text}")
                    self._send_response_blocks(
                        text=confirmation_text,
                        channel=channel,
                        thread_ts=thread_ts
                    )
                    
                    # Also send a message that shows the submitted value prominently
                    display_text = f"🎭 **Prior Life Submitted:** {user_name} was a **{input_value}** in their prior life!"
                    self._send_response_blocks(
                        text=display_text,
                        channel=channel
                    )
                else:
                    # Send error for empty input
                    channel = payload.get('channel', {}).get('id')
                    thread_ts = payload.get('message', {}).get('thread_ts')
                    
                    error_text = "❌ Please enter your prior life before submitting."
                    self._send_response_blocks(
                        text=error_text,
                        channel=channel,
                        thread_ts=thread_ts
                    )
            
            elif action_id == 'actionId-cancel':  # Cancel button
                self.log.info("✅ Processing actionId-cancel (Cancel button)")
                channel = payload.get('channel', {}).get('id')
                thread_ts = payload.get('message', {}).get('thread_ts')
                
                cancel_text = "❌ Prior life form cancelled."
                self._send_response_blocks(
                    text=cancel_text,
                    channel=channel,
                    thread_ts=thread_ts
                )
            
            else:
                self.log.info(f"Unknown action_id: {action_id}")
            
            return True  # Indicate that we handled the action
            
        except Exception as e:
            self.log.error(f"Error handling block action in MyPriorLife: {e}")
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
        
        # Check if SlackV3BlocksExtension is loaded
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
        
        # Create a fake payload to test the handler
        fake_payload = {
            'type': 'block_actions',
            'user': {'id': 'U123TEST', 'name': 'TestUser'},
            'channel': {'id': 'C123TEST'},
            'message': {'thread_ts': '1234567890.123'},
            'state': {
                'values': {
                    'prior_life_input_block': {  # Use the correct block_id
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
            # Send the initial message
            slack_client.chat_postMessage(
                channel=channel,
                text=return_msg,
                thread_ts=ts,
                reply_broadcast=True
            )
            
            # Send the form blocks
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