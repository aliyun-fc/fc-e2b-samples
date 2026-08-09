"""示例业务进程：占位代表「你自己的业务」，只监听 127.0.0.1。

绑 127.0.0.1 而不是 0.0.0.0 是有意的：网关只往容器的 5000 打流量，
业务进程一律由容器内的 openresty 反代过来，不需要自己对外暴露。
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 固定端口：nginx-app-routes.conf 的 proxy_pass 硬编码指向它，换端口要同时改那里。
APP_PORT = 8000


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        body = json.dumps(
            {"service": "my-app", "status": "ok", "path": self.path}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[my-app] {fmt % args}", flush=True)


if __name__ == "__main__":
    print(f"[my-app] listening on 127.0.0.1:{APP_PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", APP_PORT), Handler).serve_forever()
