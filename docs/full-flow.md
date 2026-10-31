# 从刷机到可用：G7615AV5 跨网完整实操流程

> 本文是 [README](../README.md) 的**操作手册版**：README 讲"为什么"和"踩过什么坑"，
> 本文讲"照着点，依次做"，把刷机 → 复位 → 找回密码 → 手动建 WAN → IPv6 → IPTV → WiFi
> → 上行方式 → 验收串成一条可复现的路径。
>
> 所有数值均为 **2026-10-31 实机验证**（联通 V3.0.5P1T1 / 重庆 306 / 硬件 V2.0）。
> 你的机器如果分区布局、地区码、行号语义不同，以 `cat /proc/mtd` 和 `sendcmd 1 DB p` 的实际输出为准。

---

## 流程总览

```
① 备份分区 ─→ ② 拆固件 ─→ ③ 传固件 ─→ ④ 刷 kernel+uboot ─→ ⑤ 验证 ─→ ⑥ 切分区重启
                                                              │
                                    ┌─────────────────────────┘
                                    ↓
⑦ 切地区码 306 ─→ ⑧ 物理复位 ─→ ⑨ 【黄金10分钟】开 telnet、固化账户、关 TR-069
                                    │
                                    ↓
⑩ 手动建/改 4 条 WAN（VID / 桥接 / 端口绑定）
                                    │
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              ⑪ IPv6 全开    ⑫ IPTV 4口     ⑬ WiFi 口令
                    └───────────────┼───────────────┘
                                    ↓
                    ⑭ 插回光纤 → 注册 → ⑮ 验收清单
```

**铁律三条**（违反会掉坑）：

1. **当前运行分区从头到尾不碰**，刷另一个分区，新固件起不来会自动回落。
2. **nand kerase / kwrite 期间绝不断电**（3~8 分钟）。
3. **顺序是"先断管理通道，再入网"**——先关 ACS，再插光纤，否则配置全被覆盖。

---

## 阶段一 · 刷机（离线操作，一次性）

### Step 1 · 确认设备状态

```
telnet: cat /proc/mtd                  # 分区表，必须先核对
        cat /proc/csp/versionstates    # 当前运行分区 current=0/1
        fw_flashing                    # curpdev=/dev/mtd7 或 mtd8 = 当前运行分区
        upgradetest getver             # Main/Spare 版本
```

> **刷写目标 = 非运行分区**。运行 mtd8 就刷 mtd7，反之亦然。
> 每台机器分区布局可能不同，**不要照抄分区号**。

### Step 2 · 开启 telnet（二选一）

**方案 A · ZTElnet26（推荐）**——固件无关，复位后仍有效：

```
ZTElnet26-windows-amd64.exe -i 192.168.1.1 -m <电脑MAC无冒号> -p 80 -u factorymode -pw "nE%jA@5b"
```

输出临时账号密码（每次随机）。`factorymode / nE%jA@5b` 是硬复位后工厂模式默认凭据。

**方案 B · go_build_zte_go**——需要当前有效的 web 超密：

```
go_build_zte_go.exe -addr http://192.168.1.1:80 -mac <电脑MAC> -username CMCCAdmin -password aDm8H%MdA
```

> 移动超密 `CMCCAdmin / aDm8H%MdA`；联通 `CUAdmin / CUAdmin`；电信 `telecomadmin / nE7jA%5m`。
> `-mac` 填**你自己电脑网卡**的 MAC，不是光猫的。

拿到账号后用本仓库工具执行命令：

```
python tools\telnet_session.py 192.168.1.1 <临时用户> <临时密码> "upgradetest getver"
```

### Step 3 · 备份分区（必做，救砖保险）

```
python tools\tftp_server.py backup
```

telnet 侧逐个推送（假设电脑 IP 192.168.1.100）：

```
tftp -p -l /dev/mtd1 192.168.1.100    # uboot        3MB
tftp -p -l /dev/mtd2 192.168.1.100    # others       2MB
tftp -p -l /dev/mtd3 192.168.1.100    # paramtag     2MB  ★每机唯一（光校准）
tftp -p -l /dev/mtd4 192.168.1.100    # wlan         2MB  ★每机唯一（Wi-Fi 校准）
tftp -p -l /dev/mtd5 192.168.1.100    # usercfg      8MB  ★含账户库/SN
tftp -p -l /dev/mtd6 192.168.1.100    # middle       6MB
```

