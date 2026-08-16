#!/usr/bin/env python3
"""53016测试服务：flag在响应头 X-Flag（测Agent的header发现能力）。"""
from http.server import BaseHTTPRequestHandler, HTTPServer

FLAG_HEADER = "BLHX{header_flag_67890}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = b"<html><body>Mock service 002. Check headers.</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("X-Flag", FLAG_HEADER)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 53016), Handler).serve_forever()
