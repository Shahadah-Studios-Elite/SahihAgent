from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI

# Works with OpenAI, Groq, OpenRouter, or Gemini (via OpenAI-compatible endpoint)
client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"),
    base_url=os.environ.get("LLM_BASE_URL", "https://openai.com")
)

SYSTEM_PROMPT = """You are SahihAgent, a precise, helpful, and reliable AI assistant.
Verify facts carefully, give clear answers, and state clearly when something is uncertain."""

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length))
            messages = body.get("messages", [])

            full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

            response = client.chat.completions.create(
                model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                messages=full_messages,
                temperature=0.3
            )

            reply = response.choices[0].message.content
            self._send_json(200, {"reply": reply})

        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))