> **paramtag / wlan / usercfg 是每台机器独有的，别人的备份不能替代你的。**
> busybox tftp 受 16 位块号限制单文件最大 32MB，大分区（kernel/osgi）用 `dd` 分段传。

### Step 4 · 拆解固件包

```
python tools\extract_firmware.py D:\ZXHN_G7615AV5_UNI_V3.0.5P1N4.bin firmware
```

得到 `kernel_p1n4.bin`（44.7MB）与 `uboot_unicom.bin`（1.8MB），MD5 对得上就用仓库现成镜像。

### Step 5 · 上传固件到光猫并校验

```
python tools\http_file_server.py firmware 8001
```

```
wget -O /upgtempfile/kernel.bin http://192.168.1.100:8001/kernel_p1n4.bin
wget -O /upgtempfile/uboot.bin  http://192.168.1.100:8001/uboot_unicom.bin
md5sum /upgtempfile/kernel.bin    # 必须与电脑端一致!
md5sum /upgtempfile/uboot.bin
```

> `/upgtempfile` 是 100MB tmpfs，重启即清空；中途重启过要重新 wget。

### Step 6 · 刷写（严禁断电）

假设当前运行 mtd8，目标 mtd7：

```
echo 2 > /proc/zteinfo/factory/factorymode      # 开启工厂模式
touch /userconfig/nanddebug                     # 解除 nand 写保护

nand kerase /dev/mtd7 0x0 0x3000000             # 擦除整分区 48MB
nand kwrite /dev/mtd7 0x0 0x2aa0000 /upgtempfile/kernel.bin

nand kerase /dev/mtd1 0x0 0x1c0000              # ★ uboot，必须刷
nand kwrite /dev/mtd1 0x0 0x1c0000 /upgtempfile/uboot.bin
```

批量执行（给长命令加等待秒数，`@@N`）：

```
python tools\telnet_session.py 192.168.1.1 <user> <pass> ^
  "echo 2 > /proc/zteinfo/factory/factorymode@@3" ^
  "touch /userconfig/nanddebug@@3" ^
  "nand kerase /dev/mtd7 0x0 0x3000000@@240" ^
  "nand kwrite /dev/mtd7 0x0 0x2aa0000 /upgtempfile/kernel.bin@@480" ^
  "nand kerase /dev/mtd1 0x0 0x1c0000@@60" ^
  "nand kwrite /dev/mtd1 0x0 0x1c0000 /upgtempfile/uboot.bin@@90"
```

> **只刷 kernel 不刷 uboot → 永远回落移动**。移动 V3.0.6 的 uboot 与联通 V3.0.5 内核不配套
> （uboot 环境变量写死了配套内核的引导参数，如 rootfs 偏移）。设备不会砖，但也永远不会起来。

### Step 7 · 验证刷写结果

```
hexdump -C -n 16 /dev/mtd7                # 99 99 99 99 44 44 44 44 55 55 55 55 aa aa aa aa
hexdump -C -s 0x192 -n 6 /dev/mtd7        # 56 33 2e 30 2e 35  → "V3.0.5"
hexdump -C -s 0xf0800 -n 32 /dev/mtd1     # REV魔数 + "V3.0.5P1N2"
upgradetest getver                        # Spare version num: V3.0.5P1N4
```

### Step 8 · 切换启动分区并重启

```
upgradetest switchver 0    # 0/1 对应备用/当前，切到刚刷好的一侧
reboot
```

2~4 分钟后以联通固件启动，登录页变为"管理员账户/其他账户"双账户样式，
登录后跳转 `unicom.html`。**若又回到移动界面 = 引导失败回落**（回去检查 uboot）。

---

## 阶段二 · 复位与账户固化（关键前置）

### Step 9 · 切地区码

```
upgradetest sdefconf 306    # 306=重庆（联通式编码表见 README）
reboot
```

`sdefconf` 会删除配置文件，重启后按新地区码重建，**此时超密会被地区模板改写为未知值**。

> 怕折腾就切 `sdefconf 0`（联通默认地区），超密保持 `CUAdmin/CUAdmin` 可预期。

### Step 10 · 物理复位（彻底清干净）

通电状态下顶住 reset 小孔 10~15 秒，指示灯全亮即成。

### Step 11 · 黄金 10 分钟（顺序不能错，**光纤必须还没插**）

```
① 拔光纤 → 顶 reset ≥60s（等 4 个网口灯同时闪/灭）→ 松手
② 立刻用 ZTElnet26 开 telnet（干净库下 factorymode 必过）——★ 别先试 CUAdmin
③ 用 telnet 覆写 DevAuthInfo（按 Level 定位，不认行号），顺手关 TR-069
④ 手动建 WAN（internet / iptv 两条，见阶段三）
⑤ 最后才插回光纤 → register.gch 填 LOID → 观察 Status 变 0 / Result 变 1
```

