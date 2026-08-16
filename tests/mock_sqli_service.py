#!/usr/bin/env python3
"""53017 SQLi 测试靶场 —— 带真实SQL注入漏洞的商品查询接口。

flag 藏在数据库 users 表 admin 用户的 password 字段：
flag = BLHX{sqli_flag_24680}
"""
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

DB = "/tmp/sqli_test.db"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    c.execute("INSERT OR REPLACE INTO products VALUES (1, 'apple', 3.5)")
    c.execute("INSERT OR REPLACE INTO products VALUES (2, 'banana', 2.0)")
    c.execute("INSERT OR REPLACE INTO products VALUES (3, 'orange', 4.0)")
    c.execute("INSERT OR REPLACE INTO users VALUES (1, 'admin', 'BLHX{sqli_flag_24680}')")
    c.execute("INSERT OR REPLACE INTO users VALUES (2, 'user', 'pass123')")
    conn.commit()
    conn.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = b"<html><body><h1>Shop</h1><p>Search products: /product?id=1</p></body></html>"
            self._respond(200, body, "text/html")
            return
        if parsed.path == "/product":
            qs = parse_qs(parsed.query)
            pid = qs.get("id", ["1"])[0]
            try:
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                # ⚠️ 故意SQL注入：字符串拼接
                c.execute(f"SELECT id, name, price FROM products WHERE id = {pid}")
                rows = c.fetchall()
                conn.close()
                if rows:
                    body = f"<html><body><h2>Product</h2><p>ID: {rows[0][0]}</p><p>Name: {rows[0][1]}</p><p>Price: {rows[0][2]}</p></body></html>".encode()
                    self._respond(200, body, "text/html")
                else:
                    self._respond(404, b"<html><body>Not found</body></html>", "text/html")
            except Exception as e:
                # 报错信息泄露（报错注入利用点）
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
    init_db()
    print("SQLi靶场: http://127.0.0.1:53017/product?id=1")
    HTTPServer(("127.0.0.1", 53017), Handler).serve_forever()
