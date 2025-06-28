
from errbot import BotPlugin, botcmd

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
			"element": {
				"type": "plain_text_input",
				"action_id": "plain_text_input-action"
			},
			"label": {
				"type": "plain_text",
				"text": " ",
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
						"text": "Submit",
						"emoji": True
					},
					"value": "click_me_123",
					"action_id": "actionId-0"
				}
			]
		}
	]

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
            return_msg = "In My Prior Life I was a Cat ! Now I am a Bot!"
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

            #return "I replied in a thread (or created one) on the parent message."
            return None