> **★ 实机修正：硬复位不会把 web 超密还原成 `CUAdmin/CUAdmin`。**
> 联通 V3.0.5P1N4 + 地区 306 的默认库里超密是**按机随机**的。
> 实测序列：复位后 `CUAdmin` 登录 → `Lognumber=1` 失败；同一时刻 `ZTElnet26` 直接开出临时账号。
> **先开 telnet，再用 telnet 改 web 密码**，顺序反了会白等 60 秒锁定期。

**③ 固化两个账户**（先 `p` 确认 Level，别信行号）：

```
sendcmd 1 DB p DevAuthInfo
```

**Level 的数值含义不要背，现场判定。** 2026-11-01 在本机（联通 V3.0.5P1N4 / 地区 306）实测：
`Level=1` 那行（`cqadmin`）才是**管理维护账号**，`Level=2` 那行（`user`）是普通账号——
与早前记录的"Row1=Level2=超管"**相反**。判定方法：登录页「管理员账户」入口提交 `Right=1`，
用哪一行的密码能进且能看到「高级配置」，那一行就是超管。

所以推荐直接用脚本（按 Level 改，附 dry-run 可先看要改哪行）：

```
python tools/solidify.py 192.168.1.1 <telnet用户> <telnet密码> ^
  --admin <超管名>:<超密> --user <普通名>:<普通密码> --tr069-off --reboot
```

手写的话（把 `<LV>` 换成你实测出来的超管 Level）：

```
sendcmd 1 DB set DevAuthInfo <LV> User <你的超管名>
sendcmd 1 DB set DevAuthInfo <LV> Pass <你的超密>
sendcmd 1 DB set DevAuthInfo <LV'> User <你的普通名>
sendcmd 1 DB set DevAuthInfo <LV'> Pass <你的普通密码>
# 关掉 ACS，防止插光纤后再次被下发覆盖
sendcmd 1 DB set MgtServer 0 URL ""
sendcmd 1 DB set MgtServer 0 PeriodicInformEnable 0
# 更彻底：连 TR069 那条 WAN 一起停掉，防止 DHCP option 43 把 ACS 地址塞回来
sendcmd 1 DB set WANC 0 Enable 0
sendcmd 1 DB set WANC 1 Enable 0
sendcmd 1 DB save
```

> ⚠️ 注意上面最后的 `DB save` 会用内存库重写 `db_user_cfg.xml`——如果你**之前用 solidify.py 改过文件**，
> 先确认内存里的 TelnetCfg 已经是新值（固件脚本末尾会做一次内存重载），否则会把 telnet 固化抹掉。
> 顺序建议：**先 solidify.py（文件级）→ 再 `DB set` 改零散字段 → 最后 `DB save`**。

> 顺序的关键：**先断管理通道，再入网**。只要 ACS 还通，插回光纤后的首次上线依旧会把
> DevAuthInfo / SSID / WAN 全部重写一遍，前面所有手工配置等于白做。
> 仅清空 URL 不够——联通侧常用 DHCP option 43 做 ACS 发现，URL 会被重新填回。

> `User`/`Pass` 在 `p` 输出里恒为 `******`，**读不出原密码，只能覆写**。
> web 登录 3 次失败会锁定约 60 秒，别连点。

---

## 阶段三 · 网页手动配置（核心，全部走厂商 UI）

前置：起一个带调试端口的 Edge，用脚本接管：

```
"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="<仓库>/.temp/edgeprof" --no-first-run ^
  --no-default-browser-check http://192.168.1.1/

python tools/zte_ui.py status        # 看 ONU 注册状态 + WAN 连接
python tools/zte_snapshot.py docs/config-snapshot-2026-10-31.md
```

> 光猫**只允许一个活动会话**，新开标签页会把旧会话挤掉，全程复用一个 page 对象。

### Step 12 · 上行线路配置：四条 WAN 的目标参数

页面路径：**基本配置 → 上行线路配置**。

> ⚠️ **第一件事：下拉框默认停在"新建WAN连接"，那个表单的 VLAN ID 本来就是空的。**
> 核对任何连接都必须**先在下拉框选中它**，表单才会回填真实值。

