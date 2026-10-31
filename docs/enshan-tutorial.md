# 【实战】ZXHN G7615AV5 移动版刷联通版：从刷机到 telnet 固化、改超密、配业务，一条线走完

> 适用：中兴 ZXHN G7615AV5（10G GPON，硬件 V2.0，256MB NAND）
> 出发点：运营商给的**正常移动版固件**（本例 V3.0.6P2T3）
> 终点：**联通 V3.0.5P1N4 + 本地地区码 + telnet 常开 + 自定超密 + 上网/IPv6/IPTV 全通**
> 全部命令实机跑通，2026-10 刷机、2026-11 复验。文中数值都来自真机，不是抄的。

---

## 写在前面

- **这台机器是双分区**（kernel1 / kernel2 各 48MB），刷的是**非运行分区**，新固件起不来会自动回落旧固件。
  所以「刷坏了开不了机」在只刷 kernel 的情况下基本不会发生——**真正的风险只有两步：刷 uboot、以及 nand 写入时断电**。
- **整个过程光纤必须拔掉**，直到第 10 步注册前都不要插。插着光纤刷机，运营商侧可能在你配置到一半时下发模板，
  把你刚改的东西覆盖掉，还会让「复位后进不去」的概率大增。
- 需要一点命令行基础（telnet 敲命令），但不需要拆机、不需要 TTL。

> ⚠️ 刷机有风险，后果自负。仅供个人设备学习折腾，遵守当地法律法规。
> 关键步骤（尤其 `nand kerase/kwrite`）**中途断电 = 真砖**，请确保电脑和光猫都接在稳定的电源上。

---

## 0. 准备清单

**硬件**

- 一根网线，电脑直连光猫 **LAN1**（后文所有 `192.168.1.1` 都指这个口）
- 电脑有线网卡**千兆**（协商成 100M 说明网线只有 4 芯通，换 Cat5e 以上）

**软件**（都在本仓库 `tools/` 与 `third_party/`）

| 用途 | 工具 |
|---|---|
| 开 telnet | `third_party/ZTElnet26-windows-amd64.exe`（首选）、`third_party/go_build_zte_go.exe`（备选） |
| 敲命令 | `tools/telnet_session.py`、`tools/tel_exec.py`（Windows 自带 telnet.exe 没法自动化） |
| 备份分区 | `tools/tftp_server.py` |
| 拆固件 | `tools/extract_firmware.py` |
| 下发固件 | `tools/http_file_server.py` |
| 固化 / 改密 / 关 TR069 | `tools/solidify.py` |
| 备份 / 回滚配置 | `tools/backup_restore.py` |

**三个容易翻车的前置设置**

1. **把这块网卡的网络类别改成「专用」**（设置 → 网络和 Internet → 属性）。
   公用 profile 下 Windows 防火墙会拦 TFTP(69) 和 HTTP(8001)，现象是光猫侧 `tftp: timeout` 而服务器毫无日志。
2. **记下电脑有线网卡的 MAC，去掉冒号**（`ipconfig /all` 里的物理地址）。
   开 telnet 的 `-m` 参数填的是**你电脑的 MAC**，不是光猫的，更不是论坛帖里那个人的。
3. 关掉电脑上的 VPN / 代理 / 虚拟机网卡，避免路由抢到 192.168.1.0/24。

---

## 1. 流程总览

| 步 | 做什么 | 大概耗时 | 风险 |
|---|---|---|---|
| 1 | 确认分区、当前运行槽 | 2 min | — |
| 2 | 开 telnet（工厂模式） | 3 min | — |
| 3 | **备份全部分区**（救砖保险） | 15 min | — |
| 4 | 拆联通固件包，取出 kernel + uboot | 2 min | — |
| 5 | 上传到光猫并校验 MD5 | 5 min | — |
| 6 | **刷 kernel 到备用分区 + 刷 uboot** | 10 min | ★★ 断电必砖 |
| 7 | 切启动槽重启 → 变成联通界面 | 5 min | 失败会自动回落 |
| 8 | 切地区码 + **拔光纤物理复位（灯全亮）** | 6 min | — |
| 9 | telnet 使能 → **固化 + 改超密 + 关 TR069** | 10 min | 顺序错会白做 |
| 10 | 网页配业务（WAN / IPv6 / DNS / WiFi） | 20 min | — |
| 11 | 插光纤、LOID 注册（跳注册页见 14.1） | 5 min | — |
| 12 | 备份一份干净配置 | 2 min | — |

