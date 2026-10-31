# Telnet 固化完整方案（2026-10-31 实机验证通过）

> 本文档记录 G7615AV5 上**从零破解**并**实机验证成功**的 telnet 固化流程。
> 全部步骤已在这台设备上跑通两次重启复验。

---

## 一、先回答"手动固化要改什么"

固化的本质是修改设备上的 `/userconfig/cfg/db_user_cfg.xml`（AES 加密的 XML 库），
具体是 `TelnetCfg` 表的 `Row 0`：

| 字段 | 原值 | 固化后 | 作用 |
|---|---|---|---|
| `Lan_Enable` | `0` | **`1`** | ★ 关键：telnetd 是否监听 LAN 侧 23 端口 |
| `TSLan_UName` | `root` | `root` | LAN 侧 telnet 账号 |
| `TSLan_UPwd` | `<设备 SN>`（出厂用序列号当密码） | **`12345`** | LAN 侧 telnet 密码 |
| `Max_Con_Num` | `2` | **`999`** | 最大并发连接数（默认 2 会占满） |
| `ExitTime` | `5` | **`999`** | 空闲超时（分钟），默认 5 分钟就断 |
| `InitSecLvl` | `0` | **`3`** | 初始化安全级别 |

同时建议一并固化 `DevAuthInfo` 的 web 账号、`MgtServer.Tr069Enable` 等（见下文）。

---

## 二、★ 为什么 `sendcmd 1 DB set` 无效（README 坑 3 的真正原因）

**实测结论：`TelnetCfg` 表在运行时是只读的。**

对照实验：

```
sendcmd 1 DB set MgtServer 0 URL TESTPROBE   → 成功，读回 val="TESTPROBE"
sendcmd 1 DB set TelnetCfg 0 Lan_Enable 1     → 无任何回显，读回仍是 val="0"
sendcmd 1 DB set TelnetCfg 0 ExitTime 999     → 无效
sendcmd 1 DB set TelnetCfg 0 QueueNum 7       → 无效
sendcmd 1 DB set TelnetCfg 0 Forbidden 1      → 无效
sendcmd 1 DB set MgtServer 5 URL BADROW       → 无效（行号越界也静默）
```

`sendcmd 1 DB set` 对 `TelnetCfg` **被静默丢弃**，但对 `MgtServer` 正常。
所以 README 里"手动写字段 + DB save"的建议在这台机器上确实无效——**必须走配置文件路径**。

> `ZTE Telnet 小助手` 内部其实有两条固化路径（从二进制里挖到的字符串）：
> `Telnet 固化成功(sendcmd命令配置)` 和 `Telnet 固化成功(配置文件修改)`。
> 后者才是这台机器上真正有效的。

---

## 三、配置文件加密算法（已完整逆向）

来源：ZXCFG 项目（`github.com/yuleniwo/zxcfg`，exe 内也引用了它）。
本仓库已用 Python 完整复刻：`tools/zte_cfg.py`。

### 3.1 文件结构（ver 4）

```
偏移 0x00  encrypt_hdr_t (60 字节)
           u32 magic  = 0x01020304 (大端)
           u32 ver    = 4
           u32 rsv[13] = 0
偏移 0x3C  逐块（encrypt_blk_hdr_t, 每块 12 字节头）
           u32 plain_len      该块明文长度
           u32 cipher_len     密文长度（已按 16 字节对齐）
           u32 have_next_blk  0=最后一块
           + cipher_len 字节 AES-CBC 密文
```

解密后得到 **ver 0 压缩层**（`compr_file_hdr_t` 60 字节 + 逐块 zlib），
解压后是 503 KB 的明文 XML：

```xml
<DB>
<Tbl name="TelnetCfg" RowCount="1">
<Row No="0">
<DM name="Lan_Enable" val="0"/>
...
</Row>
</Tbl>
...
</DB>
```

### 3.2 密钥派生（★ 最容易踩坑的地方）

