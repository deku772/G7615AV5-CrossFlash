#!/usr/bin/env python3
"""
HTTP 固件下发服务器（纯 Python，无依赖）
用途: 光猫 busybox wget 从电脑拉取固件文件（比 TFTP 快且无 32MB 限制）

用法:
    python http_file_server.py <固件所在目录> [端口]     # 默认 8001

光猫侧(telnet)拉取命令:
    wget -O /upgtempfile/kernel.bin http://192.168.1.100:8001/kernel_p1n4.bin
    md5sum /upgtempfile/kernel.bin    # 与电脑端 MD5 对比校验

注意:
    /upgtempfile 是 100MB tmpfs，重启后清空；kernel 镜像 44.7MB 放得下。
    Windows 防火墙: 网卡设为"专用"网络类别，否则入站会被拦。
"""
import os, sys
from http.server import SimpleHTTPRequestHandler, HTTPServer

root = sys.argv[1] if len(sys.argv) > 1 else '.'
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8001
os.chdir(root)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('[http] ' + (fmt % args), flush=True)


if __name__ == '__main__':
    print(f'HTTP 文件服务器: http://<本机IP>:{port} -> {os.getcwd()}', flush=True)
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()