**时间线提醒**：第 8 步复位之后到第 10 步之前，是所谓的**"黄金 10 分钟"**——此时设备是干净默认库、
telnet 能开、没有任何运营商配置干扰。**固化必须在这个窗口里做完**，插了光纤再固化就是跟 ITMS 抢时间。

---

## 2. 确认分区与当前运行槽

先开 telnet（见下一步）再执行；这里先说明要看什么：

```
cat /proc/mtd                    # 分区表，必须核对，别照抄别人的编号
cat /proc/csp/versionstates      # 当前运行槽 current=0/1
fw_flashing                      # curpdev=/dev/mtd7 或 mtd8
upgradetest getver               # Main/Spare 各自版本
```

本机实测分区表（G7615AV5 硬件 V2.0）：

```
mtd0: 10000000 "whole flash"     mtd7:  03000000 "kernel1"    ← 槽 0
mtd1: 00300000 "u-boot"          mtd8:  03000000 "kernel2"    ← 槽 1（出厂运行）
mtd2: 00200000 "others"          mtd9:  02c00000 "osgi1"
mtd3: 00200000 "parameter tags"  mtd10: 02c00000 "osgi2"
mtd4: 00200000 "wlan"            mtd11: 03100000 "plugin_data"
mtd5: 00800000 "usercfg"         mtd12: 03000000 "rootfs1"
mtd6: 00600000 "middle"          mtd13: 02ac0000 "rootfs2"
```

**刷写目标 = 非运行分区**：跑在 mtd8 就刷 mtd7，反之亦然。
**当前运行的那一分区从头到尾不许碰**——它就是你按不亮时的后路。

---

## 3. 开 telnet（刷机阶段）

刷机阶段只要求"能进 shell"，用工厂模式工具最省事（新旧固件通吃，且复位/重启后依然有效）：

```bat
third_party\ZTElnet26-windows-amd64.exe -i 192.168.1.1 -m <你电脑的MAC，无冒号> -p 80 -u factorymode -pw "nE%jA@5b"
```

成功时窗口里会打印一组**随机临时账号**（每次都不一样），拿它去登录：

```bat
python tools\telnet_session.py 192.168.1.1 <临时用户> <临时密码> "upgradetest getver"
```

> 备选：`go_build_zte_go.exe -addr http://192.168.1.1:80 -mac <MAC> -username CMCCAdmin -password aDm8H%MdA`
> —— 它走 web 账户库校验，需要当前超密有效；移动版默认 `CMCCAdmin / aDm8H%MdA`。
> 一旦超密被改或失效，这个工具会稳定 401，此时回头用 ZTElnet26。

---

## 4. 备份分区（★ 必做，救砖全靠它）

```bat
python tools\tftp_server.py backup
```

然后 telnet 侧逐个推给电脑（假设电脑 IP 是 192.168.1.100）：

```bash
tftp -p -l /dev/mtd1 192.168.1.100    # uboot        3MB  ★砖了靠它
tftp -p -l /dev/mtd2 192.168.1.100    # others       2MB
tftp -p -l /dev/mtd3 192.168.1.100    # paramtag     2MB  ★每机唯一（含光校准）
tftp -p -l /dev/mtd4 192.168.1.100    # wlan         2MB  ★每机唯一（Wi-Fi 校准）
tftp -p -l /dev/mtd5 192.168.1.100    # usercfg      8MB  ★含账户库/SN
tftp -p -l /dev/mtd6 192.168.1.100    # middle       6MB
```

**mtd1（uboot）、mtd3（paramtag）、mtd4（wlan）、mtd5（usercfg）这四份是你的命**，
别人机器上的同分区文件不能替代——paramtag/wlan 里是这台机器独有的光功率与射频校准，usercfg 绑定 SN。

> busybox 的 tftp 受 16 位块号限制，单文件最大 32MB；大分区要备份就用 `dd` 分段再传。

---

## 5. 拆固件包

```bat
python tools\extract_firmware.py D:\ZXHN_G7615AV5_UNI_V3.0.5P1N4.bin firmware
```

得到两个文件，MD5 对得上就能用：

