#!/usr/bin/env python3
"""
中兴光猫分区备份 TFTP 服务器（纯 Python，无依赖）
适用: busybox tftp 客户端 (中兴光猫自带)

用法:
    python tftp_server.py <保存目录>          # 默认监听 UDP 69

光猫侧(telnet)备份命令:
    tftp -p -l /dev/mtd1 192.168.1.100      # 备份 uboot 分区到电脑
    tftp -p -l /dev/mtd3 192.168.1.100      # 备份 paramtag（每机唯一！）
    ...

注意:
    1. busybox tftp 只支持 512 字节/块（OACK 大块协商会被拒绝），
       单文件受 16 位块号限制最大 32MB；kernel/osgi 等大分区需 dd 分段或走 HTTP。
    2. Windows 防火墙: 把网卡网络类别改为"专用"（专用 profile 默认放行），
       否则 UDP 69 入站会被拦（现象: 光猫侧报 tftp: timeout，服务器无任何日志）。
"""
import socket, struct, sys, os, threading, time

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else 'backup'
os.makedirs(OUT_DIR, exist_ok=True)


def recv_file(addr, filename, blksize, opts):
    ds = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ds.settimeout(15)
    safe = os.path.basename(filename.replace('\\', '_').replace('/', '_'))
    path = os.path.join(OUT_DIR, safe)
    try:
        # 尝试 OACK 协商大块（busybox 客户端会拒绝并回落 512）
        want_blksize = 8192
        oack = struct.pack('!H', 6) + b'blksize\x00' + str(want_blksize).encode() + b'\x00'
        if b'tsize' in opts:
            oack += b'tsize\x00' + b'0\x00'
        ds.sendto(oack, addr)
        negotiated = want_blksize
        data = None
        op = None
        try:
            data, _ = ds.recvfrom(65536 + 64)
            op = struct.unpack('!H', data[:2])[0]
            if op == 5:  # 客户端拒绝 OACK -> 回落 ACK0/512
                negotiated = blksize
                ds.sendto(struct.pack('!HH', 4, 0), addr)
            elif op == 4 or op == 3:
                pass
            else:
                negotiated = blksize
                ds.sendto(struct.pack('!HH', 4, 0), addr)
        except socket.timeout:
            negotiated = blksize
            ds.sendto(struct.pack('!HH', 4, 0), addr)
        print(f'[neg] {safe}: blksize={negotiated}', flush=True)

        expected = 1
        total = 0
        last_report = time.time()
        first_data = data if (op == 3) else None
        with open(path, 'wb') as f:
            while True:
                if first_data is not None:
                    data = first_data
                    first_data = None
                else:
                    try:
                        data, _ = ds.recvfrom(65536 + 64)
                    except socket.timeout:
                        print(f'[timeout] {safe}: 等待块 {expected}，已收 {total} 字节', flush=True)
                        break
                op = struct.unpack('!H', data[:2])[0]
                if op == 3:  # DATA
                    block = struct.unpack('!H', data[2:4])[0]
                    if block == expected:
                        f.write(data[4:])
                        expected += 1
                        total += len(data) - 4
                    ds.sendto(struct.pack('!HH', 4, block), addr)
                    if time.time() - last_report > 5:
                        print(f'[...] {safe}: {total} bytes', flush=True)
                        last_report = time.time()
                    if len(data) - 4 < negotiated:
                        break
                elif op == 5:
                    print(f'[client-error] {safe}: {data[4:]}', flush=True)
                    break
    finally:
        ds.close()
    print(f'[done] {safe}: {total} bytes', flush=True)


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', 69))
    print(f'TFTP 服务器已启动 UDP :69，备份保存到 {os.path.abspath(OUT_DIR)}', flush=True)
    while True:
        data, addr = s.recvfrom(2048)
        try:
            op = struct.unpack('!H', data[:2])[0]
        except Exception:
            continue
        if op == 2:  # WRQ (光猫上传文件到本机)
            parts = data[2:].split(b'\x00')
            filename = parts[0].decode(errors='replace')
            blksize = 512
            opts = {}
            i = 2
            while i + 1 < len(parts):
                if parts[i]:
                    k = parts[i].lower()
                    v = parts[i + 1]
                    if k == b'blksize':
                        try:
                            blksize = max(8, min(65464, int(v)))
                        except Exception:
                            pass
                    if k:
                        opts[k] = v
                i += 2
            print(f'[wrq] {filename} from {addr} blksize={blksize}', flush=True)
            t = threading.Thread(target=recv_file, args=(addr, filename, blksize, opts), daemon=True)
            t.start()


if __name__ == '__main__':
    main()