| 连接 | 封装类型 | 连接模式 | 业务类型 | IP协议版本 | VLAN 模式 | VLAN ID | 802.1p | 端口绑定 | NAT |
|---|---|---|---|---|---|---|---|---|---|
| `1_TR069_R_VID_3600` | IPoE | 路由 | TR069 | IPv4 | 改写(tag) | 3600 | 0 | PON 侧由 VLAN 绑定管 | 关 |
| `2_INTERNET_R_VID_48` | PPPoE | 路由 | INTERNET | **IPv4/v6** | 改写(tag) | **48** | 0 | LAN1 / LAN2 / LAN3 | 是（全对称型） |
| `3_IPTV_B_VID_3185` | IPoE | **桥接** | IPTV | IPv4 | 改写(tag) | **3185** | 0 | **仅 LAN4** | — |

**INTERNET（PPPoE）逐项填写**：

| 项 | 值 | 说明 |
|---|---|---|
| 使能 | 是 | |
| 封装类型 | PPPoE | 业务侧下发，灰的 |
| 连接模式 | 路由 | |
| 业务类型 | INTERNET | 灰的 |
| IP 协议版本 | **IPv4/v6** | ← IPv6 靠这个，见 Step 14 |
| 用户名 | `clan2301317426` | 业务侧填好；**密码 DB 里是 `******` 读不出，要自己补** |
| 密码 | 你自己的 | |
| MTU | 1480 | |
| VLAN 模式 | **改写(tag)** | 不选这个，VLAN ID 字段是灰的，填了也白填 |
| VLAN ID | **48** | ← 这就是 VID |
| 802.1p | 0 | |
| 启用 NAT | 是 / 全对称型 | |
| 端口绑定 | **LAN1 ✓ LAN2 ✓ LAN3 ✓ + SSID1(2.4G) ✓ + SSID5(5G) ✓**，LAN4 ✗ | checkbox `Frm_PortETH1~3` / `Frm_PortWLAN1,5` |
| 拨号模式 | 自动连接 | |

**IPTV 逐项填写**：

| 项 | 值 | 说明 |
|---|---|---|
| 封装类型 | IPoE | 灰的 |
| 连接模式 | **桥接** | 机顶盒自己 DHCP，**不能是路由** |
| 业务类型 | IPTV | 灰的 |
| VLAN 模式 | 改写(tag) | |
| VLAN ID | **3185** | |
| DHCP 服务使能 | 否 | 桥接模式不拨 DHCP |
| 端口绑定 | **仅 LAN4 ✓**（`Frm_PortETH4`） | 见 Step 15 |

> ⚠️ **注意 INTERNET 绑了 SSID1 和 SSID5**——即 **2.4G 和 5G 无线用户走这条 PPPoE 上网**。
> 这不是"Wi-Fi 绑定"的新机制，而是端口绑定表里把无线 SSID 也当作一个接入端口来用。
> 如果你把 SSID5 也勾给 IPTV，**无线用户就上不了网了**（一条 WAN 不能同时被两个业务独占同一组口）。
> 改绑时务必记住：`Frm_PortWLAN5` = **SSID5 = 5G**，不是 WLAN2（2.4G 的第二个 SSID）。

**下发动作**（关键，别忘）：

```
填完 → 点「修改」下发 → 连接名自动变成 2_INTERNET_R_VID_48 → 点「连接」
```

> 网页校验逻辑：`if ("2" == getValue("Frm_WBDMode")) { Check_IntegerRange(vlan,1,4094,"Frm_VLANID",...) }`
> —— 只有 VLAN 模式 = 改写(tag)（value=2）时才校验并接受 VLAN ID。

**结果判定**：

```
状态 → 网络侧信息 → IPv4 WAN连接信息
  模式 PPPoE / 连接名称 2_INTERNET_R_VID_48 / IP 27.14.x.x / 网关 27.14.x.1
  连接状态 连接 / 在线时长 xxx 秒
```

> 「最近一次失败原因」可能仍残留 `连接ISP服务器超时`——那是历史字段，
> **以「连接状态=连接」和 IP 是否拿到为准**。

### Step 13 · LAN 配置：DHCPv4 + 静态 DNS

页面路径：**基本配置 → LAN配置 → DHCPv4配置**。

| 项 | 值 | 说明 |
|---|---|---|
| IP 地址 | 192.168.1.1 | |
| 子网掩码 | 255.255.255.0 | |
| **DNS 来源** | **静态配置** | ← 不改这里，客户端会拿到联通的劫持 DNS |
| 接口 | 2_INTERNET_R_VID_48 | |
| **首选 DNS** | **114.114.114.114** | |
| **备选 DNS** | **8.8.8.8** | |
| 启动 DHCP 服务 | 是 | |
| 租期 | 7200 秒 | |
| 起始 / 结束 IP | 192.168.1.2 / .254 | |

