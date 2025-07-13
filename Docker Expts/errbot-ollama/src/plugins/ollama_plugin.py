from errbot import BotPlugin, botcmd
import requests

OLLAMA_URL = "http://ol:11434/api/generate"
OLLAMA_MODEL = "llama3"

class OllamaPlugin(BotPlugin):
    """
    Query a local Ollama LLM (llama3) and return answers in Slack.
    Usage: !ollama <your question>
    """
    @botcmd
    def aiq(self, msg, args):
        """Ask a question to the local Ollama LLM (llama3)"""
        prompt = args.strip()
        if not prompt:
            return "Please provide a prompt. Usage: !aiq <your question>"
        # Post a running emoticon message in the same thread/channel
        running_msg = self.send(msg.to, ":hourglass_flowing_sand: Fetching answer from Llama 3...", in_reply_to=msg)
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt
        }
        try:
            response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=60)
            answer = ""
            for line in response.iter_lines():
                if line:
                    try:
                        data = line.decode("utf-8")
                        if '"response":' in data:
                            import json
                            resp_json = json.loads(data)
                            answer += resp_json.get("response", "")
                    except Exception:
                        continue
            # Send answer and mark as done as replies in the same thread
            self.send(msg.to, answer.strip() or "(No response from Ollama)", in_reply_to=msg)
            self.send(msg.to, ":white_check_mark: Done!", in_reply_to=msg)
            return None
        except Exception as e:
            self.send(msg.to, ":x: Error fetching answer.", in_reply_to=msg)
            return None
