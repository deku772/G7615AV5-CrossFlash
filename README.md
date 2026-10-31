# ZXHN G7615AV5 跨运营商刷机工具包（移动 → 联通）

中兴 ZXHN G7615AV5（10G GPON，硬件 V2.0）**移动版刷联通固件**的完整实战流程与配套工具。
全部命令与偏移量均为实机验证，非转载拼凑。

> 本仓库源于一次完整的刷机实战（2026-10，广东移动 V3.0.6P2T3 出发 → 联通 V3.0.5P1N4 + 重庆地区码落地），
> 整理成文以便后来者少踩坑。恩山相关帖子给出了方向，但**关键细节（uboot 必须刷、账户表行号、
> telnet 获取方式、固件包结构）在实机验证前都是空白或以讹传讹**，本仓库逐一补全。

## 最终成果

| 项目 | 刷机前 | 刷机后 |
|---|---|---|
| 运营商固件 | 移动 V3.0.6P2T3/P3N4 | **联通 V3.0.5P1N4** |
| 管理界面 | 移动版 | 联通版 `unicom.html` |
| 超级管理员 | CMCCAdmin / aDm8H%MdA | **CUAdmin / CUAdmin** |
| 地区码 | 410（广东，移动式编码） | **306（重庆，联通式编码）** |
| telnet | 工厂模式工具临时开启 | 同左（本机固件 sendcmd 固化无效，见[坑 3](#常见坑)） |
| 备用分区 | 移动 V3.0.6P3N4 | 保留（天然"后悔药"，可 `switchver` 切回移动） |

## ⚠️ 免责声明

- 刷机有变砖风险。**刷 uboot（mtd1）是全流程唯一可能真砖的步骤**，失败需拆机 TTL 串口救砖。
- `nand kerase/kwrite` 期间**绝对不能断电**（约 3~8 分钟）。
- 填错分区号可能造成 NAND 坏区。**每台机器分区布局可能不同，命令必须先用 `cat /proc/mtd` 核对，不要照抄**。
- 仅供个人设备折腾学习，请遵守当地法律法规。

## 仓库内容

```
├── README.md                  # 本文档
├── docs/
│   └── config-snapshot-*.md   # 网页抓取的全量配置快照（只读留档/可复现参考）
├── tools/                     # 自研工具脚本（纯 Python，零第三方依赖）
│   ├── telnet_session.py      # telnet 自动化会话（Windows 下批量执行命令/抓输出）
│   ├── unicom_login.py        # 联通版 web 登录器（sha256+动态 token，自带失败限速）
│   ├── tftp_server.py         # TFTP 分区备份服务器（光猫 tftp -p 推送）
│   ├── http_file_server.py    # HTTP 固件下发服务器（光猫 wget 拉取，无 32MB 限制）
│   ├── cdp.py                 # 零依赖 CDP 客户端（纯标准库 WebSocket + JSON-RPC）
│   ├── zte_ui.py              # 网页操作助手（Playwright 接管本机 Edge：登录/查状态/配 WAN）
│   ├── zte_snapshot.py        # 全量配置快照抓取（状态/基本配置/高级配置/设备管理）
│   └── extract_firmware.py    # 联通固件包拆解（切出 kernel / uboot 镜像）
├── firmware/
│   ├── kernel_p1n4.bin        # 联通 kernel 镜像  44,695,552 字节  MD5 b00edea2bac30985305df345d0b876cb
│   ├── uboot_unicom.bin       # 联通 uboot 镜像   1,835,008 字节  MD5 ec60ef2071a60b7d422e252ca7f52248
│   └── MD5SUMS.txt
├── backups/                   # 一台真实设备（本仓库作者机）的分区备份样本
│   ├── paramtag.bin           # parameter tags 2MB  ★含设备 SN/光校准，每机唯一
│   ├── wlan.bin               # wlan           2MB  ★含 Wi-Fi 校准，每机唯一
│   ├── usercfg.bin            # usercfg        8MB  ★含账户库/配置（db 加密格式）
│   └── MD5SUMS.txt
└── third_party/               # 第三方工具本体（归属见下节）
    ├── go_build_zte_go.exe    # zte-telnet (starofys)  Windows 构建版
    ├── ZTElnet26-windows-amd64.exe  # ZTElnet 2.6（恩山 HavingFun）
    └── MD5SUMS.txt
```

> `zte_ui.py` / `zte_snapshot.py` 需要 `pip install playwright`（**只装 Python 包**，
> 直接用系统已装的 Edge/Chrome，不用 `playwright install` 下载内核）。
> 内网/断网环境可改用 `tools/cdp.py`（零依赖，自己实现 WebSocket）。

原始完整升级包（53MB，HavingFun 重打包版）见[参考链接](#参考链接)，可用 `tools/extract_firmware.py` 自行拆解出上述两个镜像。

### 第三方工具归属与版权

| 文件 | 作者 | 来源 | 许可 |
|---|---|---|---|
| `go_build_zte_go.exe` | starofys | [github.com/starofys/zte-telnet](https://github.com/starofys/zte-telnet) | 随上游仓库（开源） |
| `ZTElnet26-windows-amd64.exe` | HavingFun | [恩山论坛](https://www.right.com.cn/forum/thread-8476080-1-1.html)（免费附件） | 闭源，仅供学习交流，请勿商用倒卖 |

两者均从原始渠道原样收录（MD5 见 `third_party/MD5SUMS.txt`），版权归原作者；本仓库不做任何修改与再打包。
ZTElnet26 其余平台（linux/mac/arm）的构建版请到恩山原帖下载。

### 设备备份样本说明（backups/）

这是**一台真实设备的原厂备份**，仅供需要研究分区内部结构的人参考（paramtag 的标签布局、
usercfg 的加密配置头 `01 02 03 04 ...` 等）。

- **不能直接刷进你的机器**：paramtag/wlan 含每台设备独有的光功率校准，usercfg 绑定 SN——
  跨机写入轻则光模块指标异常，重则注册状态混乱。
- 备份中含设备 SN 与账户库，公开于此是经过设备所有者确认的决定；**你若想贡献自己的备份，请先想清楚
  SN 泄露的影响**（如将来在运营商网络注册时可能被他人冒用报装）。

## 环境准备（Windows）

1. **Python 3**（四个工具脚本零第三方依赖）。
2. 电脑网线直连光猫任意 LAN 口，电脑与光猫同网段（移动版默认 `192.168.1.1`，若已改网段则对应调整）。
3. **把这块网卡的网络类别改为"专用"**（设置 → 网络 → 属性）。公用 profile 下 Windows 防火墙会拦截
   UDP 69（TFTP 备份）与 8001 端口（HTTP 下发），现象是光猫侧 `tftp: timeout` 而服务器毫无日志。
4. 记下电脑有线网卡 MAC（开 telnet 工具的 `-m` 参数用，**是电脑的 MAC，不是光猫的**——论坛帖里抄别人 MAC 必失败）。

---

# 全流程

## Step 0 · 确认设备状态

```
telnet: cat /proc/mtd                  # 分区表（见文末，必须先核对）
        cat /proc/csp/versionstates    # 当前运行分区 current=0/1
        fw_flashing                    # curpdev=/dev/mtd7 或 mtd8 = 当前运行分区
        upgradetest getver             # Main/Spare 版本
```

**刷写目标 = 非运行分区**（运行 mtd8 就刷 mtd7，反之亦然）。当前运行的分区从头到尾不要碰——
这是双分区机制给你的保命后路：新固件起不来会自动回落。

## Step 1 · 开启 telnet（二选一）

**方案 A：ZTElnet26（推荐，新旧固件通吃，复位后/重启后均有效，本体见 `third_party/`）**

```
ZTElnet26-windows-amd64.exe -i 192.168.1.1 -m <电脑MAC无冒号> -p 80 -u factorymode -pw "nE%jA@5b"
```

输出临时账号密码（每次随机）。`factorymode / nE%jA@5b` 是硬复位后的工厂模式默认凭据，长期有效。

**方案 B：go_build_zte_go（github.com/starofys/zte-telnet，需要当前有效的 web 超密，本体见 `third_party/`）**

```
go_build_zte_go.exe -addr http://192.168.1.1:80 -mac <电脑MAC> -username CMCCAdmin -password aDm8H%MdA
```

> 移动版超密 `CMCCAdmin / aDm8H%MdA`；联通版 `CUAdmin / CUAdmin`；电信版 `telecomadmin / nE7jA%5m`。
> 注意：这套工具最后一步 CheckLoginAuth 走 web 账户库，超密失效（如改地区复位后）就 401，此时用方案 A。

拿到临时账号后用本仓库工具执行命令（Windows 自带 telnet.exe 无法自动化）：

```
python tools\telnet_session.py 192.168.1.1 <临时用户> <临时密码> "upgradetest getver"
```

## Step 2 · 备份分区（必做！救砖保险）

```
python tools\tftp_server.py backup
```

telnet 侧逐个推送（假设电脑 IP 192.168.1.100）：

```
tftp -p -l /dev/mtd1 192.168.1.100    # uboot        3MB
tftp -p -l /dev/mtd2 192.168.1.100    # others       2MB
tftp -p -l /dev/mtd3 192.168.1.100    # paramtag     2MB  ★每机唯一（光校准）
tftp -p -l /dev/mtd4 192.168.1.100    # wlan         2MB  ★每机唯一（Wi-Fi 校准）
tftp -p -l /dev/mtd5 192.168.1.100    # usercfg      8MB  ★含账户库/SN/配置
tftp -p -l /dev/mtd6 192.168.1.100    # middle       6MB
```

> **paramtag / wlan / usercfg 是每台机器独有的，别人的备份不能替代你的**。救砖回刷全靠它们。
> （`backups/` 目录收录了一台真实设备的备份样本，仅供研究分区结构，不可跨机刷入，详见上文说明。）
> busybox tftp 受 16 位块号限制单文件最大 32MB，大分区（kernel/osgi）如需备份用 `dd` 分段传。

## Step 3 · 拆解固件包

```
python tools\extract_firmware.py D:\ZXHN_G7615AV5_UNI_V3.0.5P1N4.bin firmware
```

得到 `kernel_p1n4.bin`（44.7MB）与 `uboot_unicom.bin`（1.8MB），MD5 与本仓库参考值一致即可用本仓库现成镜像。

## Step 4 · 上传固件到光猫并校验

```
python tools\http_file_server.py firmware 8001
```

telnet 侧（`/upgtempfile` 是 100MB tmpfs，放得下）：

```
wget -O /upgtempfile/kernel.bin http://192.168.1.100:8001/kernel_p1n4.bin
wget -O /upgtempfile/uboot.bin  http://192.168.1.100:8001/uboot_unicom.bin
md5sum /upgtempfile/kernel.bin    # 必须与电脑端一致!
md5sum /upgtempfile/uboot.bin
```

> tmpfs 重启即清空；如果中途重启过，重新 wget。

## Step 5 · 刷写（kerase/kwrite 期间严禁断电）

假设当前运行 mtd8（`fw_flashing` 确认），目标为 mtd7：

```
echo 2 > /proc/zteinfo/factory/factorymode      # 开启工厂模式
touch /userconfig/nanddebug                     # 解除 nand 写保护

# ① 刷 kernel 到备用分区
nand kerase /dev/mtd7 0x0 0x3000000             # 擦除整分区 48MB
nand kwrite /dev/mtd7 0x0 0x2aa0000 /upgtempfile/kernel.bin

# ② 刷 uboot（关键步骤！见下方说明）
nand kerase /dev/mtd1 0x0 0x1c0000
nand kwrite /dev/mtd1 0x0 0x1c0000 /upgtempfile/uboot.bin
```

用 telnet_session.py 执行时给长命令加等待：

```
python tools\telnet_session.py 192.168.1.1 <user> <pass> ^
  "echo 2 > /proc/zteinfo/factory/factorymode@@3" ^
  "touch /userconfig/nanddebug@@3" ^
  "nand kerase /dev/mtd7 0x0 0x3000000@@240" ^
  "nand kwrite /dev/mtd7 0x0 0x2aa0000 /upgtempfile/kernel.bin@@480" ^
  "nand kerase /dev/mtd1 0x0 0x1c0000@@60" ^
  "nand kwrite /dev/mtd1 0x0 0x1c0000 /upgtempfile/uboot.bin@@90"
```

> **为什么必须刷 uboot**：移动 V3.0.6 的 uboot 与联通 V3.0.5 内核不配套（uboot 环境变量里写死了
> 配套内核的引导参数，如 rootfs 偏移）。只刷 kernel 的结果是：联通内核引导失败 → 看门狗复位 →
> 双分区机制自动回落移动。**设备不会砖，但也永远不会起来**——这是本流程最容易漏的一步，
> 恩山"先刷入固件分区，然后刷入启动分区"这句话里的"启动分区"指的就是 uboot（mtd1）。
> uboot 环境变量区（0x280000+）在 0x1c0000 写入范围之外，bootargs 等会保留。

## Step 6 · 验证刷写结果

```
hexdump -C -n 16 /dev/mtd7                # 99 99 99 99 44 44 44 44 55 55 55 55 aa aa aa aa
hexdump -C -s 0x192 -n 6 /dev/mtd7        # 56 33 2e 30 2e 35  → "V3.0.5"
hexdump -C -s 0xf0800 -n 32 /dev/mtd1     # REV魔数 aa aa aa aa 55 55 55 55 44 44 44 44 99 99 99 99 + "V3.0.5P1N2"
upgradetest getver                        # Spare version num: V3.0.5P1N4
```

## Step 7 · 切换启动分区并重启

```
upgradetest switchver 0    # 0/1 对应备用/当前，切到刚刷好的一侧
reboot
```

2~4 分钟后设备以联通固件启动：登录页变为"管理员账户/其他账户"双账户样式，
登录成功后跳转 `unicom.html`。**若又回到移动界面 = 引导失败回落**（检查 Step 5 的 uboot 是否真刷了）。

## Step 8 · 切换地区码并复位

> 联通配置文件与移动有出入、地区码编码体系不同（移动式 410=广东 vs 联通式 310=广东），
> 不切换会有各种奇怪问题（如管理页显示"区域 undefined"）。

```
upgradetest sdefconf 306    # 306=重庆；完整地区码表见文末
reboot
```

`sdefconf` 会删除配置文件，重启后按新地区码重建（**此时超密会被地区模板改写为未知值**）。
为确保配置彻底干净，建议再做一次**物理复位**：通电状态下顶住 reset 小孔 10~15 秒，指示灯全亮即成。

> 帖子经验：怕折腾就切 `sdefconf 0`（联通默认地区），超密保持 `CUAdmin/CUAdmin` 可预期。

## Step 9 · 找回超密（重要行号陷阱）

改地区/复位后超密失效？用 **ZTElnet26（方案 A）再开 telnet**，**先查 Level 再改行号**：

```
sendcmd 1 DB p DevAuthInfo        # 看哪一行 Level=2（2=超管，1=普通）
```

实机（联通 V3.0.5P1N4 + 地区 306）验证结果与常见教程**相反**：

| Row | Level | 角色 |
|---|---|---|
| 0 | 1 | 普通用户（user） |
| 1 | **2** | **超级管理员（CUAdmin）** |
| 2~5 | 0 | 未启用 |

```
sendcmd 1 DB set DevAuthInfo 1 User CUAdmin     # ★ 本固件超管在第 1 行（Level=2）
sendcmd 1 DB set DevAuthInfo 1 Pass CUAdmin
sendcmd 1 DB set DevAuthInfo 0 User user        # 第 0 行是普通用户
sendcmd 1 DB set DevAuthInfo 0 Pass <普通密码>
sendcmd 1 DB save
```

> 改错行的典型症状：命令全部回 OK、`DB save` 也成功，但 web 登录照旧失败。
> **别信行号，信 Level**。DevAuthInfo 的 User/Pass 在 `p` 输出里是 `******`，看不到原值，
> 只能覆写——所以"读出原密码"这条路不存在，只能重置成已知值。
> web 登录 3 次失败会锁定约 60 秒，别连点。


## Step 9.5 · 死锁态自救（web 超密未知 + telnet 关闭）

现象组合：`sdefconf` 改写超密 → ITMS 又下发一次 → 忘了/从未知道超密，同时 23 端口关闭、
ZTElnet26 报 401。此时**没有任何软件路径能进去**，只能物理硬复位。实机诊断值（可作为状态判断依据）：

| 观测点 | 正常/已注册 | 死锁态 |
|---|---|---|
| `GET /` 页面内 `var Status / var Result` | `0 / 1` | `99 / 99`（注册态丢失或未完成） |
| `GET /register.gch` 内 `RxPower/TxPower` | -15.5 dBm / 1.97 dBm = 光路正常 | 同上（光没问题，别怀疑光纤） |
| `POST /` 登录失败后响应 | 含 `var Lognumber = N;` | `N` 递增，≥3 锁 60s |
| `GET /tr069_registering.gch` | 只有 3 秒 meta refresh，**不是全站劫持** | 任意路径仍返回正常 404 |
| `ZTElnet26 -m <电脑MAC>` | 打印临时账号 | `http code err 401` |

### 复位后的"黄金 10 分钟"（顺序不能错，光纤必须还没插）

```
① 拔光纤 → 顶 reset ≥60s（等 4 个网口灯同时闪/灭）→ 松手
② 立刻用 ZTElnet26 开 telnet（干净库下 factorymode 必过）——★ 别先试 CUAdmin
③ 用 telnet 覆写 DevAuthInfo（Row1=超管），顺手改 WiFi、关 TR-069
④ 手动建 WAN（internet / iptv 两条，见下）
⑤ 最后才插回光纤 → register.gch 填 LOID → 观察 Status 变 0 / Result 变 1
```

> **★ 实机修正：硬复位并不会把 web 超密还原成 `CUAdmin/CUAdmin`。**
> 联通 V3.0.5P1N4 + 地区 306 的默认库里超密是**按机随机**的，复位后第一个能进的门
> 是 factorymode（telnet），不是 web。实测序列：复位后 `CUAdmin` 登录 → `Lognumber=1` 失败；
> 同一时刻 `ZTElnet26` 直接开出临时账号。**先开 telnet，再用 telnet 改 web 密码**，顺序反了会白等。

```bash
# ③ 开 telnet（-m 用本机有线网卡 MAC，无冒号）
third_party/ZTElnet26-windows-amd64.exe -i 192.168.1.1 -m <电脑MAC> -p 80 -u factorymode -pw "nE%jA@5b"
```

```
# ③ 固化两个账户（本固件 Row1=超管 Level2 / Row0=普通 Level1；先 p 一遍确认 Level）
sendcmd 1 DB p DevAuthInfo
sendcmd 1 DB set DevAuthInfo 1 User CUAdmin
sendcmd 1 DB set DevAuthInfo 1 Pass <你的超密>
sendcmd 1 DB set DevAuthInfo 0 User user
sendcmd 1 DB set DevAuthInfo 0 Pass <你的普通密码>
# 关掉 ACS，避免插光纤后再次被下发覆盖（表名以本机 p MgtServer 结果为准）
sendcmd 1 DB set MgtServer 0 URL ""
sendcmd 1 DB set MgtServer 0 PeriodicInformEnable 0
# 更彻底：连 TR069 那条 WAN 一起停掉，防止 DHCP option 43 把 ACS 地址又塞回来
sendcmd 1 DB set WANC 0 Enable 0
sendcmd 1 DB set WANC 1 Enable 0
sendcmd 1 DB save
```

> 顺序的关键：**先断管理通道，再入网**。只要 ACS 还通，插回光纤后的首次上线依旧会把
> DevAuthInfo / SSID / WAN 全部重写一遍，前面所有手工配置等于白做。
> 仅清空 URL 不够——联通侧常用 DHCP option 43 做 ACS 发现，URL 会被重新填回；
> 停掉 TR069 的 WAN（本例是 VLAN 3600 的两条 `*_TR069_*`）才算真断。

### 登录脚本（已按本固件页面复刻，可直接验证密码）

```bash
python tools/unicom_login.py --acct adm --pass CUAdmin --tries 1
python tools/unicom_login.py --acct oth --pass <普通密码>
```

> 表单真实字段是 **`Password`**（`id=UserPW` 只是元素 id），提交 `UserPW=...` 会被服务器当无效请求
> 直接回登录页、且**不报错**——这是早前"401/失败"结论不可信的原因之一。

---

# Step 10 · 全程走网页配置（不碰 telnet 写库）

前置：想让所有改动都发生在厂商 UI 上，就用 Playwright 接管本机已装的 Edge，
**不需要下载浏览器内核**（`channel=msedge` / 或直接连已有的调试端口）。

```bash
# ① 用独立 profile 起一个带调试端口的 Edge（不影响日常浏览器）
"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  --remote-debugging-port=9222 \
  --user-data-dir="<仓库>/.temp/edgeprof" --no-first-run \
  --no-default-browser-check http://192.168.1.1/

# ② 脚本通过 CDP 接管它
python tools/zte_ui.py status        # 看 ONU 注册状态 + WAN 连接
python tools/zte_ui.py wanlist       # 列 WAN
python tools/zte_snapshot.py docs/config-snapshot-2026-10-31.md   # 抓全量配置快照
```

> `tools/cdp.py` 是零依赖的 CDP 客户端（纯标准库实现的 WebSocket + JSON-RPC），
> 断网环境也能用；`tools/zte_ui.py` / `tools/zte_snapshot.py` 改用 Playwright 写。

## 页面结构（不摸清就会点错地方）

| 层 | 位置 | 说明 |
|---|---|---|
| 单页菜单 | `/` 的 `#menu0`~`#menu6` | `onclick="enterFrame('status'|'basic'|'advance'|'devmanager')"` |
| 框架页 | `unicom.html` | `topFrame` = 菜单（`#mmStatu/#mmNet/#mmAdv/#mmManager`），`mainFrame` = 内容 |
| 内容页 | `getpage.gch?pid=1002&nextpage=*.gch` | 左侧二级菜单 + 右侧表单，`_SESSION_TOKEN` 藏在 hidden 里 |

- 登录：`GetAccessAccount('adm')` → 填 `#Frm_Password` → 点 `#LoginId`。
  **不要自己拼 sha256**，`passwordSHA256()` 会在页内算好并写进 `UserPW`。
- 光猫**只允许一个活动会话**：新开标签页会把旧会话挤掉，全程复用一个 page 对象。
- 桥接/改封装类型后，NAT、MTU 等区块会整块 `display:none`，Playwright 的 `fill()` 会超时；
  用 `evaluate` 直接改 `checked` / `value` 绕过。

## 三个真正卡住人的坑

### 坑 A · 业务下发的 INTERNET WAN 没有 VID

LOID 注册成功后，ITMS 会下发业务模板，本例生成：

```
1_TR069_R_VID_3600   DHCP，VLAN 3600   ← ACS 通道
2_INTERNET_R_VID_    PPPoE，VLAN 缺失  ← 连接名里 VID 是空的！
```

`2_INTERNET_R_VID_` 的 **VID 后缀为空 = VLAN ID 没写进去**（对照 TR069 那条的 `VID_3600`）。
症状是 PPPoE 一直"连接ISP服务器超时"、IP 全 0.0.0.0。

解法（网页：基本配置 → 上行线路配置 → 选中该连接）：

| 项 | 值 |
|---|---|
| VLAN 模式 | **改写(tag)**（不是"不启用(untag)"） |
| VLAN ID | **48** |
| 802.1p | 0 |
| 用户名/密码 | `clan2301317426` / `687708`（用户名业务侧已填好，密码要自己补） |

改完连接名会变成 `2_INTERNET_R_VID_48`，点「修改」下发，再点「连接」。

### 坑 B · 运营商 UDP DNS 被伪解析器劫持

联通下发的 DNS（`221.5.203.98` / `221.7.92.98`）在 **UDP** 上会把**任意域名**解析成
`192.168.1.1`（光猫自己），TCP 查询却返回真实结果。伪解析器特征：

```
aa=1（权威位）  TTL=0  随机不存在的域名也返回 192.168.1.1
```

实测可用 / 不可用（UDP）：

| 可用 | 不可用（返回 192.168.1.1） |
|---|---|
| `114.114.114.114`、`8.8.8.8`、`2400:3200::1`、`2606:4700:4700::1111` | 联通 `221.5.203.98`/`221.7.92.98`、`119.29.29.29`、`223.5.5.5`、`180.76.76.76` |

光猫侧：基本配置 → LAN配置 → DHCPv4配置 → **DNS来源 = 静态配置**，
首选 `114.114.114.114`、备选 `8.8.8.8`（IPv6 的 RA DNS 由运营商下发，改不动，
客户端侧再覆盖 `2400:3200::1` / `2606:4700:4700::1111`）。

> 排查手法：直接用 Python 发 DNS 报文对比 UDP/TCP，比在浏览器里 nslookup 直观得多。

### 坑 C · 网页没有配置导出

设备管理 → 设备管理 → **USB备份配置** 需要 U 盘；「强制推送配置」是推给 ACS 的开关。
本固件网页**无法导出配置文件**。两个替代方案：

1. `tools/zte_snapshot.py` 抓全量配置快照（Markdown），作为可复现的留档；
2. 真要二进制备份，就得重新开 telnet——但**业务下发之后 `factorymode/nE%jA@5b` 会稳定 401**，
   只在"硬复位后的默认配置"下有效（见 Step 9.5）。

---

## DevAuthInfo 的行号：别信行号，信 Level

> **移动和联通固件的行号语义确实可能不同**，网上教程也有把 Row0 当超管的。
> 唯一可靠的做法是看 `Level` 字段：`sendcmd 1 DB p DevAuthInfo` 里 **Level=2 才是超管**。

本机实测（联通 V3.0.5P1N4 / 重庆区域码）：

| 位置 | Level | 账号 |
|---|---|---|
| **Row 1** | 2（超管） | `CUAdmin` |
| **Row 0** | 1（普通） | `user` |

交叉验证：设备管理 → 用户管理（网页）里，`Username0=user` / `Username1=CUAdmin`，
`UserRight0=right1`（普通）/ `UserRight1=right2`（管理维护）——两处完全一致。

> `User`/`Pass` 在 `p` 输出里恒为 `******`，**读不出原密码，只能覆写**。
> web 登录 3 次失败会锁定约 60 秒，别连点。

---

# 常见坑（实战踩过的）

1. **只刷 kernel 不刷 uboot → 永远回落移动**。uboot 与内核必须同版本配套，见 Step 5 说明。
2. **rootfs 不是独立分区**：`mtd12/mtd13 (rootfs1/2)` 是 kernel 分区 `+0x540000` 偏移的**切片视图**，
   `cat /proc/cmdline` 的 `root=/dev/mtdblock12/13` 指向的就是它。HavingFun 重打包 bin 的
   `[0x540000, 0x2AA0000)` 区间是高熵压缩数据（由官方升级程序展开成 rootfs），**直接 kwrite 整段进去
   不含可挂载的 jffs2**——这就是为什么本流程只写 `[0x0, 0x2AA0000)` 的 kernel 段而 rootfs 交给
   联通固件首次启动自建。（实测"联通 kernel 头 + 移动 rootfs 切片"的混合镜像也起不来，别折腾。）
3. **本固件 sendcmd 固化 telnet 无效**：重启后 23 端口依旧关闭。ZTElnet26 可以随时开，但
   **`factorymode/nE%jA@5b` 只在硬复位后的默认配置下有效**——一旦 `sdefconf`/ITMS 下发改写过
   DevAuthInfo，工厂登录会稳定返回 `http code err 401`（实机复现：MAC 填对也 401），
   工具 `-h` 里那句 “To enable the default password, please push reset button for 15 seconds”
   说的就是这个前提。别把 401 当网络问题反复重试。
4. **web 升级入口被阉割**：移动 V3.0.6 与联通 V3.0.5P1N4 的设备管理菜单里都没有"版本升级"项
   （菜单数据结构里直接缺失，不是隐藏参数能唤出的）。`cu.html?hidden=upgrade` 是更新版本联通固件
   才有的入口。要补刷 osgi 等其他分区，走本流程的 telnet + nand kwrite。
5. **`-mac` 参数填电脑网卡 MAC**（无冒号十六进制），论坛教程里的是发帖人自己的，照抄必失败。
   工具日志会打印 `server mac`，那才是光猫的。
6. **防火墙拦 UDP/TCP 入站**：网卡网络类别改"专用"，或手动放行 python.exe（公用 profile 下有 Block 规则）。
7. **100M 网速**：光猫 LAN 口与电脑网卡都支持千兆且 auto，协商出 100M = **网线只有 4 芯通**
   （老旧 Cat5 或水晶头接触不良），换 Cat5e/Cat6 即恢复千兆。管理页"网络侧信息"里 LAN 口协商速率可查。
8. **telnet 长时间写入后掉线**：nand kwrite 完成后 telnetd 可能回收会话（后续命令无回显），
   重新开账号登录即可，写入本身已成功（用 hexdump 验证为准）。
9. **刷后 LAN IP 变化**：只刷 kernel/uboot 时 usercfg 保留、IP 不变；但 `sdefconf`/复位后回到
   `192.168.1.1`。若与家里主网段冲突，登进去改 LAN IP 或调整自己的组网。

# 分区表（G7615AV5 硬件 V2.0，256MB NAND，实测）

```
mtd0: 10000000 "whole flash"     mtd7:  03000000 "kernel1"    ← 备用槽 (region 0)
mtd1: 00300000 "u-boot"          mtd8:  03000000 "kernel2"    ← 出厂运行槽 (region 1)
mtd2: 00200000 "others"          mtd9:  02c00000 "osgi1"
mtd3: 00200000 "parameter tags"  mtd10: 02c00000 "osgi2"
mtd4: 00200000 "wlan"            mtd11: 03100000 "plugin_data"
mtd5: 00800000 "usercfg"         mtd12: 03000000 "rootfs1"    (= mtd7 + 0x540000 切片视图)
mtd6: 00600000 "middle"          mtd13: 02ac0000 "rootfs2"    (= mtd8 + 0x540000 切片视图)
```

> 注意 kernel1(rootfs1) 在前、kernel2(rootfs2) 在后；`fw_flashing` 的 `curpdev` 指当前运行分区。

# 地区码表（联通式编码，`cat /etc/init.d/regioncode`）

```
0   默认(联通通用)   300 江苏    301 新疆    302 海南    303 天津
304 安徽            305 上海    306 重庆    307 北京    308 四川
309 山东            310 广东    311 湖北    312 福建    313 苏州
314 浙江            315 山西    316 湖南    317 云南    318 西藏
319 黑龙江          320 贵州    321 山西2   322 河北    323 宁夏
324 广西            325 江西    326 甘肃    327 青海    328 西安
329 辽宁            330 吉林    331 内蒙古  332 河南    334 集采
```

# 参考链接

- [ZTE Telnet 小助手 V3.1.5.a（HavingFun）](https://www.right.com.cn/forum/thread-8476080-1-1.html) — telnet 开启/固化 GUI 工具与 ZTElnet26 发布帖
- [刷成联通/电信的 G7615AV5 重新刷成移动版（HavingFun）](https://www.right.com.cn/forum/thread-8472017-1-1.html) — 联通 V3.0.5P1N4 完整包与 nand 刷写命令来源
- [广东移动中兴 F7005MV3/G7615AV5 Telnet 命令整理（danch744）](https://www.right.com.cn/forum/thread-8461114-1-1.html) — sendcmd 命令集/账户行号/地区码
- [F7015TV3 无 USB 口光猫 telnet 备份刷写思路（xiafeifei）](https://www.right.com.cn/forum/thread-8411517-1-1.html) — tftp 备份与 kwrite 思路
- [starofys/zte-telnet](https://github.com/starofys/zte-telnet) — go_build_zte_go 工具源码（webFac 握手协议实现）

# 致谢

感谢恩山社区 HavingFun、danch744、xiafeifei 等先行者与 starofys 的协议实现；
本仓库只是在他们的肩膀上，把每一步实机跑通并把坑位标注清楚。

---

如果这个仓库帮到了你，欢迎 star / 提 issue 补充你机器上的实测差异（分区布局、地区码行为、行号语义等）。

> AI生成