
from errbot import BotPlugin, botcmd, botmatch
from block_life import BLOCKS_PRIORLIFE
import json

class MyPriorLife(BotPlugin):
    @botcmd
    def mypriorlife(self, msg, args):
        """Responds with 'In My Prior Life I was a Cat ! Now I am a Bot!'"""
        slack_client = getattr(self._bot, 'slack_web', None)
        if not slack_client:
            return "Slack client not available. This message is only for slack."
        else:
            slack_event = msg.extras.get('slack_event', {})
            channel = slack_event.get('channel')
            ts = slack_event.get('ts')
            if not channel or not ts:
                if not channel or not ts:
                    return f"Cannot find channel or timestamp for threading. msg.extras: {msg.extras}"
            return_msg = "Hi ! I am WRCBot ! In My Prior Life I was a Cat ! Now I am a Bot!"
            slack_client.chat_postMessage(
            channel=channel,
            text=return_msg,
            thread_ts=ts,
            reply_broadcast=True
            )
            slack_client.chat_postMessage(
                channel=channel,
                blocks=BLOCKS_PRIORLIFE,
                text="What were you in your prior life?",
                thread_ts=ts,
                reply_broadcast=True
            )

            #return "I replied in a thread (or created one) on the parent message."
            return None
    @botmatch('.*')
    def handle_block_action(self, msg, action):
        """Handle block actions from the Prior Life input."""
        print("Entering handle_block_action")
        print(f"Received action: {action}")