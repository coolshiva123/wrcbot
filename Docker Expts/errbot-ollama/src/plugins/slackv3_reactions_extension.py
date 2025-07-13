from errbot import BotPlugin

class SlackV3ReactionsExtension(BotPlugin):
    """
    Extension to patch SlackV3 backend to handle Slack reaction events.
    """

    def activate(self):
        super().activate()
        self.log.info("Activating SlackV3 Reactions Extension...")
        backend = self._bot  # FIXED: use self._bot directly
        if hasattr(backend, "_generic_wrapper"):
            self._patch_backend(backend)
        else:
            self.log.error("Slack backend does not have _generic_wrapper method.")

    def _patch_backend(self, backend):
        original_wrapper = backend._generic_wrapper

        def patched_wrapper(event_data):
            # Handle reaction events
            if 'event' in event_data:
                event = event_data['event']
                event_type = event.get('type')
                if event_type in ['reaction_added', 'reaction_removed']:
                    self.log.info(f"Handling Slack reaction event: {event_type}")
                    self._handle_reaction_event(event_type, event)
                    return None
            # Fallback to original logic
            return original_wrapper(event_data)

        backend._generic_wrapper = patched_wrapper
        self.log.info("✅ Successfully patched SlackV3 backend _generic_wrapper to handle reaction events.")

    def _handle_reaction_event(self, event_type, event):
        """
        Route Slack reaction events to plugins.
        """
        try:
            self.log.info(f"Routing {event_type} to plugins. Reaction: {event.get('reaction')}, User: {event.get('user')}")
            handled = False
            active_plugins = self._bot.plugin_manager.get_all_active_plugins()
            for plugin in active_plugins:
                # Skip self to avoid recursion
                if plugin.__class__.__name__ == 'SlackV3ReactionsExtension':
                    continue
                callback_methods = [
                    f'callback_{event_type}',      # e.g., callback_reaction_added
                    'callback_reaction',           # generic
                ]
                for method_name in callback_methods:
                    if hasattr(plugin, method_name):
                        try:
                            callback = getattr(plugin, method_name)
                            plugin_name = plugin.__class__.__name__
                            self.log.info(f"Calling {plugin_name}.{method_name}")
                            result = callback(event)
                            if result:
                                self.log.info(f"Reaction event {event_type} handled by {plugin_name}.{method_name}")
                                handled = True
                        except Exception as e:
                            self.log.error(f"Error in {plugin_name}.{method_name}: {e}")
            if not handled:
                self.log.info(f"No plugin handled the {event_type} event")
        except Exception as e:
            self.log.error(f"Error handling reaction event {event_type}: {e}")