| 文件 | 大小 | MD5 |
|---|---|---|
| `kernel_p1n4.bin` | 44,695,552 | `b00edea2bac30985305df345d0b876cb` |
| `uboot_unicom.bin` | 1,835,008 | `ec60ef2071a60b7d422e252ca7f52248` |

---

## 6. 上传到光猫并校验

```bat
python tools\http_file_server.py firmware 8001
```

telnet 侧（`/upgtempfile` 是 100MB 的 tmpfs，放得下）：

```bash
wget -O /upgtempfile/kernel.bin http://192.168.1.100:8001/kernel_p1n4.bin
wget -O /upgtempfile/uboot.bin  http://192.168.1.100:8001/uboot_unicom.bin
md5sum /upgtempfile/kernel.bin      # 必须和电脑上的 MD5 一致
md5sum /upgtempfile/uboot.bin
```

MD5 不一致就重下——**带着坏文件去 kwrite 是这个流程里最没必要的自杀方式**。

---

## 7. 刷写（★ 期间绝对不能断电）

假设当前运行 mtd8，目标 mtd7：

```bash
echo 2 > /proc/zteinfo/factory/factorymode      # 进工厂模式
touch /userconfig/nanddebug                     # 解除 nand 写保护

# ① kernel 写到备用分区（0x0 ~ 0x2AA0000，不要写满整个 48MB）
nand kerase /dev/mtd7 0x0 0x3000000
nand kwrite /dev/mtd7 0x0 0x2aa0000 /upgtempfile/kernel.bin

# ② uboot 写到 mtd1
nand kerase /dev/mtd1 0x0 0x1c0000
nand kwrite /dev/mtd1 0x0 0x1c0000 /upgtempfile/uboot.bin
```

用脚本跑要给足等待时间（`@@秒`）：

```bat
python tools\telnet_session.py 192.168.1.1 <user> <pass> ^
  "echo 2 > /proc/zteinfo/factory/factorymode@@3" ^
  "touch /userconfig/nanddebug@@3" ^
  "nand kerase /dev/mtd7 0x0 0x3000000@@240" ^
  "nand kwrite /dev/mtd7 0x0 0x2aa0000 /upgtempfile/kernel.bin@@480" ^
  "nand kerase /dev/mtd1 0x0 0x1c0000@@60" ^
  "nand kwrite /dev/mtd1 0x0 0x1c0000 /upgtempfile/uboot.bin@@90"
```

### 为什么 uboot 必须一起刷（这一步漏了就永远起不来）

移动 V3.0.6 的 uboot 与联通 V3.0.5 的内核**不配套**：uboot 环境变量里写死了配套内核的引导参数
（rootfs 偏移等）。只刷 kernel 的结果是——联通内核引导失败 → 看门狗复位 → **双分区自动回落移动固件**。

于是你会看到：刷完、切槽、重启，2 分钟后**还是移动界面**。
设备没砖，但永远进不去联通，很多人卡在这里以为是固件包有问题。

> 恩山原帖那句「先刷入固件分区，然后刷入启动分区」，**「启动分区」指的就是 uboot（mtd1）**。
> uboot 的环境变量区在 0x280000 之后，`0x1c0000` 的写入范围碰不到它，bootargs 会保留。

---

## 8. 验证刷写结果

```bash
hexdump -C -n 16 /dev/mtd7                # 99 99 99 99 44 44 44 44 55 55 55 55 aa aa aa aa
hexdump -C -s 0x192 -n 6 /dev/mtd7        # 56 33 2e 30 2e 35 → "V3.0.5"
hexdump -C -s 0xf0800 -n 32 /dev/mtd1     # REV 魔数 + "V3.0.5P1N2"
upgradetest getver                        # Spare version num: V3.0.5P1N4
```

然后切槽重启：

```bash
upgradetest switchver 0     # 0/1 对应两个槽，切到刚刷好那一侧
reboot
```

2~4 分钟后设备以联通固件起来：登录页变成「管理员账户 / 其他账户」双入口，登录后跳 `unicom.html`。

**如果又是移动界面 = 回落了**，回去检查第 7 步的 uboot 到底写没写进去。

---

## 9. 切地区码，然后拔光纤物理复位

```bash
upgradetest sdefconf 306     # 306=重庆；其他地区见附录 E
reboot
```

`sdefconf` 会清掉配置文件，重启后按新地区模板重建。**此时 web 超密会被改成未知值**。

接着做一次彻底物理复位（这一步就是你说的「拔光纤 - reset 全灯亮」）：