```python
# 1) 从 /tagparam/paramtag 取 ID_INDIVKEY = 1824 的 tag 值（32 字节 ASCII）
key_str = paramtag[ID_INDIVKEY]        # 本机: eeU7FYDdYbyh3SkHztuY69t22cHbhYs3

# 2) MD5 时长度传 33 —— 把 C 字符串结尾的 NUL 也算进摘要（这是原版的坑）
m5      = md5(key_str + b'\x00').hexdigest()

# 3) 取前 31 个字符再做 SHA256
key     = sha256(m5[:31].encode()).digest()      # 32 字节

# 4) IV：sha256(iv_str[:31])[:16]
iv_str  = "667b02a85c61c786def4521b060265e8"      # USER_IV (ver4)
iv      = sha256(iv_str[:31].encode()).digest()[:16]

# 5) AES-256-CBC
```

> **不漏掉那个 NUL 字节，MD5 就对不上，解密会直接失败。**
> 验证方法：`tools/zte_cfg.py` 重新压缩后的字节应与原文件**逐字节相同**
> （长度、`content_crc`、`hdr_crc` 全部吻合）——这是算法复刻正确的铁证。

### 3.3 paramtag 解析

`/tagparam/paramtag` 结构：头部 `TAGH` + 版本，偏移 20 起是 tag 列表。
每个 tag：`u16 id` + `u16 len` + `len` 字节数据，下一条按 `(9+len) & ~3` 对齐。

需要用到的 ID：

| ID | 名称 | 用途 |
|---|---|---|
| 1824 | `ID_INDIVKEY` | ★ 个性化密钥（本机有，用它） |
| 2177 | `ID_GPONSN` | 备用（拼接 MAC 派生） |
| 32769 | `ID_PONMAC` | 备用 |
| 256 | `ID_MAC1` | 备用 |

若 `ID_INDIVKEY` 不存在，才退回 `USER_KEY = "8cc72b05705d5c46f412af8cbed55aad"`。

---

## 四、★★ 三个致命陷阱（照做就会白忙）

### 陷阱 1：`sendcmd 1 DB save` 会覆盖你的文件

`DB save` 会用**内存 DB 重新序列化**并写回 `db_user_cfg.xml`。
内存 DB 里的 `TelnetCfg` 是旧值（只读表改不了），所以**你刚写好的文件会被抹掉**。

实测：
```
cp 新配置 -> md5 = 87741764...   ✓ 写入成功
sendcmd 1 DB save
             -> md5 = 3540622e...   ✗ 被内存 DB 覆盖，回滚
```

**对策：改完文件后绝对不要执行 `DB save`。**

### 陷阱 2：`sendcmd 1 DB rreset` 之后别再动文件

`rreset` 会让内存 DB 按**磁盘上的文件**重新加载。如果磁盘已经是新文件，这一步是无害的
（`solidify.py` 末尾就靠它让内存立刻生效）；但如果你还没覆盖好文件就 rreset，
内存会带着旧值继续跑，随后任何一次 `DB save` 都会把旧值写回磁盘。

**稳妥顺序：写文件 → 校验 MD5 → `reboot`。** 想让内存立刻生效才用 `rreset`，且顺序必须在覆盖之后。

### 陷阱 3：必须同时覆盖 `db_backup_cfg.xml`

设备上有 `db_backup_cfg.xml`，启动/恢复流程会拿它覆盖 `db_user_cfg.xml`。
`/userconfig/RestoreFlag` 内容为 `1` 时会触发恢复。

**对策：两个文件都要写成新版本。**

```bash
cp /tmp/db_user_cfg.xml.new /userconfig/cfg/db_user_cfg.xml
cp /tmp/db_user_cfg.xml.new /userconfig/cfg/db_backup_cfg.xml
sync
```

### 正确顺序（实测通过）

```
1. pull  /userconfig/cfg/db_user_cfg.xml   （备份）
2. pull  /tagparam/paramtag
3. 解密 → 改 XML 字段 → 重新压缩 → 重新加密
4. printf 转义串写入 /tmp/db_user_cfg.xml.new
5. cp 到 db_user_cfg.xml  和  db_backup_cfg.xml   （两个都要！）
6. sync
7. reboot                                     （不要 DB save；rreset 可选且必须在 cp 之后）
8. 等待 ~50 秒，telnet 端口自动打开
9. root/12345 登录成功 = 固化完成
```