> **联通下发的 DNS（`221.5.203.98` / `221.7.92.98`）在 UDP 上会把任意域名解析成 `192.168.1.1`**，
> TCP 查询却正常。伪解析器特征：`aa=1`（权威位）、`TTL=0`、随机不存在的域名也返回 192.168.1.1。
>
> 实测可用 / 不可用（UDP）：
>
> | 可用 | 不可用（返回 192.168.1.1） |
> |---|---|
> | `114.114.114.114`、`8.8.8.8`、`2400:3200::1`、`2606:4700:4700::1111` | 联通 `221.5.203.98`/`221.7.92.98`、`119.29.29.29`、`223.5.5.5`、`180.76.76.76` |
>
> 排查手法：直接用 Python 发 DNS 报文对比 UDP/TCP，比在浏览器里 nslookup 直观得多。

### Step 14 · IPv6 全开（三处缺一不可）

| # | 位置 | 项 | 值 |
|---|---|---|---|
| ① | 上行线路配置 → 选中 INTERNET 连接 | IP 协议版本 | **IPv4/v6**（`Frm_protocol`=3） |
| ② | LAN配置 → RA配置 | 使能 | **是**（最小等待 200 / 最大等待 600，M=否 / **O=是**） |
| ③ | LAN配置 → DHCPv6配置 | 启动 DHCP 服务 | **是**（网关 `fe80::1/64`，DNS 刷新 86400s，LAN 侧 DNS 方式 HGWProxy） |

**前缀来源与委派**（无需手填，运营商下发）：

- 「状态 → 网络侧信息 → IPv6 WAN连接信息」应看到：
  `PPP = 2_INTERNET_R_VID_48`，`GUA获取方式 = SLAAC`，
  `前缀获取方式 = DHCPv6`，`获取前缀 = 2408:8262:7e59:5045::/64`，`连接状态 = 连接`
- 「基本配置 → 前缀管理」应看到委派记录：
  `前缀 2408:8262:7e59:5045::/64，来源 PrefixDelegation，有效期 3600/3600，下发方式 RA/DHCPv6`

> RA 的 **O 标志**设成"是"，客户端才能拿到除 DNS 外的其他 IPv6 选项。

**验证**：客户端 ping `2400:3200::1`（阿里 IPv6 DNS）通 → IPv6 通路正常。

> ⚠️ **IPv6 的 DNS 不要指望在光猫改**：RA 由运营商控制，发下来的 DNS 改不动。
> 要绕开就在**客户端**手动配 `2400:3200::1` / `2606:4700:4700::1111`。

### Step 15 · IPTV：4 口怎么配

**当前实况**：ITMS 下发的 `3_IPTV_B_VID_3185` 是**桥接 + IPoE + VLAN 3185**，
**端口绑定只有 LAN4 = 是**（LAN1/2/3 = 否）。即**机顶盒只能插 LAN4**。

页面路径：**基本配置 → 绑定设置**。

当前绑定表：

| 端口 | 绑定模式 | VLAN 绑定 |
|---|---|---|
| LAN1 / LAN2 / LAN3 / LAN4 | 端口绑定 | （空） |
| PON | VLAN绑定 | `4001/3185,3600/3600` |
| SSID1~SSID7 | 端口绑定 | （空） |
| SSID8 | VLAN绑定 | `4001/3185,3600/3600` |

**要让 4 个口都能接 IPTV**：

```
绑定设置 → 绑定模式 选「VLAN绑定」（Frm_Mode=1，当前是 0=端口绑定）
  → LAN1 / LAN2 / LAN3 / LAN4  的 VLAN绑定 输入框（Frm_VLAN0a~3a）都填 3185
  → PON 侧保持 4001/3185,3600/3600
  → 确定
```

**两种绑定模式的区别**（这是最容易搞混的地方）：

| | 端口绑定 | VLAN 绑定 |
|---|---|---|
| 语义 | 某条 WAN 只走指定物理口 | 按 VLAN 标记载体，**一个口可同时跑多业务** |
| 现状 | INTERNET 占 LAN1/2/3，IPTV 占 LAN4 | PON 侧 `4001/3185,3600/3600` |
| 4 口同时上网+看 IPTV | ❌ 做不到（物理独占） | ✅ 做到，LAN 口 VLAN 列表写 `48,3185,3600` |

