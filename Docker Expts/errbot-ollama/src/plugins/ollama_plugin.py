from errbot import BotPlugin, botcmd
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

class OllamaPlugin(BotPlugin):
    """
    Query a local Ollama LLM (llama3) and return answers in Slack.
    Usage: !ollama <your question>
    """
    @botcmd
    def ollama(self, msg, args):
        """Ask a question to the local Ollama LLM (llama3)"""
        prompt = args.strip()
        if not prompt:
            return "Please provide a prompt. Usage: !ollama <your question>"
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
                            # Extract the response text
                            import json
                            resp_json = json.loads(data)
                            answer += resp_json.get("response", "")
                    except Exception:
                        continue
            return answer.strip() or "(No response from Ollama)"
        except Exception as e:
            return f"Error querying Ollama: {e}"
