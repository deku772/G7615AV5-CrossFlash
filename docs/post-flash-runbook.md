# 刷机后 Runbook（shell / telnet 视角）

> 本文档回答一个问题：**刷完固件、复位完、光纤还没插的这 10 分钟里，用 shell 要做什么、按什么顺序、怎么验证、怎么防止被运营商覆盖。**
>
> 原理与逆向细节见 [telnet-solidify.md](telnet-solidify.md)；网页侧配置见 [full-flow.md](full-flow.md)。
> 本文只讲**操作顺序和验收标准**，2026-11-01 在实机复验。

---

## 0. 先看清"刷完之后设备是什么状态"

很多人刷完就以为完事了，其实设备此时处于**能用但裸奔**的状态：

| 项目 | 刷机/复位后的状态 | 风险 |
|---|---|---|
| telnet | **关闭**（`Lan_Enable=0`） | 下次想进只能再借工厂工具，且工具可能失效 |
| web 超管 | 固件默认（联通为 `CUAdmin/CUAdmin`） | 运营商一插光纤就可能改掉 |
| TR069 / ACS | **默认开启**（`Tr069Enable=1`） | ★ 插光纤后 ITMS 重新下发业务配置，把你改的全覆盖 |
| 业务 WAN | ITMS 下发的 4 条（含 TR069） | 一旦被重新下发，自定义绑定全丢 |
| LOID 注册 | 复位后回到未注册（`Status=99`） | 页面反复跳注册页 |
| 地区码 | 固件默认，未匹配本地 | WiFi 信道、IPTV VLAN 可能不对 |

**结论：刷机的最后一步不是"刷完"，而是"固化 + 断掉远程下发通道"。**

---

## 1. 黄金 10 分钟（顺序不能错，光纤必须还没插）

> 顺序错了会白忙：先固化再复位 = 被清空；先插光纤再固化 = 已被覆盖。

### Step 1 · 拿到临时 shell