> **只把 IPTV 端口绑到 LAN4 而不动 VLAN 绑定，机顶盒插 LAN1 是收不到 IPTV 流的。**
> 用 VLAN 绑定时，WAN 侧对应连接必须是**桥接**模式（当前 IPTV 已经是桥接，OK）。

### Step 16 · WiFi 口令

页面路径：**基本配置 → WLAN配置 → 无线基本配置(2.4G / 5G)**。

| 项 | id | 2.4G | 5G |
|---|---|---|---|
| SSID 名称 | `Frm_ESSID` | `G7615_2G` | `G7615_5G` |
| 认证方式 | `Frm_Authentication` | WPA/WPA2-PSK | WPA/WPA2-PSK |
| **WPA 预共享密钥（生效口令）** | `Frm_KeyPassphrase` | **`g7615av5`** | **`g7615av5`** |
| WPA 加密算法 | `Frm_WPAEncryptType` | AES | AES |
| 密钥长度 | `Frm_WEPEncryptionLevel` | 64bit | 64bit |
| 当前密钥 | `Frm_WEPKeyIndex` | 1 | 1 |
| 密钥1~4 | `Frm_WEPKey0~3` | 11111/22222/33333/44444 | 同左 |
| 双频合一 | `Frm_SSIDCombine` | 否 | 否 |
| 访客网络 | — | 关 | 关 |

> ⚠️ **「密钥1~4」是 WEP 密钥槽，不是生效口令**（对应 `WEPKey0~3`，DB 里存 base64 密文）。
> 认证方式为 WPA/WPA2-PSK 时它们完全不参与认证。**改密码只改 `Frm_KeyPassphrase`。**
>
> 双频合一 = 否 ⇒ 2.4G 和 5G 是**两个独立口令**（当前恰好相同）。
> 若在 2.4G 勾了双频合一，页面会弹窗问是否同步改 5G。

### Step 17 · 上行方式：GPON 还是 XGPON

页面路径：**设备管理 → 上行方式**。

`Frm_LANMode` 可选值：

| value | 选项 | 说明 |
|---|---|---|
| 1 | 1G/XG 自适应 | **当前值**。与局端自动协商 |
| 2 | GPON | 强制 2.5G GPON |
| 4 | XGPON | 强制 10G XGPON |
| 49~52 | 网口1~网口4 | 电口回传（配合 GPON 上行做网口备份） |

**当前状态**：状态页「设备信息」显示 **上行方式 = GPON**，
「远程管理状态」显示 **GPON状态 = 认证成功**，
上行接口信息实测光功率：输入 **-15.6 dBm**（参考 -27~-8）、输出 **2.3 dBm**（参考 0.5~5）——**光路正常**。

**结论：现在是 GPON 在跑，且是"自适应协商成 GPON"，不是被限制成 GPON。**

**能不能切 XGPON？**

XGPON 是**物理层标准**，局端必须发 XGPON 光谱，光猫单方面切过去会掉线：

| 情况 | 切 XGPON 的结果 |
|---|---|
| 联通给你开的是 GPON（绝大多数家庭宽带） | ❌ PON 断开 → 光猫失联 → 只能物理复位 |
| 联通给你开的是 XGPON（千兆+ 新套餐 / 政企） | ✅ 可切，网口协商到 10G |
| 保持 1G/XG 自适应 | ✅ **最优**，跟局端走 |

**真要切**（页面提示"业务重启生效"）：

```
设备管理 → 上行方式 → 模式选择 选 XGPON → 确定 → 设备重启
```

回退：同样路径把 `Frm_LANMode` 改回 `1`（自适应）再重启。

> ⚠️ **除非联通明确给你的线路是 XGPON，否则不要动这个下拉框。**
> 刷完联通固件后本机默认就是 `1`（自适应），这是最安全的状态。

### Step 18 · 插回光纤并注册

```
⑤ 最后才插回光纤
→ 高级配置 → LOID配置 → 填 LOID（联通给的宽带识别码，最长 24 位）+ 密码 → 点「认证注册」
→ 状态 → 逻辑ID注册信息：注册状态 / 配置结果 从"初始状态"变为正常
→ 状态 → 设备信息：ONU注册状态 = 运行状态(o5)，区域码 = 重庆
→ 状态 → 远程管理状态：GPON状态 = 认证成功
```