> 想确认磁盘写对了、又不想马上重启，可以在 `cp` + `sync` 之后执行一次 `sendcmd 1 DB rreset`：
> 内存会按新文件重载，随后用 `sendcmd 1 DB p TelnetCfg` 就能看到 `Lan_Enable=1`。但**必须确认 cp 已完成**。

---

## 五、怎么把文件推上去（设备没有 base64）

设备 busybox 只有 `hexdump`，**没有 `base64`**，但 **`printf` 支持 `\xNN`**：

```bash
# 本地：把二进制转成 \xNN 转义串，分块推送
printf '\x01\x02\x03\x04...' > /tmp/db_user_cfg.xml.new
printf '\x...' >> /tmp/db_user_cfg.xml.new
```

单条命令的转义串别太长（6000 字符为宜，约 600 字节/次），一次 36 KB 的文件
分 25 块约 25 秒完成。

校验：`md5sum` 本地与设备一致即可。

---

## 六、本仓库新增工具

| 工具 | 作用 |
|---|---|
| `tools/zte_cfg.py` | ★ db_user_cfg.xml ver4 加解密（Python 复刻 zxcfg） |
| `tools/pull_file.py` | telnet 拉取设备文件（hexdump 传输，设备无 base64） |
| `tools/push_cfg2.py` | 分步推送配置（push / cp / rreset / check 四个阶段） |
| `tools/solidify.py` | 一键固化：改 XML → push → cp 两文件 → MD5 校验；可选改 web 账号、关 TR069、直接重启 |

### 一键固化

```bash
# 只固化 telnet
python tools/solidify.py 192.168.1.1 <telnet用户> <telnet密码>

# 固化 + 改 web 超密/普通账号 + 关 TR069 + 重启
python tools/solidify.py 192.168.1.1 <telnet用户> <telnet密码> \
  --admin <超管名>:<超密> --user <普通名>:<普通密码> --tr069-off --reboot

# 只演算不写设备（结果写到 .temp/dryrun.xml，可人工 diff）
python tools/solidify.py 192.168.1.1 <telnet用户> <telnet密码> --admin a:b --dry-run
```

> `--admin-level` 用于指定"哪一级是超管"（默认 `1`）。本机实测 `Level=1` 才是管理维护账号，
> 与部分教程的 `Level=2` 说法相反——**这个数值别背，改完用「管理员账户」入口验证一次**。

---

## 七、固化结果（本机实机验证）

固化后：

```
sendcmd 1 DB p TelnetCfg
  <DM name="Lan_Enable"  val="1"/>
  <DM name="Max_Con_Num" val="999"/>
  <DM name="ExitTime"    val="999"/>
  <DM name="InitSecLvl"  val="3"/>
```

- 重启后 23 端口**自动开启**（无需任何工具）
- `root / 12345` 可直接登录
- **连续两次重启复验均通过**
- 磁盘 `db_user_cfg.xml` 与 `db_backup_cfg.xml` 内容一致且保有修改
- web 界面正常（HTTP 200），`DevAuthInfo` 等其他配置未受影响

> ⚠️ 安全提示：`root/12345` 是弱口令，请勿在公网/桥接侧暴露 telnet。
> 需要更强密码时，把 `tools/solidify.py` 里 `CHANGES['TelnetCfg']['TSLan_UPwd']`
> 改成你自己的值再跑一遍。

---

## 八、附：临时 telnet 账号怎么拿

`ZTElnet26` / `ZTE Telnet 小助手` 每次「使能」会生成**随机**临时账号（10 位随机大小写串）。
小助手把它显示在「基本配置」页的 `Telnet 用户名` / `Telnet 密码` 两个输入框里，
可以用 UI 自动化直接读出来（见 `tools/fill_ztetelnet.py` 的定位方式）：

```python
from pywinauto import Desktop
win = Desktop(backend="uia").windows(title_re=".*ZTE Telnet.*")[0]
for c in win.descendants(control_type="Edit"):
    r = c.rectangle()
    if 360 <= r.top <= 400:      # Telnet 用户名 / 密码 两行
        print(c.get_value())
```

拿到后 `python tools/telnet_session.py 192.168.1.1 <user> <pass> "<cmd>"`
即可执行任意命令。固化完成后就不需要这个临时账号了——直接用 `root/12345`。
