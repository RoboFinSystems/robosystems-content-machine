"""Serve the demo account's sign-in once, on localhost, so a Playwright take can sign in
without the password appearing in the automation's code or transcript.

The recording browser fetches it with `page.request.get('http://127.0.0.1:18765/')` and
fills the robosystems.ai sign-in form. The server answers one request, then exits (or
gives up after two minutes). Reads DEMO_ACCOUNT_EMAIL / DEMO_ACCOUNT_PASSWORD from .env.

Usage: uv run --no-project python tools/demo_signin_server.py   (run in the background)
"""

import http.server
import json
import re
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"
PORT = 18765

values = dict(re.findall(r"(?m)^(DEMO_ACCOUNT_\w+)=(.*)$", ENV.read_text()))
BODY = json.dumps(
  {"e": values["DEMO_ACCOUNT_EMAIL"], "p": values["DEMO_ACCOUNT_PASSWORD"]}
).encode()


class Handler(http.server.BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(BODY)

  def log_message(self, *args):
    pass


server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
server.timeout = 120
server.handle_request()
