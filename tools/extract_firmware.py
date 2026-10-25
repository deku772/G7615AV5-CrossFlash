#!/usr/bin/env python3
"""
中兴 G7615AV5 联通固件包拆解工具（纯 Python，无依赖）
从 HavingFun 重打包的联通 V3.0.5P1N4 完整升级 bin 中切出可直接
nand kwrite 的 kernel 镜像与 uboot 镜像。

用法:
    python extract_firmware.py <ZXHN_G7615AV5_UNI_V3.0.5P1N4.bin> [输出目录]

输出:
    kernel_p1n4.bin   0x2AA0000 字节  包内偏移 [0x0, 0x2AA0000)
    uboot_unicom.bin  0x1C0000 字节   包内偏移 [0x3100040, 0x32C0040)

参考 MD5 (V3.0.5P1N4, HavingFun 重打包版):
    kernel_p1n4.bin   b00edea2bac30985305df345d0b876cb
    uboot_unicom.bin  ec60ef2071a60b7d422e252ca7f52248

固件包结构速查 (实测逆向):
    0x0000000  FWD魔数 99999999 44444444 55555555 AAAAAAAA  联通 kernel 镜像起始
    0x0000192  版本串 "V3.0.5P1N4"（刷后验证点, hexdump -s 0x192 -n 6）
    0x0000180  产品串 "ZXHN G7615AV5 UNI V3.0.5P1N4"
    0x0000144  LE u32 = 整包大小 (0x32C0040)
    0x0000164  LE u32 = 0x3000000 (kernel 分区大小 48MB, 与 kernel1/2 分区一致)
    0x00540000 (相对分区)  rootfs 切片槽: kernel 分区内嵌 jffs2 rootfs 的偏移;
                           本包该区间为压缩数据(由升级程序展开), 直接 kwrite 不含可挂载 rootfs
    0x2AA0000  preplugin.img 段起始 = kernel 镜像实际长度边界
    0x2B80000  squashfs #2 (5.6MB, 压缩内容)
    0x3100000  REV魔数 AAAA5555 DDDD9999 + "V3.0.5P1N2" 段头
    0x3100040  联通 uboot 镜像起始, 长度 0x1C0000 (包头字段 @0x1a4)
    0x32C0030  尾部 "HavingFun" 签名
"""
import hashlib, os, sys

KERNEL_LEN = 0x2AA0000      # kernel 镜像长度 = 包内 [0x0, 0x2AA0000)
UBOOT_OFF = 0x3100040       # uboot 在包内的偏移
UBOOT_LEN = 0x1C0000        # uboot 长度

REF_MD5 = {
    'kernel_p1n4.bin': 'b00edea2bac30985305df345d0b876cb',
    'uboot_unicom.bin': 'ec60ef2071a60b7d422e252ca7f52248',
}


def md5_of(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    os.makedirs(out_dir, exist_ok=True)

    size = os.path.getsize(src)
    if size != 0x32C0040:
        print(f'[warn] 包大小 {size} (0x{size:x}) 与参考值 0x32C0040 不一致，'
              f'结构可能不同，输出仅供参考！')

    with open(src, 'rb') as f:
        # kernel
        f.seek(0)
        h = hashlib.md5()
        kpath = os.path.join(out_dir, 'kernel_p1n4.bin')
        with open(kpath, 'wb') as d:
            remaining = KERNEL_LEN
            while remaining > 0:
                chunk = f.read(min(1 << 20, remaining))
                if not chunk:
                    raise SystemExit('[error] 包读取意外截断')
                d.write(chunk)
                h.update(chunk)
                remaining -= len(chunk)
        kmd5 = h.hexdigest()

        # uboot
        f.seek(UBOOT_OFF)
        h2 = hashlib.md5()
        upath = os.path.join(out_dir, 'uboot_unicom.bin')
        with open(upath, 'wb') as d:
            remaining = UBOOT_LEN
            while remaining > 0:
                chunk = f.read(min(1 << 20, remaining))
                if not chunk:
                    raise SystemExit('[error] 包读取意外截断(uboot)')
                d.write(chunk)
                h2.update(chunk)
                remaining -= len(chunk)
        umd5 = h2.hexdigest()

        # 版本串验证
        f.seek(0x192)
        ver = f.read(10)

    print(f'kernel_p1n4.bin   {KERNEL_LEN:#x} 字节  md5={kmd5}  '
          f'{"OK" if kmd5 == REF_MD5["kernel_p1n4.bin"] else "与参考值不一致!"}')
    print(f'uboot_unicom.bin  {UBOOT_LEN:#x} 字节  md5={umd5}  '
          f'{"OK" if umd5 == REF_MD5["uboot_unicom.bin"] else "与参考值不一致!"}')
    print(f'kernel @0x192 版本串: {ver}')
    print(f'输出目录: {os.path.abspath(out_dir)}')


if __name__ == '__main__':
    main()
