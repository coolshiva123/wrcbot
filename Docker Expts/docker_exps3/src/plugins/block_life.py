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
					"value": "submit_value",
					"action_id": "actionId-0"
				}
			]
		}
	]
