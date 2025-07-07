import json
import logging
from errbot import BotPlugin


class SlackV3BlocksExtension(BotPlugin):
    """
    Extension plugin to add Slack blocks and interactive components support 
    to SlackV3 backend via websocket mode.
    """

    def activate(self):
        """Activate the extension."""
        super().activate()
        self.log.info("Activating SlackV3 Blocks Extension...")
        self._patch_backend()
        self.log.info("Extension activated - blocks support available via helper methods")

    def deactivate(self):
        """Deactivate the plugin and restore original backend"""
        self._unpatch_backend()
        super().deactivate()
        self.log.info("SlackV3BlocksExtension plugin deactivated")

    def send_blocks_to_channel(self, channel, blocks, text=""):
        """Send blocks to a specific channel."""
        try:
            self.log.info(f"🔵 send_blocks_to_channel called with channel={channel}, text={text}, blocks={len(blocks) if blocks else 0} blocks")
            
            # Get the bot instance and check its type
            bot = self._bot
            self.log.info(f"Bot type: {type(bot)}")
            self.log.info(f"Bot attributes: {[attr for attr in dir(bot) if not attr.startswith('_')]}")
            
            # The bot itself might be the backend or have backend attribute
            backend = None
            if hasattr(bot, 'backend'):
                backend = bot.backend
                self.log.info(f"Backend type: {type(backend)}")
            else:
                # The bot itself might be the backend
                backend = bot
                self.log.info(f"Using bot as backend, type: {type(backend)}")
            
            self.log.info(f"Backend attributes: {[attr for attr in dir(backend) if not attr.startswith('_')]}")
            
            # Try different ways to access the Slack client
            slack_client = None
            
            # Check for web client attributes
            for attr in ['web_client', 'slack_web', '_slack_client', 'client', 'slack_client', '_web_client']:
                if hasattr(backend, attr):
                    client = getattr(backend, attr)
                    self.log.info(f"Found attribute {attr}: {type(client)}")
                    if client and hasattr(client, 'chat_postMessage'):
                        slack_client = client
                        self.log.info(f"Using {attr} as Slack client")
                        break
            
            if slack_client:
                self.log.info(f"✅ Attempting to send blocks to channel {channel}")
                self.log.info(f"Blocks to send: {json.dumps(blocks, indent=2) if blocks else 'None'}")
                response = slack_client.chat_postMessage(
                    channel=channel,
                    text=text,
                    blocks=blocks or []
                )
                self.log.info(f"✅ Slack API response: {response}")
                
                # Check if response indicates success
                if hasattr(response, 'get') and response.get('ok'):
                    self.log.info("✅ Slack API returned success")
                    return response
                elif hasattr(response, 'status_code') and response.status_code == 200:
                    self.log.info("✅ HTTP status indicates success")
                    return response
                else:
                    self.log.warn(f"⚠️ Unclear response status: {response}")
                    return response
            else:
                self.log.error("❌ No Slack client with chat_postMessage method found")
                self.log.error("Available backend attributes: " + ', '.join([attr for attr in dir(backend) if not attr.startswith('_')]))
                return None
                
        except Exception as e:
            self.log.error(f"Error sending blocks to channel: {e}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")
            return None

    def send_blocks_to_message(self, message, blocks, text=""):
        """Send blocks in response to a message."""
        try:
            # Extract channel from message
            channel = None
            if hasattr(message.frm, 'channelid'):
                channel = message.frm.channelid
            elif hasattr(message.frm, 'id'):
                channel = message.frm.id
            else:
                channel = str(message.frm)
            
            return self.send_blocks_to_channel(channel, blocks, text)
            
        except Exception as e:
            self.log.error(f"Error sending blocks to message: {e}")
            return None
    # ... existing code ...

    def _create_fake_message_from_payload(self, payload):
        """Create a fake message object from interactive payload."""
        try:
            # Create fake person and room objects
            user_info = payload.get('user', {})
            channel_info = payload.get('channel', {})
            
            fake_person = type('FakePerson', (), {
                'userid': user_info.get('id', 'unknown'),
                'username': user_info.get('username', user_info.get('name', 'unknown')),
                'channelid': channel_info.get('id', 'unknown'),
                'id': channel_info.get('id', 'unknown')
            })()
            
            # Create fake message
            fake_message = type('FakeMessage', (), {
                'frm': fake_person,
                'to': fake_person,
                'body': f"Interactive component action",
                'json': {'payload': payload}
            })()
            
            return fake_message
            
        except Exception as e:
            self.log.error(f"Error creating fake message: {e}")
            return None

    def _patch_backend(self):
        """Patch the SlackV3 backend to handle block_actions"""
        try:
            # In ErrBot, self._bot IS the backend
            backend = self._bot
            
            # Store original method if not already stored
            if not hasattr(backend, '_original_generic_wrapper'):
                original_method = getattr(backend, '_generic_wrapper', None)
                backend._original_generic_wrapper = original_method
                self.log.info(f"Found original _generic_wrapper: {original_method}")
            
            # Create a closure that captures the extension instance
            extension = self
            original_wrapper = backend._original_generic_wrapper
            
            def patched_wrapper(event_data):
                return extension._patched_generic_wrapper(backend, event_data, original_wrapper)
            
            # Replace the method
            backend._generic_wrapper = patched_wrapper
            
            self.log.info("✅ Successfully patched SlackV3 backend _generic_wrapper to handle interactive events")
            
            # Verify the patch is in place
            current_method = getattr(backend, '_generic_wrapper', None)
            self.log.info(f"Current _generic_wrapper method after patch: {current_method}")
            
        except Exception as e:
            self.log.error(f"❌ Failed to patch SlackV3 backend: {e}")
            # Debug information
            self.log.error(f"Bot object type: {type(self._bot)}")
            self.log.error(f"Available methods: {[attr for attr in dir(self._bot) if 'generic' in attr.lower()]}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")

    def _unpatch_backend(self):
        """Restore original backend functionality"""
        try:
            backend = self._bot
            if hasattr(backend, '_original_generic_wrapper'):
                backend._generic_wrapper = backend._original_generic_wrapper
                delattr(backend, '_original_generic_wrapper')
                self.log.info("✅ Successfully restored original SlackV3 backend _generic_wrapper")
        except Exception as e:
            self.log.error(f"❌ Failed to unpatch SlackV3 backend: {e}")

    def _patched_generic_wrapper(self, backend, event_data, original_wrapper):
        """Patched generic event wrapper to handle interactive events"""
        try:
            self.log.info(f"🚀 PATCHED _generic_wrapper CALLED! Event data keys: {list(event_data.keys()) if event_data else 'None'}")
            self.log.debug(f"🔍 Patched wrapper - Full event data: {event_data}")
            
            # Check if this is an interactive event (block_actions, etc.)
            if 'type' in event_data and event_data['type'] in ['block_actions', 'interactive_message', 'message_action']:
                self.log.info(f"✅ Handling interactive event: {event_data['type']}")
                interactive_type = event_data['type']
                result = self._handle_interactive_event(interactive_type, event_data)
                if result:
                    return result
                else:
                    self.log.info(f"ℹ️ Interactive event {interactive_type} processed but no plugin handled it")
                    return None
            
            # For regular events, use the original logic
            self.log.info(f"🔄 Processing as regular event")
            
            # Call the original _generic_wrapper method
            if original_wrapper:
                return original_wrapper(event_data)
            else:
                # Fallback to original logic from _generic_wrapper
                try:
                    event = event_data["event"]
                    event_type = event["type"]

                    try:
                        event_handler = getattr(backend, f"_handle_{event_type}")
                        return event_handler(backend.slack_web, event)
                    except AttributeError:
                        self.log.debug(f"Event type {event_type} not supported.")
                except KeyError:
                    # This is where the "Ignoring unsupported Slack event!" used to come from
                    # But now we've already handled interactive events above
                    self.log.debug("Event has no 'event' key - might be a different event structure")
                    self.log.debug(f"Event structure: {event_data}")
            
        except Exception as e:
            self.log.error(f"❌ Error in patched generic wrapper: {e}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")
        
        return None

    def _handle_interactive_event(self, event_type, payload):
        """Handle interactive events by routing to appropriate plugins"""
        try:
            self.log.info(f"🎯 Routing {event_type} event to plugins")
            self.log.info(f"Payload keys: {list(payload.keys())}")
            
            # Initialize action variables
            action_id = None
            action_value = None
            
            # Extract action information for block_actions
            if event_type == 'block_actions':
                actions = payload.get('actions', [])
                if actions:
                    action = actions[0]  # Use first action
                    action_id = action.get('action_id')
                    action_value = action.get('value')
                    self.log.info(f"Extracted action_id: {action_id}, value: {action_value}")
                else:
                    self.log.warn("No actions found in block_actions event")
                    return None
            
            handled = False
            
            # Get all active plugins
            active_plugins = self._bot.plugin_manager.get_all_active_plugins()
            
            for plugin in active_plugins:
                # Skip self to avoid infinite recursion
                if plugin.__class__.__name__ == 'SlackV3BlocksExtension':
                    continue
                
                # Try different callback method names
                callback_methods = [
                    'handle_block_action',          # Our NameCollector uses this
                    f'callback_{event_type}',       # e.g., callback_block_actions  
                    'callback_interactive',         # Generic interactive handler
                    'callback_interactive_component' # Alternative name
                ]
                
                for method_name in callback_methods:
                    if hasattr(plugin, method_name):
                        try:
                            callback = getattr(plugin, method_name)
                            plugin_name = plugin.__class__.__name__
                            self.log.info(f"📞 Calling {plugin_name}.{method_name}")
                            
                            # Call the plugin's handler with correct parameters
                            if method_name == 'handle_block_action':
                                # NameCollector expects: handle_block_action(action_id, value, payload, message)
                                fake_message = self._create_fake_message_from_payload(payload)
                                result = callback(action_id, action_value, payload, fake_message)
                            else:
                                result = callback(payload)
                                
                            if result:
                                self.log.info(f"✅ Interactive event {event_type} handled by {plugin_name}.{method_name}")
                                handled = True
                                # Don't return here - let other plugins also handle their actions
                                # return result  # REMOVED: This was causing the bug!
                                
                        except Exception as e:
                            plugin_name = plugin.__class__.__name__
                            self.log.error(f"❌ Error in {plugin_name}.{method_name}: {e}")
                            import traceback
                            self.log.error(f"Traceback: {traceback.format_exc()}")
            
            if not handled:
                self.log.info(f"ℹ️ No plugin handled the {event_type} event")
            
        except Exception as e:
            self.log.error(f"❌ Error handling interactive event {event_type}: {e}")
            import traceback
            self.log.error(f"Traceback: {traceback.format_exc()}")
        
        return None

    # Static helper methods for other plugins to use
    @staticmethod
    def get_extension_instance(bot):
        """Get the SlackV3BlocksExtension instance."""
        for plugin in bot.plugin_manager.get_all_active_plugins():
            if isinstance(plugin, SlackV3BlocksExtension):
                return plugin
        return None

    @staticmethod
    def send_blocks_static(bot, channel, blocks, text=""):
        """Static helper method to send blocks to a channel."""
        extension = SlackV3BlocksExtension.get_extension_instance(bot)
        if extension:
            return extension.send_blocks_to_channel(channel, blocks, text)
        else:
            logging.error("SlackV3BlocksExtension not found or not active")
            return None

    @staticmethod
    def send_blocks_to_message_static(bot, message, blocks, text=""):
        """Static helper method to send blocks in response to a message."""
        extension = SlackV3BlocksExtension.get_extension_instance(bot)
        if extension:
            return extension.send_blocks_to_message(message, blocks, text)
        else:
            logging.error("SlackV3BlocksExtension not found or not active")
            return None