1. **把光纤拔掉**（SC/APC 头收好，别磕碰端面）；
2. 通电状态下用卡针顶住 reset 小孔 **10~15 秒**；
3. 看到**所有指示灯同时亮一下再灭/闪**，松手（没反应就继续顶到 30~60 秒，不同批次固件判定阈值不同）；
4. 等 60 秒左右，设备以干净默认配置重启完成。

> 复位后**不要先赌 web 超密**。联通 V3.0.5P1N4 在部分地区模板下，默认库里的超密是按机器随机的，
> `CUAdmin/CUAdmin` 经常进不去。**第一件事是开 telnet**，进去以后用 shell 改密码——顺序反了纯浪费 10 分钟。

---

## 10. telnet 使能

设备起来后（能 ping 通 192.168.1.1），再次用 ZTElnet26 开壳：

```bat
third_party\ZTElnet26-windows-amd64.exe -i 192.168.1.1 -m <你电脑的MAC> -p 80 -u factorymode -pw "nE%jA@5b"
```

干净默认库下这一步**必过**（工厂凭据只在这时有效）。拿到随机临时账号后先跑三条只读命令确认环境：

```bat
python tools\tel_exec.py <临时用户> <临时密码> "cat /proc/mtd" "sendcmd 1 DB p DevAuthInfo" "sendcmd 1 DB p TelnetCfg"
```

要看的三件事：

| 看什么 | 期望 | 意义 |
|---|---|---|
| `TelnetCfg.Lan_Enable` | `0` | 现在 telnet 只是被工具临时打开，重启就没了 |
| `DevAuthInfo` 里 `Level=1` 和 `Level=2` 两行 | 都存在、`Enable=1` | 记下**哪一行是超管**，下一步要改它 |
| `MgtServer.Tr069Enable` | `1` | 远程下发通道还开着，等一下要关 |

---

## 11. 固化 + 改超密 + 关 TR069（一条命令）

这是全流程最关键的一步，也是网上教程错得最多的一步。

### 11.1 为什么不能直接 `sendcmd 1 DB set TelnetCfg ...`

因为 **`TelnetCfg` 在运行时是只读表**，`DB set` 对它**静默丢弃**——命令回 OK、读回还是 0。
对照实验：

```
sendcmd 1 DB set MgtServer 0 URL TESTPROBE    → 生效，读回 TESTPROBE
sendcmd 1 DB set TelnetCfg 0 Lan_Enable 1     → 无回显，读回仍是 0
```

所以真正的固化路径是**改设备上那个加密的配置文件**：

```
/userconfig/cfg/db_user_cfg.xml     ← AES-256-CBC + zlib，改完推回去
/userconfig/cfg/db_backup_cfg.xml   ← ★ 必须一起改，启动时会拿它覆盖上面那个
```

### 11.2 一条命令搞定

```bat
python tools\solidify.py 192.168.1.1 <临时用户> <临时密码> ^
  --admin 你的超管名:你的超管密码 ^
  --user  你的普通用户名:你的普通密码 ^
  --tr069-off --reboot
```

它会自动完成：

| 动作 | 内容 |
|---|---|
| 拉 paramtag 解密钥 | 每机唯一的 `INDIVKEY`，不拉这个解不开 |
| 解密 + 改 XML | `TelnetCfg`：`Lan_Enable=1`、密码 `12345`、`Max_Con_Num=999`、`ExitTime=999`、`InitSecLvl=3` |
| 改 web 账号 | **按 `Level` 定位行**，不认行号；同时把该行 `Enable` 置 1 |
| 关 TR069 | `MgtServer.Tr069Enable=0`、ACS 地址清空、停周期上报 |
| 回写两个文件 | `db_user_cfg.xml` + `db_backup_cfg.xml`，并做 MD5 双向校验 |
| 重启 | 60 秒后 telnet 自己就开了 |

**先看不动手**：加 `--dry-run`，只打印要改的行和字段，会把结果写到 `.temp/dryrun.xml` 里，方便对比。

### 11.3 关于「改哪一行」——别信行号，也别信网上的 Level

这里有个流传很广的错误说法：「`Level=2` 才是超管」。

本机（联通 V3.0.5P1N4 / 地区 306）实测结果**正好相反**：

