#!/usr/bin/env python3
"""极简 CDP 客户端（纯标准库，无第三方依赖）。

用途：驱动本机已安装的 Edge/Chrome（以 --remote-debugging-port 启动），
通过 Runtime.evaluate 在真实页面上执行操作，等同人工点击。
"""
import base64
import json
import os
import socket
import struct
import time
import urllib.request


class WS:
    def __init__(self, url, timeout=30):
        # ws://127.0.0.1:9222/devtools/page/XXXX
        assert url.startswith("ws://")
        rest = url[5:]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            "GET /%s HTTP/1.1\r\n"
            "Host: %s:%s\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ) % (path, host, port, key)
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("websocket handshake closed")
            buf += chunk
        head, rest = buf.split(b"\r\n\r\n", 1)
        status = head.split(b"\r\n")[0]
        if b"101" not in status:
            raise RuntimeError("handshake failed: %s" % status.decode("latin1"))
        self.buf = rest

    def _recv_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        payload = text.encode()
        header = bytearray()
        header.append(0x81)  # FIN + text
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def recv(self):
        # 返回完整文本消息（处理分片与 ping）
        chunks = []
        while True:
            b0, b1 = self._recv_exact(2)
            fin = b0 & 0x80
            opcode = b0 & 0x0F
            masked = b1 & 0x80
            ln = b1 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._recv_exact(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else None
            data = self._recv_exact(ln)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x9:  # ping -> pong
                self._send_control(0xA, data)
                continue
            if opcode == 0x8:
                raise RuntimeError("websocket closed by peer")
            chunks.append(data)
            if fin:
                return b"".join(chunks).decode("utf-8", "replace")

    def _send_control(self, opcode, payload):
        header = bytearray([0x80 | opcode])
        n = len(payload)
        header.append(0x80 | n)
        mask = os.urandom(4)
        header += mask
        self.sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class CDP:
    def __init__(self, port=9222):
        self.port = port
        self._id = 0
        self.ws = None

    # ---- 目标管理 ----
    def targets(self):
        with urllib.request.urlopen("http://127.0.0.1:%d/json" % self.port, timeout=10) as r:
            return json.loads(r.read().decode())

    def open_tab(self, url):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/json/new?%s" % (self.port, url), method="PUT"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    def attach(self, url=None, ws_url=None):
        if ws_url is None:
            ts = [t for t in self.targets() if t.get("type") == "page"]
            if url:
                ts = [t for t in ts if url in t.get("url", "")]
            if not ts:
                raise RuntimeError("no matching page target")
            ws_url = ts[0]["webSocketDebuggerUrl"]
        self.ws = WS(ws_url)
        self.call("Runtime.enable")
        return ws_url

    def call(self, method, params=None, timeout=30):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s -> %s" % (method, msg["error"]))
                return msg.get("result", {})
        raise TimeoutError(method)

    # ---- 常用封装 ----
    def js(self, expr, timeout=30):
        r = self.call(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": True},
            timeout=timeout,
        )
        res = r.get("result", {})
        if r.get("exceptionDetails"):
            raise RuntimeError("JS error: %s" % json.dumps(r["exceptionDetails"])[:400])
        return res.get("value")

    def goto(self, url, wait=1.5):
        self.call("Page.navigate", {"url": url})
        time.sleep(wait)

    def close(self):
        if self.ws:
            self.ws.close()
