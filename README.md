# ZXHN G7615AV5 跨运营商刷机工具包（移动 → 联通）

中兴 ZXHN G7615AV5（10G GPON，硬件 V2.0）**移动版刷联通固件**的完整实战记录与配套工具。
全部命令与偏移量均为实机验证（2026-10 刷机，2026-11 复验），非转载拼凑。

---

## 从哪开始

| 你的情况 | 看这篇 |
|---|---|
| **第一次刷，想照着做一遍** | **[docs/enshan-tutorial.md](docs/enshan-tutorial.md)** ← 主线教程，从移动版一路做到能上网 |
| 已经刷完，只知道要"固化"但不知道顺序 | [docs/post-flash-runbook.md](docs/post-flash-runbook.md) — 刷机后 shell Runbook |
| 想查网页每个字段怎么填（四条 WAN / IPv6 / 端口绑定 / id 对照） | [docs/full-flow.md](docs/full-flow.md) — 网页配置细节手册 |
| 想把上网和 IPTV 塞进一根网线 | [docs/iptv-single-line.md](docs/iptv-single-line.md) — 单线复用 |
| 想搞懂 telnet 固化为什么这么做 | [docs/telnet-solidify.md](docs/telnet-solidify.md) — 加密算法与三个陷阱 |
| 要写脚本操作网页 / 查字段 id | [docs/web-ui-structure.md](docs/web-ui-structure.md) — 菜单树与字段对照 |
| 配置乱了想回滚 | [附录 · 备份与回滚](#备份与回滚) |

> 本文（README）是**索引 + 附录**：主流程只给一页速查，具体操作看教程；
> 所有踩坑、分区表、地区码统一放在文末**附录**，不打断阅读。

---

## 最终成果

| 项目 | 刷机前 | 刷机后 |
|---|---|---|
| 运营商固件 | 移动 V3.0.6P2T3 | **联通 V3.0.5P1N4** |
| 管理界面 | 移动版 | 联通版 `unicom.html` |
| 超级管理员 | CMCCAdmin / aDm8H%MdA | 自定义（脚本按 `Level` 改，见附录 B） |
| 地区码 | 410（广东，移动式编码） | **306（重庆，联通式编码）** |
| telnet | 工厂工具临时开启 | **固化常开**：`root/12345`，重启自启（两次复验） |
| 备用分区 | 移动 V3.0.6P3N4 | 保留（天然"后悔药"，可 `switchver` 切回） |
| IPTV | 只能插运营商指定那一个口 | **单线复用**：LAN1 做 Trunk，一根线跑上网(48)+IPTV(3185) |
| 配置备份 | 网页无导出功能 | `backup_restore.py` 一键备份/回滚，含明文 XML 与密钥 |

## ⚠️ 免责与三条红线

- 刷机有变砖风险，后果自负；仅供个人设备学习折腾。
- **红线 1：刷 uboot（mtd1）是全流程唯一可能真砖的步骤**，失败需拆机 TTL 救砖。
- **红线 2：`nand kerase/kwrite` 期间绝对不能断电**（约 3~8 分钟）。
- **红线 3：分区号必须先用 `cat /proc/mtd` 核对**，每台机器布局可能不同，不要照抄。

---

## 全流程一览

主线共 12 步，详细命令、截图位置与失败处理见 [docs/enshan-tutorial.md](docs/enshan-tutorial.md)。

| 步 | 做什么 | 一句话要点 |
|---|---|---|
| 1 | 确认分区与运行槽 | `fw_flashing` 看 `curpdev`，**刷非运行分区** |
| 2 | 开 telnet（工厂模式） | `ZTElnet26 -m <电脑MAC> -u factorymode -pw nE%jA@5b` |
| 3 | **备份分区** | mtd1/3/4/5 是命，`tftp -p` 推给电脑 |
| 4 | 拆联通固件包 | `extract_firmware.py` 得 kernel + uboot |
| 5 | 上传并校验 MD5 | `wget` 到 `/upgtempfile`，MD5 必须一致 |
| 6 | 刷 kernel + **刷 uboot** | ★ 漏了 uboot 就永远回落移动 |
| 7 | 切槽重启 | `upgradetest switchver 0` + `reboot` |
| 8 | 切地区码 → **拔光纤物理复位** | `sdefconf 306`，reset 顶 10~15s 到灯全亮 |
| 9 | telnet 使能 | 复位后 `factorymode` 必过，先开壳别赌 web 超密 |
| 10 | **固化 + 改超密 + 关 TR069** | `solidify.py --admin a:b --tr069-off --reboot` |
| 11 | 网页配业务 | WAN/PPPoE、IPv6、DNS、WiFi（**不碰 shell 写库**） |
| 12 | 插光纤注册 + 备份 | LOID 注册 → `Status=0/Result=1` → `backup_restore.py` |

**"黄金 10 分钟"**：第 8 步复位后到第 11 步之前，设备是干净默认库，固化必须在这个窗口内完成；
插了光纤再固化就是和 ITMS 抢时间。

---

## 仓库内容

```
├── docs/
│   ├── enshan-tutorial.md     # ★ 主线教程：刷机 → 复位 → telnet → 固化 → 改密 → 配业务 → 验收
│   ├── post-flash-runbook.md  # ★ 刷机后 shell Runbook（固化顺序 / 验收 / 防覆盖 / 备份回滚）
│   ├── iptv-single-line.md    # ★ IPTV 单线复用（VLAN 绑定原理 / 位掩码 / 抓包验证 / 排查）
│   ├── telnet-solidify.md     # ★ Telnet 固化逆向（加密算法 / 三个致命陷阱）
│   ├── full-flow.md           # 网页配置细节手册（四条 WAN / IPv6 / 端口绑定 / 关键 id 对照）
│   ├── web-ui-structure.md    # Web 界面结构（菜单树 / 字段 id / 标签页）
│   └── config-snapshot-*.md   # 全量配置快照（只读留档）
├── tools/                     # 纯 Python，零第三方依赖
│   ├── 【刷机与固件】extract_firmware.py  tftp_server.py  http_file_server.py
│   ├── 【telnet 与配置库】telnet_session.py  tel_exec.py  zte_cfg.py
│   │                      pull_file.py  push_cfg.py  push_cfg2.py
│   │                      solidify.py  backup_restore.py  restore_base.py
│   │                      inject_pppoe.py  recover_after_reset.py  factory_reset.py
│   ├── 【网页自动化与取证】unicom_login.py  cdp.py  zte_ui.py  zte_snapshot.py
│   │                      snapshot_now.py  zte_dump_*.py  probe_live*.py  probe_html.py
│   └── fill_ztetelnet.py      # 从 ZTE Telnet 小助手窗口读出随机临时账号
├── firmware/                  # kernel_p1n4.bin / uboot_unicom.bin + MD5SUMS.txt
├── backups/                   # 一台真实设备的分区备份样本（仅研究分区结构，不可跨机刷入）
└── third_party/               # ZTElnet26（HavingFun）、go_build_zte_go（starofys）
```

**几个关键工具**

| 工具 | 作用 |
|---|---|
| `tools/solidify.py` | ★ 一键固化：telnet 常开 + 改 web 账号（按 Level）+ 关 TR069 + 回写两文件 |
| `tools/backup_restore.py` | ★ 配置备份 / 校验 / 回滚（含明文 XML 与 paramtag） |
| `tools/zte_cfg.py` | `db_user_cfg.xml` ver4 加解密（Python 复刻 zxcfg，含 NUL 参与 MD5 的坑） |
| `tools/extract_firmware.py` | 联通固件包拆解，切出 kernel / uboot |
| `tools/restore_base.py` | 以原厂完整备份为基底注入业务行（绕开 WAN 索引不重建的坑） |

> `zte_ui.py` / `zte_snapshot.py` / `probe_*.py` 需要 `pip install playwright`（**只装 Python 包**，
> 直接用系统已装的 Edge/Chrome，不用 `playwright install` 下载内核）。
> 断网环境可改用 `tools/cdp.py`（零标准库外零依赖）。

### 第三方工具归属

| 文件 | 作者 | 来源 | 许可 |
|---|---|---|---|
| `go_build_zte_go.exe` | starofys | [github.com/starofys/zte-telnet](https://github.com/starofys/zte-telnet) | 随上游仓库 |
| `ZTElnet26-windows-amd64.exe` | HavingFun | [恩山论坛](https://www.right.com.cn/forum/thread-8476080-1-1.html) | 闭源，仅供学习交流，请勿商用倒卖 |

两者均原样收录（MD5 见 `third_party/MD5SUMS.txt`），版权归原作者。

### 设备备份样本说明（backups/）

一台真实设备的原厂备份，仅供研究分区内部结构（paramtag 标签布局、usercfg 加密头等）。
**不能跨机刷入**：paramtag/wlan 含每机独有的光功率与射频校准，usercfg 绑定 SN。

---

## 环境准备（Windows）

1. **Python 3**（工具脚本零第三方依赖）。
2. 网线直连光猫 LAN 口，与光猫同网段（默认 `192.168.1.1`）。
3. **把这块网卡的网络类别改成「专用」**。公用 profile 下防火墙会拦 UDP 69（TFTP）与 8001 端口（HTTP 下发），
   现象是光猫侧 `tftp: timeout` 而服务器毫无日志。
4. 记下电脑有线网卡 MAC（开 telnet 的 `-m` 参数用，**是电脑的，不是光猫的**）。

### 备份与回滚

```bat
python tools\backup_restore.py 192.168.1.1 root 12345 backup
python tools\backup_restore.py 192.168.1.1 root 12345 verify backups\<日期>\db_user_cfg.xml
python tools\backup_restore.py 192.168.1.1 root 12345 restore backups\<日期>\db_user_cfg.xml --reboot
```

回滚是**字节级覆盖**，等于回到备份那一刻；脚本会先把现场配置存到 `/tmp/rollback_<时间戳>.xml`。

---

# 附录

## 附录 A · 七个真正卡住人的坑

> A~C 是刷完固件必踩的，D~G 是手动配业务时的四个高频误解。

### 坑 A · 业务下发的 INTERNET WAN 没有 VID

LOID 注册成功后，ITMS 会下发业务模板，本例生成：

```
1_TR069_R_VID_3600   DHCP，VLAN 3600   ← ACS 通道
2_INTERNET_R_VID_    PPPoE，VLAN 缺失  ← 连接名里 VID 是空的！
```

`2_INTERNET_R_VID_` 的 **VID 后缀为空 = VLAN ID 没写进去**（对照 TR069 那条的 `VID_3600`）。
症状是 PPPoE 一直"连接ISP服务器超时"、IP 全 `0.0.0.0`。

**VID 到底填在哪**：很多人打开"上行线路配置"发现 VLAN ID 是空的，就以为这固件没地方填 VID。
真相是**页面默认停在"新建WAN连接"，那个表单本来就是空值**。正确路径：

```
基本配置 → 上行线路配置
  ① 下拉框（默认"新建WAN连接"）→ 选中 2_INTERNET_R_VID_
  ② "VLAN 模式" → 选 改写(tag)          ← 不选这个，VLAN ID 字段是灰的
  ③ "VLAN ID" → 填你当地的（本例 48）
  ④ "802.1p" → 0
  ⑤ 用户名/密码 → 业务侧给的用户名 + 自己的密码
  ⑥ 点「修改」下发 → 连接名变成 2_INTERNET_R_VID_48 → 点「连接」
```

网页校验逻辑在 `wan_conf.html`：
`if ("2" == getValue("Frm_WBDMode")) { Check_IntegerRange(vlan,1,4094,"Frm_VLANID",...) }`
—— **只有 VLAN 模式 = 改写(tag)（value=2）时才校验并接受 VLAN ID**。

> ⚠️ **别用"新建WAN连接"表单核对配置**——它的默认值（untag / VLAN 空 / IPv4 / MTU 1480）
> 和任何真实连接都不一样，用它做对照会得出错误结论。核对一律用下拉框选中具体连接。

本机真实参数（联通 V3.0.5P1T1 / 重庆 306）：

| 连接 | 封装 | 模式 | 业务 | VLAN 模式 | VLAN ID | 端口绑定 |
|---|---|---|---|---|---|---|
| `1_TR069_R_VID_3600` | IPoE | 路由 | TR069 | 改写(tag) | 3600 | PON 侧由 VLAN 绑定表管 |
| `2_INTERNET_R_VID_48` | PPPoE | 路由 | INTERNET | 改写(tag) | 48 | LAN1/2/3 + SSID1 + SSID5 |
| `3_IPTV_B_VID_3185` | IPoE | **桥接** | IPTV | 改写(tag) | 3185 | 仅 LAN4 |

### 坑 B · 运营商 UDP DNS 被伪解析器劫持

联通下发的 DNS（`221.5.203.98` / `221.7.92.98`）在 **UDP** 上会把**任意域名**解析成 `192.168.1.1`（光猫自己），
TCP 查询却返回真实结果。伪解析器特征：`aa=1`（权威位）、`TTL=0`、随机不存在的域名也返回 `192.168.1.1`。

| 可用（UDP） | 不可用（返回 192.168.1.1） |
|---|---|
| `114.114.114.114`、`8.8.8.8`、`2400:3200::1`、`2606:4700:4700::1111` | 联通 `221.5.203.98`/`221.7.92.98`、`119.29.29.29`、`223.5.5.5`、`180.76.76.76` |

处理：基本配置 → LAN配置 → DHCPv4配置 → **DNS来源 = 静态配置**，首选 `114.114.114.114`、备选 `8.8.8.8`。
IPv6 的 RA DNS 由运营商下发、光猫改不动，客户端侧覆盖。

### 坑 C · 网页没有配置导出

设备管理 → 设备管理 →「USB备份配置」需要 U 盘；「强制推送配置」是推给 ACS 的开关。
本固件网页**无法导出配置文件**。替代方案：

1. `tools/zte_snapshot.py` 抓全量配置快照（Markdown），作为可复现留档；
2. 真要二进制备份就走 telnet + `tools/backup_restore.py`——但**业务下发之后 `factorymode/nE%jA@5b` 会稳定 401**，
   它只在"硬复位后的默认配置"下有效。

### 坑 D · IPv6 不开就是"半双栈"

三处必须同时到位，缺一处就表现为"有地址但上不了网"或"客户端拿不到地址"：

| 位置 | 字段 | 实测值 |
|---|---|---|
| 上行线路配置 | IP 协议版本（`Frm_protocol`，value=3） | `IPv4/v6` |
| LAN配置 → RA配置 | 使能 | 是（M=否 / O=**是**） |
| LAN配置 → DHCPv6配置 | 启动 DHCP 服务 | 是（LAN DNS 获取方式 = HGWProxy） |

前缀来自 **DHCPv6-PD** 委派：状态 → 网络侧信息 → IPv6 WAN连接信息 里能看
`获取前缀 2408:8262:xxxx::/64`，来源 `PrefixDelegation`，下发方式 RA/DHCPv6。
验证：客户端 ping 通 `2400:3200::1`。

### 坑 E · IPTV 是桥接 + 只绑 LAN4

ITMS 下发的 `3_IPTV_B_VID_3185` 是 **桥接 + IPoE + VLAN 3185**，端口绑定只有 LAN4。
也就是说机顶盒**只能插 LAN4**（不另配 VLAN 绑定的前提下）。

> ⚠️ 注意 INTERNET 那条同时绑了 **SSID1(2.4G) 和 SSID5(5G)**——无线用户走的就是这条 PPPoE。
> 别把 SSID5 勾给 IPTV，否则无线用户直接断网。`Frm_PortWLAN5` = SSID5 = 5G，不是 WLAN2。

**「端口绑定」和「VLAN 绑定」是两套机制**：

| | 端口绑定（PortBinding） | VLAN 绑定（VlanPortMask） |
|---|---|---|
| 本质 | 让某端口使用某个 WAN，标签由光猫**剥掉** | 让某端口变成 Trunk，标签**原样透传** |
| 同一口能否多 WAN | 页面互斥，只能选一个 | 可以，多个 WAN 在同一 bit 上置位 |
| 适合 | 机顶盒直连光猫 | **单线复用** |

让上网和 IPTV 走同一根线的正确写法（2026-11-01 实测）：**VLAN 绑定里每个端口一个输入框，
一行一条 `用户VLAN/运营商VLAN`**，例如 LAN1 填两行 `48/48`、`3185/3185`。
不需要"WAN 侧必须桥接"这个前提——上网保持路由模式也能和桥接 IPTV 共存。

完整步骤、位掩码换算、抓包验证、四层排查见 **[docs/iptv-single-line.md](docs/iptv-single-line.md)**。

### 坑 F · WiFi 的"密钥1~4"是 WEP 槽位，不是生效口令

| 字段 | id | 值 |
|---|---|---|
| SSID 名称 | `Frm_ESSID` | 2.4G `G7615_2G` / 5G `G7615_5G` |
| 认证方式 | `Frm_Authentication` | `WPA/WPA2-PSK` |
| **WPA 预共享密钥（生效口令）** | `Frm_KeyPassphrase` | ← **改密码只改这一栏** |
| WPA 加密算法 | `Frm_WPAEncryptType` | `AES` |
| 密钥1~4 | `Frm_WEPKey0~3` | `11111`/`22222`/... ← **WEP 密钥槽，WPA 模式下不生效** |

界面上那四个"密钥1~4"是 WEP 的轮换密钥槽（DB 里存 base64 密文），认证方式为 WPA/WPA2-PSK 时
完全不参与认证，改它们不会改变连接密码。2.4G/5G 是**两个独立口令**（`Frm_SSIDCombine`=否 时）。

### 坑 G · GPON / XGPON：设备支持 ≠ 运营商给你 XGPON

「设备管理 → 上行方式」页 `Frm_LANMode`：

| value | 选项 | 说明 |
|---|---|---|
| 1 | 1G/XG 自适应 | **默认，最优解**，跟局端走 |
| 2 | GPON | 强制 2.5G |
| 4 | XGPON | 强制 10G |
| 49~52 | 网口1~4 | 电口回传 |

XGPON 是**物理层标准**，局端（OLT）必须发 XGPON 光谱。**局端还是 GPON 而你切成 XGPON = 光模块收不到信号 → PON 失联**，
只能物理复位。除非联通明确给你开了 XGPON，否则不要动这个下拉框。

判断当前：状态 → 网络侧信息 → 上行接口信息，`GPON状态 = 认证成功` + 光功率正常（本例 -15.6dBm / 2.3dBm）。
**只要网页能进、PPPoE 能拨号，就是 GPON 在跑。**

> 刷完联通固件后默认就是 `1`（自适应），所以状态页显示"上行方式 GPON"是协商结果，不是被限制。

---

## 附录 B · DevAuthInfo：别信行号，也别信网上的 Level

**唯一可靠的做法是现场判定。** 网上流传两套互相矛盾的说法（"Level=2 是超管"/"Row0 是超管"），
不同固件、不同地区模板都可能不同。

本机实测（联通 V3.0.5P1N4 / 地区 306）与流传说法**相反**：

| Row | User | Level | 实际身份 |
|---|---|---|---|
| 0 | `cqadmin` | **1** | **管理维护账号（超管）** |
| 1 | `user` | 2 | 普通账号 |

验证过程（两步都做过）：

1. 登录页「管理员账户」入口提交 `Right=1`，用 `Level=1` 那行的密码能登进去，且能看到「高级配置 / 设备管理」全套菜单；
   用 `Level=2` 的密码在这个入口失败。
2. 网页「设备管理 → 用户管理」页里，「管理维护账号」栏显示的用户名与 `Level=1` 那行一致
   （`UserRight0=right1`=普通 / `UserRight1=right2`=管理维护 这套对照反过来用过就会踩）。

所以 `tools/solidify.py` 用 `--admin-level`（默认 1）指定哪一级是超管。**改完用「管理员账户」入口试一次**，
能进「高级配置」就对；进不去就加 `--admin-level 2` 重跑。

> `User`/`Pass` 在 `sendcmd p` 输出里恒为 `******`，**读不出原密码，只能覆写**。
> 但明文 XML 里是明文，`solidify.py --dry-run` 会把原值打出来。
> web 登录 3 次失败锁定约 60 秒，别连点。

**一个反直觉的现象**：硬复位**不会**把 web 超密还原成 `CUAdmin/CUAdmin`——部分地区模板下默认库超密是按机随机的。
复位后第一个能进的门是 telnet（factorymode），不是 web。**先开 telnet，再用 shell 改超密**，顺序反了会白等。

## 附录 C · 杂项问题速查

1. **只刷 kernel 不刷 uboot → 永远回落移动**。uboot 与内核必须同版本配套。
2. **rootfs 不是独立分区**：`mtd12/mtd13` 是 kernel 分区 `+0x540000` 偏移的**切片视图**，
   `root=/dev/mtdblock12/13` 指的就是它。重打包 bin 的 `[0x540000, 0x2AA0000)` 是高熵压缩数据，
   **直接 kwrite 整段进去不含可挂载的 jffs2**。这就是本流程只写 `[0x0, 0x2AA0000)` 的 kernel 段、
   rootfs 交给固件首次启动自建的原因。（"联通 kernel 头 + 移动 rootfs 切片"的混合镜像也起不来，别折腾。）
3. **`sendcmd 1 DB set TelnetCfg` 无效**：该表运行时只读，`DB set` 被静默丢弃。走配置文件路径，
   且必须同时覆盖 `db_backup_cfg.xml`、改完**不能** `DB save` / `DB rreset`。详见
   [telnet-solidify.md](docs/telnet-solidify.md)。
4. **`factorymode/nE%jA@5b` 只在硬复位后的默认配置下有效**。一旦 `sdefconf`/ITMS 改写过 DevAuthInfo，
   工厂登录稳定 401（MAC 填对也 401）。别把 401 当网络问题反复重试。
5. **web 升级入口被阉割**：移动 V3.0.6 与联通 V3.0.5P1N4 的设备管理菜单里都没有"版本升级"项
   （菜单数据结构里直接缺失，不是隐藏参数能唤出的）。要补刷 osgi 等其他分区，走 telnet + `nand kwrite`。
6. **`-mac` 参数填电脑网卡 MAC**（无冒号），论坛教程里的是发帖人自己的，照抄必失败。
   工具日志会打印 `server mac`，那才是光猫的。
7. **防火墙拦 UDP/TCP 入站**：网卡网络类别改"专用"，或手动放行 python.exe。
8. **100M 网速**：两端都支持千兆且 auto，协商出 100M = **网线只有 4 芯通**，换 Cat5e/Cat6。
9. **telnet 长时间写入后掉线**：`nand kwrite` 完成后 telnetd 可能回收会话（后续命令无回显），
   重开账号登录即可，写入本身已成功（以 `hexdump` 验证为准）。
10. **刷后 LAN IP 变化**：只刷 kernel/uboot 时 usercfg 保留、IP 不变；但 `sdefconf`/复位后回到 `192.168.1.1`。

## 附录 D · 分区表（硬件 V2.0，256MB NAND，实测）

```
mtd0: 10000000 "whole flash"     mtd7:  03000000 "kernel1"    ← 备用槽 (region 0)
mtd1: 00300000 "u-boot"          mtd8:  03000000 "kernel2"    ← 出厂运行槽 (region 1)
mtd2: 00200000 "others"          mtd9:  02c00000 "osgi1"
mtd3: 00200000 "parameter tags"  mtd10: 02c00000 "osgi2"
mtd4: 00200000 "wlan"            mtd11: 03100000 "plugin_data"
mtd5: 00800000 "usercfg"         mtd12: 03000000 "rootfs1"    (= mtd7 + 0x540000 切片视图)
mtd6: 00600000 "middle"          mtd13: 02ac0000 "rootfs2"    (= mtd8 + 0x540000 切片视图)
```

> kernel1(rootfs1) 在前、kernel2(rootfs2) 在后；`fw_flashing` 的 `curpdev` 指当前运行分区。

## 附录 E · 地区码表（联通式编码，`cat /etc/init.d/regioncode`）

```
0   默认(联通通用)   300 江苏    301 新疆    302 海南    303 天津
304 安徽            305 上海    306 重庆    307 北京    308 四川
309 山东            310 广东    311 湖北    312 福建    313 苏州
314 浙江            315 山西    316 湖南    317 云南    318 西藏
319 黑龙江          320 贵州    321 山西2   322 河北    323 宁夏
324 广西            325 江西    326 甘肃    327 青海    328 西安
329 辽宁            330 吉林    331 内蒙古  332 河南    334 集采
```

> 怕折腾就切 `sdefconf 0`（联通默认地区），超密与行为最可预期。

## 附录 F · 参考链接与致谢

- [ZTE Telnet 小助手 V3.1.5.a（HavingFun）](https://www.right.com.cn/forum/thread-8476080-1-1.html) — telnet 开启/固化 GUI 工具与 ZTElnet26 发布帖
- [刷成联通/电信的 G7615AV5 重新刷成移动版（HavingFun）](https://www.right.com.cn/forum/thread-8472017-1-1.html) — 联通 V3.0.5P1N4 完整包与 nand 刷写命令来源
- [广东移动中兴 F7005MV3/G7615AV5 Telnet 命令整理（danch744）](https://www.right.com.cn/forum/thread-8461114-1-1.html) — sendcmd 命令集/地区码
- [F7015TV3 无 USB 口光猫 telnet 备份刷写思路（xiafeifei）](https://www.right.com.cn/forum/thread-8411517-1-1.html) — tftp 备份与 kwrite 思路
- [starofys/zte-telnet](https://github.com/starofys/zte-telnet) — go_build_zte_go 源码（webFac 握手协议实现）

感谢恩山社区 HavingFun、danch744、xiafeifei 等先行者与 starofys 的协议实现。
本仓库只是在他们的肩膀上，把每一步实机跑通并把坑位标注清楚。

---

如果这个仓库帮到了你，欢迎 star / 提 issue 补充你机器上的实测差异（分区布局、地区码行为、Level 语义等）。

> AI生成