> 注册成功后 ITMS 会下发业务模板，若下发的 INTERNET 连接又是 `2_INTERNET_R_VID_`（VID 为空），
> 回到 Step 12 手动补 VLAN 48。

---

## 阶段四 · 验收清单

逐条打勾，全绿才算跑通：

| # | 检查项 | 位置 | 期望值 |
|---|---|---|---|
| 1 | 软件版本 | 状态 → 设备信息 | V3.0.5P1T1 / 联通固件 |
| 2 | 区域码 | 状态 → 设备信息 | 重庆，配置正常 |
| 3 | ONU 注册 | 状态 → 设备信息 | 运行状态(o5) |
| 4 | 光功率 | 状态 → 上行接口信息 | 输入 -15~ -27 dBm，输出 0.5~5 dBm |
| 5 | PON | 状态 → 远程管理状态 | GPON状态 = 认证成功 |
| 6 | IPv4 上网 | 状态 → IPv4 WAN连接信息 | 2_INTERNET_R_VID_48，连接状态 = 连接，IP 非 0 |
| 7 | PPPoE 参数 | 上行线路配置 → 选 INTERNET | VLAN 模式 = 改写(tag)，VLAN ID = 48，IP协议 = IPv4/v6 |
| 8 | IPv6 前缀 | 状态 → IPv6 WAN连接信息 | 获取前缀 2408:...::/64，连接状态 = 连接 |
| 9 | RA | LAN配置 → RA配置 | 使能 = 是，O = 是 |
| 10 | DHCPv6 | LAN配置 → DHCPv6配置 | 启动 DHCP 服务 = 是 |
| 11 | IPTV | 上行线路配置 → 选 IPTV | 桥接，VLAN 3185，端口绑定 LAN4 = 是 |
| 12 | 4 口绑定 | 基本配置 → 绑定设置 | LAN1~4 的 VLAN绑定含 3185（若要 4 口都通） |
| 13 | 静态 DNS | LAN配置 → DHCPv4配置 | 首选 114.114.114.114 / 备选 8.8.8.8，DNS来源 = 静态配置 |
| 14 | WiFi | WLAN配置 | SSID G7615_2G / G7615_5G，PSK = g7615av5 |
| 15 | 上行方式 | 设备管理 → 上行方式 | 1G/XG 自适应（不要动） |
| 16 | TR-069 | 状态 → 远程管理状态 | Inform 上报状态 = 未上报（无 ACS 配置参数） |

**客户端侧再验一遍**：

```
ping 114.114.114.114          # IPv4 通
nslookup www.baidu.com        # 返回真实 IP，不是 192.168.1.1
ping -6 2400:3200::1          # IPv6 通
nslookup -type=AAAA www.baidu.com
```

---

## 常见故障速查

| 现象 | 根因 | 处理 |
|---|---|---|
| PPPoE 一直"连接ISP服务器超时" | ITMS 下发的连接 VID 为空 | Step 12：VLAN 模式改写(tag) + VLAN ID 48 + 点「修改」下发 |
| 网页上找不到 VLAN ID 填哪 | 下拉框停在"新建WAN连接" | 先选中具体连接再看表单 |
| 填了 VLAN ID 不生效 | VLAN 模式不是"改写(tag)" | 网页只在 value=2 时校验并接受 VLAN ID |
| 域名解析成 192.168.1.1 | 联通 UDP DNS 被伪解析器劫持 | DHCPv4配置 → DNS来源改静态配置 → 114.114.114.114 / 8.8.8.8 |
| 客户端拿不到 IPv6 地址 | WAN 侧 IP协议版本 = IPv4 | Step 14 ①：改成 IPv4/v6 |
| IPv6 有前缀但客户端不通 | RA 或 DHCPv6 没开 | Step 14 ②③ |
| 机顶盒插 LAN1 收不到 IPTV | IPTV 只绑了 LAN4 | Step 15：绑定设置切 VLAN绑定，4 个口都填 3185 |
| 切 XGPON 后光猫失联 | 局端是 GPON | 物理复位，回到自适应（`Frm_LANMode=1`） |
| 复位后 CUAdmin 登不上 | 默认库超密按机随机 | 用 ZTElnet26 开 telnet，再改密码 |
| telnet 401 | 已下发配置，factorymode 失效 | 只能物理复位回默认库 |
| 刷完还是移动界面 | uboot 没刷 / 没切分区 | Step 6 + Step 8 |
| 插光纤后配置被重置 | ACS 还在线 | 先关 TR-069（Step 11 ③）再插光纤 |

---

## 工具速查

