#!/usr/bin/env python3
"""ZTE db_user_cfg.xml (ver 4) 解密/加密工具。

算法来源：zxcfg (github.com/yuleniwo/zxcfg) src/zxcfg.c
  - 文件头 60 字节: magic(0x01020304 BE) + ver + rsv[13]
  - 之后逐块: plain_len(4) cipher_len(4) have_next_blk(4) + 密文
  - ver==4 使用 paramtag 的 ID_INDIVKEY(1824) 或 USER_KEY/USER_IV
  - 密钥派生: MD5(key_str) -> hex -> SHA256(hex[:31]) -> AES-256-CBC
  - IV: SHA256(iv_str[:31])[:16]
"""
import hashlib
import re
import struct
import zlib

from Crypto.Cipher import AES

XML_HDR_MAGIC = 0x01020304
SPLIT_BLK_SIZE = 0x10000
ID_INDIVKEY = 1824
ID_GPONSN = 2177
ID_PONMAC = 32769
ID_MAC1 = 256
DEF_KEY = "PON_Dkey"
DEF_IV = "PON_DIV"
USER_KEY = "8cc72b05705d5c46f412af8cbed55aad"
USER_IV = "667b02a85c61c786def4521b060265e8"


def derive_key_iv(key_str, iv_str, key_method=1):
    """key_method=1: md5(key+'\0') -> hex -> sha256(hex[:31]); 0: sha256(str[:31])

    注意 zxcfg 源码里 tb_md5(zc->key, 33, m5) 传入的长度是 33，
    即把 C 字符串结尾的 NUL 也算进摘要，所以这里要补一个 b'\\x00'。
    """
    if key_method == 1:
        m5 = hashlib.md5(key_str.encode() + b'\x00').hexdigest()
        key = hashlib.sha256(m5[:31].encode()).digest()
    else:
        key = hashlib.sha256(key_str.encode()[:31]).digest()
    iv = hashlib.sha256(iv_str.encode()[:31]).digest()[:16]
    return key, iv


def parse_paramtag(path):
    """解析 paramtag，返回 (indivkey, gponsn, ponmac, mac1)。"""
    mem = open(path, 'rb').read()
    if mem[:4] != b'TAGH':
        raise ValueError('bad paramtag header')
    pos = 20
    endp = len(mem)
    if pos + 8 > endp or mem[pos + 4] == mem[pos + 5] or (mem[pos + 4] != 0 and mem[pos + 5] != 0):
        raise ValueError('invalid paramtag')
    le = mem[pos + 4] > 0
    found = {}
    while pos + 8 <= endp:
        if le:
            tid = (mem[pos + 1] << 8) | mem[pos]
            tlen = (mem[pos + 5] << 8) | mem[pos + 4]
        else:
            tid = (mem[pos] << 8) | mem[pos + 1]
            tlen = (mem[pos + 4] << 8) | mem[pos + 5]
        val = mem[pos + 6:pos + 6 + tlen]
        if tid in (ID_INDIVKEY, ID_GPONSN, ID_PONMAC, ID_MAC1) and tid not in found:
            found[tid] = val
        pos += (9 + tlen) & ~3
    return found


def key_from_paramtag(path):
    """返回 (key_str, iv_str, key_method)。"""
    found = parse_paramtag(path)
    indiv = found.get(ID_INDIVKEY)
    if indiv:
        # 个性化密钥: 32 字节 ASCII
        ks = indiv[:32].decode('latin1').rstrip('\x00')
        return ks, USER_IV, 1
    return USER_KEY, USER_IV, 1


def decrypt(data, key, iv):
    """解密 ver4 xml，返回 (明文xml bytes, 明文长度)。"""
    assert len(data) >= 60
    magic, ver = struct.unpack_from('>II', data, 0)
    if magic != XML_HDR_MAGIC:
        raise ValueError('bad magic %08x' % magic)
    out = bytearray()
    off = 60
    n = len(data)
    blk = 0
    while off < n:
        if off + 12 > n:
            break
        plain_len, cipher_len, have_next = struct.unpack_from('>III', data, off)
        off += 12
        if cipher_len == 0:
            break
        ct = data[off:off + cipher_len]
        off += cipher_len
        c = AES.new(key, AES.MODE_CBC, iv)
        pt = c.decrypt(ct)
        if blk == 0:
            # 第一块解密后应为 XML_HDR_MAGIC + 0
            if struct.unpack_from('>I', pt, 0)[0] != XML_HDR_MAGIC:
                raise ValueError('decrypt failed (magic mismatch) at block 0')
        out += pt[:plain_len]
        blk += 1
        if have_next == 0:
            break
    return bytes(out), blk