| Row | User | Level | 实际身份 |
|---|---|---|---|
| 0 | `cqadmin` | **1** | **管理维护账号（超管）** |
| 1 | `user` | 2 | 普通账号 |

验证方法（实测）：

1. 登录页有两个入口，「管理员账户」提交的是 `Right=1`；用 `cqadmin` 的密码能从它进，
   进得去能看到「高级配置 / 设备管理」全套菜单；而 `Level=2` 那行（`user`）的密码对应的是
   「其他账户」入口（`Right=2`）。
2. 交叉核对：网页「设备管理 → 用户管理」页有「管理维护账号 / 普通账号」两个页签，
   各自显示该权限下的用户名，和 `sendcmd 1 DB p DevAuthInfo` 里的 User 对照即可。

所以脚本默认 `--admin-level 1`。**如果你的机器是反过来的**，加 `--admin-level 2` 再跑一次即可。
更稳妥的判断：改完用「管理员账户」入口登录一次，能进「高级配置」就是对的。

> 另外注意：`DevAuthInfo` 的 `Pass` 在 `sendcmd p` 的输出里恒为 `******`，**读不出原密码，只能覆写**。
> 好在配置文件的明文 XML 里是明文，`solidify.py --dry-run` 会把原值打出来给你看。

### 11.4 手工做的话（理解原理用）

```
1. pull  /tagparam/paramtag                      取 INDIVKEY
2. pull  /userconfig/cfg/db_user_cfg.xml          当前配置
3. 解密 → 改字段 → 重新压缩加密
4. 写入 /tmp/db_user_cfg.xml.new
5. cp 到 db_user_cfg.xml 和 db_backup_cfg.xml      ★两个都要
6. sync
7. reboot                                          ★不要 DB save、不要 DB rreset
```

三个必须记住的陷阱：

- **改完不要执行 `sendcmd 1 DB save`**：它用内存里的旧库重新序列化写回磁盘，你刚写的文件会被抹掉。
- **不要 `DB rreset`**：同理（脚本末尾那次 `rreset` 是在文件已是新版本之后做的内存重载，不影响磁盘）。
- **两个文件必须一起改**：只改 `db_user_cfg.xml`，重启后会被 `db_backup_cfg.xml` 还原。

---

## 12. 重启验证

等 60 秒后：

```bat
telnet 192.168.1.1 23
```

能连上就说明 `Lan_Enable=1` 生效了，用 `root / 12345` 登录（临时账号已经不需要了）。然后核对：

```bash
sendcmd 1 DB p TelnetCfg
#   Lan_Enable=1  Max_Con_Num=999  ExitTime=999  InitSecLvl=3
sendcmd 1 DB p MgtServer
#   Tr069Enable=0
md5sum /userconfig/cfg/db_user_cfg.xml /userconfig/cfg/db_backup_cfg.xml
#   两个 MD5 必须相同
```

**建议再重启一次复核**：有些机器第一次只是内存生效，第二次才真正读盘。
两次都能 `root/12345` 登进去，固化才算坐实。

顺手用浏览器登录一次 web（管理员账户 + 你设的超密），能进管理页而不是注册页，就说明密码也改对了。

---

## 13. 进光猫配业务（网页）

此时光纤还没插，属于"离线施工"。顺序建议照下面走，全部在厂商 UI 里点，别再用 shell 改 WAN。

### 13.1 上行线路配置（PPPoE 就在这里填）

