#!/usr/bin/env python3
"""53019 SSRF 靶场 —— 带真实SSRF的URL预览功能。

flag 在 http://127.0.0.1:53020/internal 端点（只能通过SSRF访问的"内部服务"）：
BLHX{ssrf_flag_97531}
"""
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

INTERNAL_PORT = 53020
FLAG = "BLHX{ssrf_flag_97531}"


class InternalHandler(BaseHTTPRequestHandler):
    """内部服务：只监听127.0.0.1:53020，模拟内网端点。"""

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/internal":
            body = f"<html><body><h2>Internal Service</h2><p>flag: {FLAG}</p></body></html>".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = b"<html><body><h1>URL Preview</h1><form>URL: <input name='url'><button>Fetch</button></form></body></html>"
            self._respond(200, body, "text/html")
            return
        if parsed.path == "/fetch":
            qs = parse_qs(parsed.query)
            url = qs.get("url", [""])[0]
            # ⚠️ 故意SSRF：服务端请求任意URL
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    content = resp.read().decode(errors="replace")[:2000]
                body = f"<html><body><h2>Fetched</h2><pre>{content}</pre></body></html>".encode()
                self._respond(200, body, "text/html")
            except Exception as e:
                body = f"<html><body><h2>Error</h2><pre>{e}</pre></body></html>".encode()
                self._respond(500, body, "text/html")
            return
        self._respond(404, b"not found", "text/plain")

    def _respond(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    import threading

    threading.Thread(
        target=lambda: HTTPServer(("127.0.0.1", INTERNAL_PORT), InternalHandler).serve_forever(),
        daemon=True,
    ).start()
    print(f"SSRF靶场: http://127.0.0.1:53019/fetch?url=http://127.0.0.1:{INTERNAL_PORT}/internal")
    HTTPServer(("127.0.0.1", 53019), Handler).serve_forever()
