#!/usr/bin/env python3
"""53018 命令注入靶场 —— 带真实命令注入的ping功能。

flag 在目标机器 /flag.txt（Linux）或环境变量 FLAG_RCE（Windows本地测试）：
BLHX{rce_flag_13579}
"""
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

FLAG = "BLHX{rce_flag_13579}"


def write_flag():
    # Linux容器：写 /flag.txt；Windows本地：设环境变量
    try:
        with open("/flag.txt", "w") as f:
            f.write(FLAG)
    except OSError:
        os.environ["FLAG_RCE"] = FLAG


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = b"<html><body><h1>Network Tool</h1><form>Ping: <input name='host'><button>Go</button></form></body></html>"
            self._respond(200, body, "text/html")
            return
        if parsed.path == "/ping":
            qs = parse_qs(parsed.query)
            host = qs.get("host", [""])[0]
            # ⚠️ 故意命令注入：直接拼接shell命令
            try:
                result = subprocess.run(
                    f"ping -c 1 {host} 2>&1 || ping -n 1 {host} 2>&1",
                    shell=True, capture_output=True, text=True, timeout=5,
                    errors="replace",
                )
                out = (result.stdout or "") + (result.stderr or "")
                body = f"<html><body><h2>Ping Result</h2><pre>{out}</pre></body></html>".encode()
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
    write_flag()
    print("RCE靶场: http://127.0.0.1:53018/ping?host=127.0.0.1")
    HTTPServer(("127.0.0.1", 53018), Handler).serve_forever()