用 `ZTElnet26` / `ZTE Telnet 小助手` 点一次「使能」，它会生成**随机**临时账号并显示在界面上。
读出账号后先确认能登录（脚本见 [telnet-solidify.md §八](telnet-solidify.md#八附临时-telnet-账号怎么拿)）。

```bash
python tools/telnet_session.py 192.168.1.1 <临时用户> <临时密码> "id"
```

### Step 2 · 只读巡检（不改任何东西）

进 shell 后**先看清楚再动手**，这几条都是只读的：

```bash
cat /proc/mtd                      # 分区表，核对 mtd 编号，别照抄别人的
sendcmd 1 DB p TelnetCfg           # 当前 telnet 状态（Lan_Enable 应为 0）
sendcmd 1 DB p DevAuthInfo         # web 账户，记下 Level=2 那一行是超管
sendcmd 1 DB p MgtServer           # TR069 状态和 ACS 地址
cat /etc/init.d/regioncode         # 可用地区码
cat /proc/cpuinfo | grep -i model  # 确认硬件型号
```

> ★ **DevAuthInfo 不要信行号，要信 `Level`。** 不同固件行序不同，本机是 Row0=Level1（普通）、
> Row1=Level2（超管）。认错行改错账户，会出现"改了密码但登不进"。

### Step 3 · 固化（一次性写好三件事）

| 目标 | 表 / 字段 | 值 |
|---|---|---|
| telnet 常开 | `TelnetCfg.Row0.Lan_Enable` | `1` |
| telnet 弱口令 | `TelnetCfg.Row0.TSLan_UPwd` | `12345`（建议换掉） |
| 连接数不卡 | `TelnetCfg.Row0.Max_Con_Num` | `999` |
| 空闲不断线 | `TelnetCfg.Row0.ExitTime` | `999` |
| 权限够用 | `TelnetCfg.Row0.InitSecLvl` | `3` |
| web 超管 | `DevAuthInfo.Row1.User/Pass` | 自定义（Level 必须为 2） |
| **断远程下发** | `MgtServer.Row0.Tr069Enable` | **`0`** |

★ **`TelnetCfg` 是运行时只读表，`sendcmd 1 DB set` 对它静默无效** —— 必须走"改配置文件再推回"的路径。
原因和对照实验见 [telnet-solidify.md §二](telnet-solidify.md#二--为什么-sendcmd-1-db-set-无效readme-坑-3-的真正原因)。

```bash
# 一键固化（改 TelnetCfg + DevAuthInfo + MgtServer，推回两个文件并重启）
python tools/solidify.py 192.168.1.1 <临时用户> <临时密码>
```

手写的话，核心只有一句：**`db_user_cfg.xml` 和 `db_backup_cfg.xml` 必须同时覆盖，否则重启后被备份文件还原。**

### Step 4 · 重启并验证（约 50 秒）

```bash
reboot
```

等 50~60 秒后：

```bash
# 1) telnet 端口应该自己开了
telnet 192.168.1.1 23        # 或 bash: </dev/tcp/192.168.1.1/23

# 2) root/12345 能登录，且字段还在
sendcmd 1 DB p TelnetCfg
#   期望: Lan_Enable=1  Max_Con_Num=999  ExitTime=999  InitSecLvl=3
```

**建议重启两次再确认一次** —— 有些机器第一次是"内存生效"，第二次才真正读盘。

### Step 5 · 立刻备份（此时配置最干净）

```bash
python tools/backup_restore.py 192.168.1.1 root 12345 backup
```

会生成 `backups/<日期>/`：

| 文件 | 用途 |
|---|---|
| `db_user_cfg.xml` | 加密原文件，**唯一的真回滚源**，可字节级推回 |
| `db_user_cfg.xml.dec` | 明文 XML，可读可 diff |
| `paramtag.bin` | 设备密钥（换机/恢复明文时必需） |
| `summary.md` | 关键表摘要 + 恢复命令 |

> ⚠️ 这份备份是**设备专属**的：`paramtag` 里含 INDIVKEY，别跨设备混用。

---

## 2. 固化完成后的验收清单

| 检查项 | 命令 | 期望 |
|---|---|---|
| telnet 自启 | `telnet 192.168.1.1 23` | 能连上，`root/12345` 可登录 |
| 连接数 | `sendcmd 1 DB p TelnetCfg` | `Max_Con_Num=999` |
| 不断线 | 同上 | `ExitTime=999` |
| web 超管 | 浏览器登录 | 能进管理页，不是注册页 |
| TR069 已关 | `sendcmd 1 DB p MgtServer` | `Tr069Enable=0` |
| 两文件一致 | `md5sum /userconfig/cfg/db_user_cfg.xml /userconfig/cfg/db_backup_cfg.xml` | 两个 MD5 相同 |
| 网能上 | 电脑 ping 外网 | 通 |

---

## 3. 防止被运营商"重新下发"覆盖

这是刷机后最容易翻车的地方：**你改得好好的，插上光纤几天后配置自己变回去了。**

### 3.1 切断三条下发通道

| 通道 | 怎么断 | 说明 |
|---|---|---|
| TR069 / ACS | `MgtServer.Tr069Enable=0` | 最主要的一条，ITMS 靠它下发业务配置 |
| TR069 专用 WAN | 删除或禁用 `1_TR069_R_VID_3600` / `2_TR069_B_VID_3600` | 断了 TR069 的承载 |
| DHCP option 43 | 关掉对应 WAN 的 DHCP 选项注入 | 防止 ACS 地址被重新塞回来 |

> 注意：本机实测**复位后 `Tr069Enable` 默认是 `1`**，即使 ACS 地址为空。
> 只要将来 DHCP option 43 把地址送进来，它就会连上去。
> 看到 `Tr069Enable=1` 就当没固化成。

### 3.2 怎么发现"已经被覆盖"

配置被重下发不是无痕的，看这几个信号：

```bash
# 1) 你改过的绑定回来了没有
sendcmd 1 DB p PortBinding          # 突然冒出一堆行 = 被重新下发
sendcmd 1 DB p MultiWancConfProduct # VlanPortMask 被打回默认

# 2) 配置文件时间戳变了没
ls -la /userconfig/cfg/             # db_user_cfg.xml 的时间不是你自己改的时间

# 3) TR069 是否被重新打开
sendcmd 1 DB p MgtServer            # Tr069Enable 又变回 1
```

一旦发现被覆盖，**别急着再改一遍** —— 先断 TR069，否则改完还会被覆盖。正确顺序是：
**关 TR069 → 从备份恢复配置 → 重启 → 验证。**

---

## 4. 备份与回滚

```bash
# 备份（随时可做，不影响业务）
python tools/backup_restore.py 192.168.1.1 root 12345 backup

# 只核对备份内容，不碰设备
python tools/backup_restore.py 192.168.1.1 root 12345 verify backups/2026-11-01/db_user_cfg.xml

# 回滚（先自动把现场配置存到 /tmp/rollback_<时间戳>.xml）
python tools/backup_restore.py 192.168.1.1 root 12345 restore backups/2026-11-01/db_user_cfg.xml --reboot
```

回滚脚本的行为是**字节级覆盖**，不做字段级合并，所以回滚后等于"回到备份那一刻"，中间做的任何改动都会消失。

---

## 5. 哪些事必须走 shell，哪些必须走网页

这条分工搞反了会出玄学问题。

| 操作 | 走哪 | 原因 |
|---|---|---|
| telnet 固化 | **shell 改配置文件** | `TelnetCfg` 是只读表，`DB set` 无效 |
| web 超密 | **shell 改配置文件** | 与上面同一条链路，且要认 `Level` 不认行号 |
| 关 TR069 / ACS | shell（`MgtServer` 可用 `DB set`） | 该表可写，但改完别 `DB save` 覆盖其它改动 |
| 增删 WAN、PPPoE 账号 | **必须网页** | ★ 见下 |
| 端口绑定 / VLAN 绑定 | **必须网页** | 涉及 PortMask 位掩码联动 |
| IPv6、WiFi、地区相关 | **必须网页** | 多表联动 |

> ★ **为什么 WAN 必须走网页**：手工往 XML 里插 WAN 行，字段虽然对，但设备内部的
> **WAN 索引 / 关联体系不会随之重建**。结果是网页上 WAN 模式被判成 PPP、用户名读空，
> 点"确定"报「当前操作无效」，既不能改也不能删。
> 这个坑在 `tools/restore_base.py` 的注释里有完整记录 —— 后来改用"以原厂完整备份为基底，
> 只注入业务行"才绕过去。

---

## 6. 常见故障速查

| 现象 | 大概率原因 | 处理 |
|---|---|---|
| 重启后 telnet 又连不上 | 只覆盖了 `db_user_cfg.xml`，没覆盖 `db_backup_cfg.xml` | 两个文件都推，`sync` 后重启 |
| 改完立刻变回去 | 执行了 `sendcmd 1 DB save` 或 `rreset` | 重推后**只 `reboot`** |
| `DB set TelnetCfg` 没反应 | 该表运行时只读 | 走配置文件路径 |
| 网页登录跳到注册页 | LOID 未注册（`Status=99`） | 见 [full-flow.md](full-flow.md) 注册章节 |
| 改了超密却登不进 | 改错行（信行号没信 `Level`） | 找 `Level=2` 那行 |
| 配置过几天自己变了 | TR069 还开着 | 关 `Tr069Enable`，再恢复备份 |
| 网页点确定报「当前操作无效」 | 手工插过 WAN 行，索引没重建 | 用原厂备份做基底重做 |

---

## 7. 一页速查

```bash
# ── 刷完/复位后，光纤还没插 ──
# 1. 开临时 telnet（ZTElnet26 使能，读出随机账号）
# 2. 只读巡检
cat /proc/mtd ; sendcmd 1 DB p TelnetCfg ; sendcmd 1 DB p DevAuthInfo ; sendcmd 1 DB p MgtServer
# 3. 固化（TelnetCfg + DevAuthInfo + MgtServer.Tr069Enable=0）
python tools/solidify.py 192.168.1.1 <用户> <密码>
# 4. 重启并验证两次
reboot   # 等 50s
sendcmd 1 DB p TelnetCfg    # Lan_Enable=1 / ExitTime=999 / InitSecLvl=3
# 5. 备份
python tools/backup_restore.py 192.168.1.1 root 12345 backup

# ── 之后走网页 ──
# WAN / PPPoE / IPv6 / WiFi / 端口绑定 / VLAN 绑定 全部用厂商 UI

# ── 出问题 ──
python tools/backup_restore.py 192.168.1.1 root 12345 restore backups/<日期>/db_user_cfg.xml --reboot
```