| 脚本 | 用途 |
|---|---|
| `tools/telnet_session.py` | telnet 自动化会话（批量命令/抓输出） |
| `tools/unicom_login.py` | 联通版 web 登录器（sha256+动态 token，自带失败限速） |
| `tools/tftp_server.py` | TFTP 分区备份服务器 |
| `tools/http_file_server.py` | HTTP 固件下发服务器（无 32MB 限制） |
| `tools/extract_firmware.py` | 联通固件包拆解（切 kernel / uboot） |
| `tools/cdp.py` | 零依赖 CDP 客户端（断网环境可用） |
| `tools/zte_ui.py` | 网页操作助手（Playwright 接管 Edge） |
| `tools/zte_snapshot.py` | 全量配置快照抓取 |
| `tools/recover_after_reset.py` | 复位后自助恢复 |
| `tools/probe_live.py` | 逐条 WAN / 绑定 / RA / 上行方式 逐项取证（本流程配套） |
| `tools/probe_live2.py` | LAN 二级菜单 + WLAN 双频 + IPTV 详情取证 |
| `tools/probe_live3.py` | 原始字段值取证（select 的真实 value、id 映射） |
| `tools/probe_html.py` | 关键页面原始 HTML dump（分析 JS 联动逻辑） |

> `zte_ui.py` / `zte_snapshot.py` / `probe_*.py` 需要 `pip install playwright`
> （**只装 Python 包**，直接用系统已装的 Edge/Chrome，不需要 `playwright install` 下载内核）。
> `probe_*.py` 用 `p.chromium.launch(channel="msedge")` **直接起浏览器**，
> 不需要事先开 `--remote-debugging-port`，比 `connect_over_cdp` 省事。
>
> 探针脚本默认用 `CUAdmin` 登录；你的密码不同就设环境变量：
>
> ```bash
> ZTE_ADMIN_PASS='你的密码' python tools/probe_live.py .temp/probe1.txt
> ```

---

## 关键 id 对照表（网页自动化用）

| 页面 | 含义 | id |
|---|---|---|
| 上行线路配置 | 连接下拉框 | 第一个 `select`（值 `IGD.WD1.WCD1.WCIP1` / `WCD3.WCPPP1` / `WCD4.WCIP1`） |
| | VLAN 模式 | `Frm_WBDMode`（0=untag, 1=transparent, **2=tag**） |
| | VLAN ID | `Frm_VLANID` |
| | 802.1p | — |
| | 用户名 / 密码 | `Frm_UserName` / `Frm_UserPassword` |
| | IP 协议版本 | `Frm_protocol`（1=IPv4, 2=IPv6, **3=IPv4/v6**） |
| | 封装类型 | `WanAddress_select`（PPP=PPPoE, IP=IPoE） |
| | 连接模式 | `WanConnectMode_select`（Route=路由, BRIDGE=桥接） |
| | 业务类型 | `Frm_ServList`（1=INTERNET, 2=TR069, **8=IPTV**） |
| 上行线路配置 | 端口绑定 LAN1~4 / PON | `Frm_PortETH1` ~ `Frm_PortETH5`（ETH5=PON） |
| | 端口绑定 SSID1~8 | `Frm_PortWLAN1` ~ `Frm_PortWLAN8`（**WLAN5=SSID5=5G**，不是 WLAN2） |
| 绑定设置 | 绑定模式 | `Frm_Mode`（0=端口绑定, 1=VLAN绑定） |
| | LAN1~4 VLAN绑定 | `Frm_VLAN0a` ~ `Frm_VLAN3a` |
| 上行方式 | 模式选择 | `Frm_LANMode`（1=自适应, 2=GPON, 4=XGPON, 49~52=网口1~4） |
| WLAN | SSID 名称 | `Frm_ESSID` |
| | **WPA 预共享密钥** | `Frm_KeyPassphrase` |
| | WEP 密钥槽 | `Frm_WEPKey0` ~ `Frm_WEPKey3`（不生效） |
| | 认证方式 | `Frm_Authentication` |
| RA 配置 | 使能 | `Frm_Enable` |
| 前缀管理 | RA / DHCPv6 下发 | `Frm_RA` / `Frm_DHCPV6` / `Frm_Onlink` / `Frm_AutoConf` |

---

*本文所有实测数据来自 2026-10-31 对一台真实 G7615AV5（联通 V3.0.5P1T1 / 重庆 306 / 硬件 V2.0）的抓取，
可用 `tools/probe_live*.py` 复现。机器不同请以实际输出为准。*