> 这一节只给关键值和坑位；四条 WAN 的完整字段清单与网页 id 对照见
> [full-flow.md § 上行线路配置](full-flow.md#step-12--上行线路配置四条-wan-的目标参数)。

路径：**基本配置 → 上行线路配置**。ITMS 还没下发，列表可能是空的，需要**新建 WAN 连接**。

| 字段 | 值 |
|---|---|
| 连接名称 | `INTERNET`（会拼成 `1_INTERNET_R_VID_48`） |
| 封装类型 | `PPPoE` |
| 连接模式 | `路由` |
| 业务类型 | `INTERNET` |
| **VLAN 模式** | **`改写(tag)`** ← 不选这个，VLAN ID 是灰的、存不进去 |
| **VLAN ID** | 你当地的上网 VLAN（本例 48） |
| 802.1p | 0 |
| 用户名 / 密码 | 宽带账号 / 密码 |
| MTU | 1480 |
| IP 协议版本 | **`IPv4/v6`** ← 想有 IPv6 必须选这个 |
| 启用 NAT | 是 |

点「确定」/「修改」下发，然后点「连接」。

> ★ 最常踩的坑：打开这页发现 **VLAN ID 是空的**，就以为"这固件没地方填 VID"。
> 其实是因为**下拉框默认停在"新建WAN连接"**，那个表单本来就是空值。
> 必须先在连接下拉框里选中已有连接，表单才会回填真实值。核对配置时尤其注意这一点。

### 13.2 IPv6（三处缺一不可）

1. **WAN 侧**：上面那条连接的「IP 协议版本」= `IPv4/v6`。
2. **LAN 侧 RA**：LAN配置 → RA配置 → 使能 = 是（O 标志建议 = 是）。
3. **LAN 侧 DHCPv6**：LAN配置 → DHCPv6配置 → 启动 DHCP 服务 = 是。

验证：**状态 → 网络侧信息 → IPv6 WAN连接信息** 里能看到 `2408:.../64` 前缀，
客户端 ping 通 `2400:3200::1` 就通了。

> 前缀是运营商 **DHCPv6-PD** 委派下来的整个 /64，不是静态配的，网页上改不了也不需要改。

### 13.3 DNS（运营商 DNS 在 UDP 上会被劫持）

实测：联通下发的 `221.5.203.98` 在 **UDP** 查询下会把**任意域名**解析成 `192.168.1.1`（光猫自己），
TCP 查询却返回正确结果——这是运营商侧的伪解析器，不是光猫的锅。

处理：**LAN配置 → DHCPv4配置 → DNS来源 = 静态配置**，首选 `114.114.114.114`、备选 `8.8.8.8`。
IPv6 的 RA DNS 由运营商下发、光猫改不动，只在客户端上覆盖 `2400:3200::1`。

### 13.4 WiFi

**基本配置 → WLAN配置**。改密码只改 **`WPA 预共享密钥`**（`Frm_KeyPassphrase`）这一栏。

> 页面上那四个「密钥1~4」是 **WEP 的轮换密钥槽**，认证方式是 WPA/WPA2-PSK 时完全不参与认证，
> 改它们不会影响连接密码。这是个常见误解。

### 13.5 IPTV（可选，看你要不要单线复用）

默认只是桥接 + 绑一个 LAN 口，机顶盒只能插那一个口。要做「一根线同时跑上网和 IPTV」，
走 **基本配置 → 绑定设置 → VLAN 绑定**：把 LAN1 的 VLAN 绑定写成两行 `48/48`、`3185/3185`，
然后用一根网线接路由器 WAN，路由器里设 IPTV VLAN = 3185，机顶盒插路由器指定的 IPTV 口。

完整原理、位掩码换算、抓包验证与四层排查，见 [iptv-single-line.md](iptv-single-line.md)。

---

## 14. 插回光纤，LOID 注册

1. 插回光纤，等 PON 灯常亮（约 30 秒）；
2. 浏览器打开 `http://192.168.1.1/`，用你的超密登录；
3. 注册页填 **LOID**（联通给的宽带识别码，24 位以内），密码留空或按当地要求填，点注册；
4. 页面每 4 秒轮询一次进度，成功标志是 `Status=0`、`Result=1`，随后 PPPoE 自动拨上。

注册页的判定只有一句：`Status=="0" && Result=="1"` 才算「已注册」，其余一律回到 LOID 表单。
没注册成功时 `PDTCTUSERINFO` 里是 `Status=99 Result=99`。

---

### 14.1 一直跳 LOID 注册页怎么办（有线、WiFi 都跳）

**现象**：插网线也好、连 WiFi 也好，打开 `192.168.1.1` 就被强制跳到 LOID 注册页，
输超密登录后也进不了管理界面，改哪个口、换哪台电脑都一样。

**原因**：这**不是**网络问题，跟 LAN 口绑定、WiFi、路由都没有关系。
拦截在 httpd 这一层，是全局的：

```
register.gch 的逻辑：
  Status == "0" && Result == "1"  →  输出「已注册成功，无需再注册。」
  否则                            →  渲染 LOID 表单；登录后 redirect 到注册页
```

所以「换有线 / 换 WiFi / 换浏览器 / 清 cookie」全都没用，因为判定值不合格。
设备只是认为自己**没注册**，把 web 入口锁死了。

**解法：三条 set 把注册状态写成「已完成」，再 save + 同步备份 + 重启。**

```
sendcmd 1 DB set PDTCTUSERINFO 0 Status 0
sendcmd 1 DB set PDTCTUSERINFO 0 Result 1
sendcmd 1 DB set PDTCTUSERINFO 0 AutoRegFlg 0
sendcmd 1 DB save
cp /userconfig/cfg/db_user_cfg.xml /userconfig/cfg/db_backup_cfg.xml
reboot
```

三条 set 各自的作用，少一条都不行：

| 命令 | 作用 | 少写的后果 |
|---|---|---|
| `Status 0` | 注册状态=成功 | 判定不通过，照旧跳 |
| `Result 1` | 注册结果=成功 | 判定不通过，照旧跳 |
| `AutoRegFlg 0` | 关掉开机自动注册 | 重启后被自动改回 `99/99`，白干 |

后面两条同样不能省：

| 命令 | 作用 | 少写的后果 |
|---|---|---|
| `DB save` | 把内存 DB 落盘到 `db_user_cfg.xml` | 重启后改动全丢 |
| `cp ... db_backup_cfg.xml` | 同步备份文件 | `DB save` **只写** `db_user_cfg.xml`，重启时被 backup 回滚，一样全丢 |
| `reboot` | 让 httpd 重新加载 | **改完 DB 网页不会立刻变**，因为 httpd 缓存了 `OBJ_USER_REGISTER` 运行态对象，kill httpd 重启也没用，必须整机重启 |

**验证（三条都实测过）：**

1. 命令行直接问注册页：
   ```bash
   curl -s "http://192.168.1.1/register.gch"
   ```
   期望只返回一句中文：**`已注册成功，无需再注册。`** —— 没有 LOID 输入框、没有表单。
2. 复查数据库：
   ```
   sendcmd 1 DB p PDTCTUSERINFO
   ```
   期望 `Status=0`、`Result=1`、`AutoRegFlg=0`。
3. **重启后再查一遍**。值仍是 `0/1/0` 才算真的固化住；如果变回 `99/99`，说明 `AutoRegFlg`
   没写进去，或者 `db_backup_cfg.xml` 没同步。

**三个坑（都是踩过的）：**

| 坑 | 现象 | 正解 |
|---|---|---|
| 改完 DB 不重启 | 命令执行成功，网页照旧跳 | 必须 `reboot`，httpd 只认启动时加载的那份 |
| 只 `DB save` 不同步 backup | 重启后一切回滚 | 手补 `cp db_user_cfg.xml db_backup_cfg.xml` |
| 只改 `CheckRegistEnable 0` | 注册页纹丝不动 | 判定值是 `Status`/`Result`，`CheckRegistEnable` 只管注册按钮是否可点 |

**副作用，改之前要知道：**

- 这等于把**本地注册入口关掉了**。以后真要重新做 LOID 注册，先改回来再重启：
  ```
  sendcmd 1 DB set PDTCTUSERINFO 0 Status 99
  sendcmd 1 DB set PDTCTUSERINFO 0 Result 99
  sendcmd 1 DB set PDTCTUSERINFO 0 AutoRegFlg 1
  sendcmd 1 DB save
  cp /userconfig/cfg/db_user_cfg.xml /userconfig/cfg/db_backup_cfg.xml
  reboot
  ```
- 它只骗过**本地网页的跳转判定**，不改变 OLT 侧的真实注册状态。如果 PON 灯还在闪
  （物理层没注册上），网页不跳了，网照样上不了 —— 这时候该查的是光纤和 LOID，不是这条命令。
- 表里的 `UserName` 是你提交过的 LOID / 宽带账号，留空说明从没提交成功过。

---

### 14.2 注册后运营商下发覆盖配置

注册成功后运营商可能下发业务模板（多出 TR069 等 WAN 行）。因为我们在第 11 步已经把
`Tr069Enable` 关了、`AutoRegFlg` 也置 0，正常情况下它**改不动**你的配置。

如果发现 WAN 列表突然变多、端口绑定冒出一堆没配过的行、或者 IPTV 突然不能看了，
说明下发通道又开了，按 [post-flash-runbook.md §3](post-flash-runbook.md) 断掉再恢复备份。

---

## 15. 收尾：备份一份干净配置

```bat
python tools\backup_restore.py 192.168.1.1 root 12345 backup
```

产出在 `backups/<日期>/`：加密原文件（回滚用）、明文 XML（可读可 diff）、paramtag（密钥）、摘要。

以后哪天配置被搞乱了，一条命令回滚：

```bat
python tools\backup_restore.py 192.168.1.1 root 12345 restore backups\<日期>\db_user_cfg.xml --reboot
```

---

## 16. 验收清单

| 检查项 | 怎么查 | 期望 |
|---|---|---|
| 固件版本 | 状态 → 设备信息 | 联通 V3.0.5P1N4 |
| 地区码 | 状态页 / `cat /etc/init.d/regioncode` | 你选的那个 |
| telnet 自启 | 重启后 `telnet 192.168.1.1 23` | 不借任何工具就能连 |
| telnet 账号 | `root / 12345` | 登录成功 |
| 连接数 / 超时 | `sendcmd 1 DB p TelnetCfg` | `Max_Con_Num=999`、`ExitTime=999` |
| web 超密 | 浏览器「管理员账户」 | 能进，看到「高级配置」 |
| TR069 | `sendcmd 1 DB p MgtServer` | `Tr069Enable=0` |
| 两文件一致 | `md5sum db_user_cfg.xml db_backup_cfg.xml` | MD5 相同 |
| 上网 | 电脑 ping 223.5.5.5 | 通，延迟正常 |
| IPv6 | ping `2400:3200::1` | 通 |
| 备份 | `backups/<日期>/` | 四个文件齐全 |

---

## 17. 出问题看哪里

| 现象 | 先看 |
|---|---|
| 刷完重启还是移动界面 | 第 7 步 uboot —— 没刷或刷错分区 |
| 复位后 `CUAdmin/CUAdmin` 进不去 | 正常，复位默认库超密可能是随机的 → 先开 telnet 再用脚本改 |
| 改了超密却登不进 | 改错行（Level 认反了）→ 第 11.3 节 |
| 重启后 telnet 又关了 | 只覆盖了 `db_user_cfg.xml`，没覆盖 `db_backup_cfg.xml` |
| PPPoE 一直超时、IP 全 0 | VLAN 模式没选「改写(tag)」/ VLAN ID 没填 → 第 13.1 节 |
| 域名解析全变成 192.168.1.1 | 运营商 UDP DNS 劫持 → 第 13.3 节 |
| 过几天配置自己变了 | TR069 还开着 → 关掉再恢复备份 |
| 网页点确定报「当前操作无效」 | 手改过 WAN 行、索引没重建 → 用 `restore_base.py` 以原厂备份为基底重做 |
| **有线 / WiFi 打开就跳 LOID 注册页** | `PDTCTUSERINFO` 不是 `0/1` → 第 14.1 节，三条 set + cp + 重启 |
| 改完注册状态、重启还是跳 | `AutoRegFlg` 没置 0，或没 `cp` 到 `db_backup_cfg.xml` → 第 14.1 节 |
| 注册页不跳了但网还是不通 | 命令只改本地判定，PON 没注册上照样不通 → 查 PON 灯与 LOID |

更多坑位记录见仓库 README 的**附录 A**（七个大坑）与**附录 B**（杂项速查）。

---

## 附：一路踩过的坑（摘要）

这些是真正卡住人的点，详细版在 README 附录：

1. **只刷 kernel 不刷 uboot → 永远回落移动**。
2. **`TelnetCfg` 运行时只读**，`DB set` 静默无效，必须改配置文件。
3. **改完不能 `DB save`**，会把你的修改用内存旧值覆盖回去。
4. **两个配置文件要一起改**，否则被备份还原。
5. **`-m` 参数是电脑的 MAC**，抄别人的必失败。
6. **网卡网络类别是"公用"时**，TFTP/HTTP 全被防火墙拦。
7. **VLAN ID 填不进去**，是因为 VLAN 模式没选「改写(tag)」。
8. **运营商 UDP DNS 是伪解析器**，换 114。
9. **WEP 密钥 1~4 不是 WPA 密码**，改 `WPA 预共享密钥`。
10. **XGPON 不是想切就能切**，局端是 GPON 你切过去就失联。

---

> 本文基于一台真实设备的完整刷机记录整理。感谢恩山 HavingFun、danch744、xiafeifei 等先行者的帖子，
> 以及 starofys 的 zte-telnet 实现。文中所有"实测"结论都可以在你自己的机器上复现验证。
