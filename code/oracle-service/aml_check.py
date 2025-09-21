# aml_api_server.py
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 6000

class AMLRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/aml-check":
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            print(f"[AML API] Received request: {data}")

            # Static response
            response = {
                "approved": True,
                "flagged": False,
                "reason": "",
                "risk_score": 0
            }

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run():
    print(f"[AML API] Starting server on port {PORT}...")
    server = HTTPServer(("", PORT), AMLRequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    run()