def decompress(dec):
    """ver0 压缩层: compr_file_hdr_t + 逐块 zlib inflate -> 完整 XML 文本。"""
    magic, ver = struct.unpack_from('>II', dec, 0)
    if magic != XML_HDR_MAGIC:
        raise ValueError('bad compr magic')
    # compr_file_hdr_t: magic,ver,content_len,last_compr_blk_off,split_blk_size,
    #                    content_crc,hdr_crc,rsv[8]  => 60 bytes
    content_len, last_off, split_size = struct.unpack_from('>III', dec, 8)
    off = 60
    out = bytearray()
    n = len(dec)
    while off < n:
        if off + 12 > n:
            break
        blk_size, compred_size, next_off = struct.unpack_from('>III', dec, off)
        off += 12
        if compred_size == 0:
            break
        cdata = dec[off:off + compred_size]
        off += compred_size
        d = zlib.decompressobj()
        out += d.decompress(cdata)
        if next_off == 0:
            break
    return bytes(out)


def _crc32(data, crc=0):
    return zlib.crc32(data, crc) & 0xFFFFFFFF


def compress(plain):
    """明文 XML -> ver0 压缩层。

    严格复刻 zxcfg compress_file()：
      compr_file_hdr_t (60B): magic,ver,content_len,last_compr_blk_off,
                              split_blk_size(0x10000),content_crc,hdr_crc,rsv[8]
      每块: compr_blk_hdr_t(12B) blk_size/compred_blk_size/next_compred_blk_off + deflate 数据
      每块按 0x10000 独立 deflate(Z_FINISH, MAX_MEM_LEVEL)
    """
    content_len = len(plain)
    # 组装各压缩块
    blocks = []
    pos = 0
    while pos < content_len:
        chunk = plain[pos:pos + SPLIT_BLK_SIZE]
        pos += len(chunk)
        co = zlib.compressobj(9, zlib.DEFLATED, 15, 9, zlib.Z_DEFAULT_STRATEGY)
        zdata = co.compress(chunk) + co.flush()
        blocks.append((len(chunk), zdata))

    # 计算 next_compred_blk_off 链与 content_crc
    next_off = 60
    body = bytearray()
    content_crc = 0
    last_off = 0
    for i, (blk_size, zdata) in enumerate(blocks):
        blk_len = 12 + len(zdata)
        content_crc = _crc32(zdata, content_crc)
        has_next = 1 if i < len(blocks) - 1 else 0
        if has_next:
            next_off += blk_len
            last_off = next_off
        else:
            next_off = 0
        body += struct.pack('>III', blk_size, len(zdata), next_off)
        body += zdata

    cfh = bytearray(struct.pack('>IIIIIII', XML_HDR_MAGIC, 0, content_len,
                                last_off, SPLIT_BLK_SIZE, content_crc, 0))
    cfh += b'\x00' * 32
    # hdr_crc = crc32(magic .. content_crc)，即前 24 字节
    hdr_crc = _crc32(bytes(cfh[:24]))
    struct.pack_into('>I', cfh, 24, hdr_crc)
    return bytes(cfh) + bytes(body)


def encrypt_raw(comp, key, iv):
    """压缩层字节 -> ver4 文件（AES-256-CBC 分块加密）。

    每块必须 16 字节对齐（AES-CBC 要求），末尾不足处补 0。
    """
    hdr = struct.pack('>II', XML_HDR_MAGIC, 4) + b'\x00' * 52
    out = bytearray(hdr)
    pos = 0
    while pos < len(comp):
        chunk = comp[pos:pos + SPLIT_BLK_SIZE]
        pos += len(chunk)
        have_next = 1 if pos < len(comp) else 0
        # AES-CBC 要求块长为 16 的倍数
        pad = (-len(chunk)) % 16
        if pad:
            chunk = chunk + b'\x00' * pad
        c = AES.new(key, AES.MODE_CBC, iv)
        ct = c.encrypt(chunk)
        out += struct.pack('>III', len(chunk), len(ct), have_next)
        out += ct
    return bytes(out)


def encrypt(plain, key, iv):
    """明文 xml -> ver4 文件（含 ver0 压缩层）。"""
    return encrypt_raw(compress(plain), key, iv)


if __name__ == '__main__':
    import sys
    src = sys.argv[1]
    ptg = sys.argv[2] if len(sys.argv) > 2 else None
    data = open(src, 'rb').read()
    ver = struct.unpack_from('>I', data, 4)[0]
    print('ver =', ver)
    if ver == 4 and ptg:
        ks, ivs, km = key_from_paramtag(ptg)
        print('key_str =', ks)
    else:
        ks, ivs, km = (USER_KEY, USER_IV, 1)
        print('key_str =', ks)
    k, iv = derive_key_iv(ks, ivs, km)
    plain, blk = decrypt(data, k, iv)
    print('aes blocks =', blk, 'dec len =', len(plain))
    ver2 = struct.unpack_from('>I', plain, 4)[0]
    if ver2 == 0:
        plain = decompress(plain)
        print('decompressed len =', len(plain))
    print(plain[:300])
    open(src + '.dec', 'wb').write(plain)
    print('->', src + '.dec')
