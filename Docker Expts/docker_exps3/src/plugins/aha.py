from errbot import BotPlugin, botcmd
from errbot.backends.slack import SlackReplyMixin
from errbot.core import ErrBot, Message # Import Message for type hinting if desired

class SlackBlockInput(BotPlugin, SlackReplyMixin):
    """
    An Errbot plugin to demonstrate capturing input from Slack Block Kit actions
    when running in Slack Socket Mode.
    """

    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        # Store a simple counter or state if needed
        self._button_click_count = 0

    @botcmd(threaded=True) # Run in a thread for responsiveness
    def aha(self, msg, args):
        """
        Sends a Slack message with an interactive button.
        Example: !aha
        """
        # Define the block for the message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Hello! Click the button below to send me some input."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Click Me!",
                            "emoji": True
                        },
                        "style": "primary", # Optional: 'primary' or 'danger'
                        "value": "my_custom_button_value", # Data sent with the action
                        "action_id": "unique_button_click_action" # Unique identifier for this action
                    }
                ]
            }
        ]

        # Send the message with blocks.
        # self.send_card is a SlackReplyMixin method convenient for blocks.
        self.send_card(
            to=msg.frm,
            title="Interactive Button Example",
            body="Interact with the button below:",
            blocks=blocks,
            in_reply_to=msg, # Optional: Send the initial message in a thread
            groupchat_status=msg.groupchat_status
        )
        return "Interactive button sent!"

    # This method is automatically called by Errbot's Slack backend
    # when an interactive component (like our button) is clicked.
    def callback_message(self, msg: Message):
        """
        Handles interactive component callbacks (e.g., button clicks).
        This method is specific to how Errbot's Slack backend processes
        interactive payloads from Socket Mode.
        """
        self.log.debug(f"Received callback_message: {msg.body}")

        # Slack interactive payloads have a specific structure.
        # msg.body will contain the JSON payload from Slack.
        payload = msg.body

        # Extract relevant information from the payload
        action_type = payload.get('type')
        user_id = payload.get('user', {}).get('id')
        user_name = payload.get('user', {}).get('name')
        channel_id = payload.get('container', {}).get('channel_id')
        thread_ts = payload.get('container', {}).get('thread_ts') # The thread timestamp if it's a threaded message

        # Check if it's a block_actions payload
        if action_type == 'block_actions' and payload.get('actions'):
            for action in payload['actions']:
                action_id = action.get('action_id')
                action_value = action.get('value')
                block_id = action.get('block_id')

                # Check if this is our specific button action
                if action_id == "unique_button_click_action":
                    self._button_click_count += 1 # Increment our simple counter

                    # Acknowledge the action immediately to Slack (important!)
                    # Errbot's backend typically handles the initial HTTP 200 OK
                    # for Socket Mode, but explicitly sending a blank response
                    # within the callback can sometimes be necessary for complex flows.
                    # For a simple text reply, self.send will be enough usually.

                    # Construct the reply message
                    reply_text = (
                        f"Hey <@{user_id}>, thanks for clicking the button!\n"
                        f"You clicked button with value: `{action_value}`\n"
                        f"This button has been clicked {self._button_click_count} time(s)."
                    )

                    # Determine where to send the reply.
                    # If it was in a thread, reply to that thread.
                    # Otherwise, reply in the original channel.
                    target_channel_id = msg.frm.channelid if msg.frm else channel_id
                    
                    # Construct a Message object that points to the correct thread if applicable
                    # The 'msg' object passed to callback_message will already have thread_ts if it was in a thread.
                    target_msg = Message(body=reply_text, frm=msg.frm, to=msg.to, channelid=target_channel_id)
                    if thread_ts:
                         target_msg.thread_ts = thread_ts # Set the thread_ts for the reply

                    self.send(
                        msg.frm, # Send to the channel where the action originated
                        reply_text,
                        in_reply_to=target_msg, # Crucial for threading if the original block message was in a thread
                        groupchat_status=msg.groupchat_status # Maintain context
                    )
                    # No explicit return value needed for callback_message
                    return # Exit after handling our action
        
        # If no specific action was handled, you might log it or ignore
        self.log.info(f"Unhandled Slack Block Action payload: {action_type}")