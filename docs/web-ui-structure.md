# 联通 G7615AV5 Web 管理界面 · 页面结构交接文档

> 本文档由 `tools/zte_dump_structure.py` 自动抓取生成。
> 抓取时间: 2026-10-31 18:24:52

## 1. 整体框架

```
http://192.168.1.1/            单页菜单 (#menu0 ~ #menu6)
  └─ 点击菜单 → enterFrame() → template.gch
       ├─ topFrame    主菜单栏  (#mmStatu / #mmNet / #mmAdv / #mmManager)
       └─ mainFrame   内容区    (getpage.gch?pid=1002&nextpage=<页面>.gch)
```

| 元素 | 作用 | 说明 |
|---|---|---|
| `#Frm_Password` | 登录密码输入框 | 表单真实字段名是 `Password`，`id=UserPW` 只是元素 id |
| `#LoginId` | 登录按钮 | 需先执行 `GetAccessAccount('adm')` 选账户类型 |
| `#Frm_Loginchecktoken` | 动态令牌 | 每次会话不同，提交前必须从当前页重取 |
| `UserRandomNum` | 随机数 | 与密码一起做 `sha256(明文 + 随机数)` |
| `accountType` | `adm` / `oth` | 提交 `Right=1`（adm）/ `Right=2`（oth），服务端按 DevAuthInfo 的 Level 匹配。本机实测 adm↔`Level=1`、oth↔`Level=2`，与部分教程相反，以现场验证为准 |

登录提交字段（已实测有效）：

```
Frm_Logintoken=0
Frm_Loginchecktoken=<当前页 token>
_cu_url=1
Right=1
Username=
UserRandomNum=<8位随机数>
Password=sha256(密码明文 + UserRandomNum)
action=login
accountType=adm|oth
```

## 状态  (`#mmStatu`)

入口页: `/getpage.gch?pid=1002&nextpage=status_dev_info_t.gch`

| 子菜单 | 触发方式 |
|---|---|
| 状态 | `href=` |
| 网络侧信息 | `javascript:OnMenuItemClick("mmStatu","smWanStatu"); openLink_cu("getpage.gch?pid=1002&nextpage=status_ethwan_if_t.gch")` |
| 用户侧信息 | `javascript:OnMenuItemClick("mmStatu","smLanStatu"); openLink_cu("getpage.gch?pid=1002&nextpage=e8_status_wlan_info_t.gch` |
| 统计数据 | `javascript:OnMenuItemClick("mmStatu","smGemStat"); openLink_cu("getpage.gch?pid=1002&nextpage=pon_status_stat_info_t.gch` |
| 远程管理状态 | `javascript:OnMenuItemClick("mmStatu","smRmtMgr"); openLink_cu("getpage.gch?pid=1002&nextpage=cuc_status_itms_info_t.gch"` |
| 语音信息 | `javascript:OnMenuItemClick("mmStatu","smVOIPStatu"); openLink_cu("getpage.gch?pid=1002&nextpage=status_voip_4less_t.gch"` |
| 逻辑ID注册信息 | `javascript:OnMenuItemClick("mmStatu","smRegisterInfo"); openLink_cu("getpage.gch?pid=1002&nextpage=status_registerinfo_t` |
| MESH 拓扑图 | `javascript:OnMenuItemClick("mmStatu","smStaTOPO"); openLink_cu("getpage.gch?pid=1002&nextpage=topo_t.gch")` |
| 插件状态 | `javascript:OnMenuItemClick("mmStatu","smPluginstate"); openLink_cu("getpage.gch?pid=1002&nextpage=status_pluginstate_t.g` |
| 进网许可证 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=network_access_license_info_t.gch')` |

### 状态

> 打开失败或无独立内容页。

### 网络侧信息

URL: `/getpage.gch?pid=1002&nextpage=status_ethwan_if_t.gch`

页内标签: 设备信息、用户侧信息、统计数据、远程管理状态、语音信息、逻辑ID注册信息、MESH 拓扑图、插件状态、IPv6 WAN连接信息、上行接口信息、下行光接口信息、4in6隧道连接信息

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### 用户侧信息

URL: `/getpage.gch?pid=1002&nextpage=e8_status_wlan_info_t.gch`

页内标签: 设备信息、网络侧信息、统计数据、远程管理状态、语音信息、逻辑ID注册信息、MESH 拓扑图、插件状态、LAN接口信息、USB接口信息、终端下挂设备信息、无线诊断信息

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### 统计数据

URL: `/getpage.gch?pid=1002&nextpage=pon_status_stat_info_t.gch`

页内标签: 设备信息、网络侧信息、用户侧信息、远程管理状态、语音信息、逻辑ID注册信息、MESH 拓扑图、插件状态、WAN统计数据、语音统计数据、LAN统计数据、WLAN统计数据

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### 远程管理状态

URL: `/getpage.gch?pid=1002&nextpage=cuc_status_itms_info_t.gch`

页内标签: 设备信息、网络侧信息、用户侧信息、统计数据、语音信息、逻辑ID注册信息、MESH 拓扑图、插件状态

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### 语音信息

URL: `/getpage.gch?pid=1002&nextpage=status_voip_4less_t.gch`

页内标签: 设备信息、网络侧信息、用户侧信息、统计数据、远程管理状态、逻辑ID注册信息、MESH 拓扑图、插件状态、电话号码

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### 逻辑ID注册信息

URL: `/getpage.gch?pid=1002&nextpage=status_registerinfo_t.gch`

页内标签: 设备信息、网络侧信息、用户侧信息、统计数据、远程管理状态、语音信息、MESH 拓扑图、插件状态

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### MESH 拓扑图

URL: `/getpage.gch?pid=1002&nextpage=topo_t.gch`

页内标签: 设备信息、网络侧信息、用户侧信息、统计数据、远程管理状态、语音信息、逻辑ID注册信息、插件状态

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| ZTE:G7615AV5-G-C | `(no-id)` | text |  |  |
| qing-home重命名 | `(no-id)` | text |  |  |
| ZXSLC SR7410-f4:2d:06:65:30:17重命名 | `(no-id)` | text |  |  |
| Unknown重命名 | `(no-id)` | text |  |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### 插件状态

URL: `/getpage.gch?pid=1002&nextpage=status_pluginstate_t.gch`

页内标签: 设备信息、网络侧信息、用户侧信息、统计数据、远程管理状态、语音信息、逻辑ID注册信息、MESH 拓扑图

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### 进网许可证

> 打开失败或无独立内容页。

## 基本配置  (`#mmNet`)

入口页: `/getpage.gch?pid=1002&nextpage=IPv46_net_wan_conf_t.gch`

| 子菜单 | 触发方式 |
|---|---|
| 基本配置 | `href=` |
| LAN配置 | `javascript:OnMenuItemClick("mmNet","smAddMgr"); openLink_cu("getpage.gch?pid=1002&nextpage=net_dhcp_dynamic_t.gch")` |
| WLAN配置 | `javascript:OnMenuItemClick("mmNet","smWLAN"); openLink_cu("getpage.gch?pid=1002&nextpage=net_wlan_basic_t1.gch")` |
| 绑定设置 | `javascript:OnMenuItemClick("mmNet","smBindConf"); openLink_cu("getpage.gch?pid=1002&nextpage=net_vlan_port_binding_t.gch` |
| 前缀管理 | `javascript:OnMenuItemClick("mmNet","smPrefixMgr"); openLink_cu("getpage.gch?pid=1002&nextpage=net_prefix_t.gch")` |
| 远程管理 | `javascript:OnMenuItemClick("mmNet","smTR069"); openLink_cu("getpage.gch?pid=1002&nextpage=net_tr069_basic_t.gch")` |
| 主从网关端口绑定 | `javascript:OnMenuItemClick("mmNet","smVlan"); openLink_cu("getpage.gch?pid=1002&nextpage=net_slave_bindonport_t.gch")` |
| MESH参数配置 | `javascript:OnMenuItemClick("mmNet","smMeshParams"); openLink_cu("getpage.gch?pid=1002&nextpage=mesh_workmode_switch_t.gc` |
| 最大接入用户数 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=pon_net_cltlmt_t.gch')` |
| 下挂从网关数量 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=roomPon_count_cltlmt_t.gch')` |
| 4in6隧道连接设置 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=net_dsliteeth_conf_t.gch')` |
| ARP检测 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=net_arpdetect_t.gch')` |
| DHCP清链 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=net_dhcpcleanlink_t.gch')` |

### 基本配置

> 打开失败或无独立内容页。

### LAN配置

URL: `/getpage.gch?pid=1002&nextpage=net_dhcp_dynamic_t.gch`

页内标签: 上行线路配置、WLAN配置、绑定设置、前缀管理、远程管理、主从网关端口绑定、MESH参数配置、静态分配客户端配置、特殊设备地址配置、端口DHCP服务控制、RA配置、DHCPv6配置、IPv6前缀管理、DHCP Isolation配置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| IP地址 | `Frm_BasicIPAddr` | text | 192.168.1.1 |  |
| 子网掩码 | `Frm_SubnetMask` | text | 255.255.255.0 |  |
| DNS来源 | `LanDNS_select` | select-one | Static | HGWProxy,Static*,WANConnection |
| 接口 | `LanDNS_Interface_select` | select-one | IGD.WD1.WCD3.WCPPP1 | IGD.WD1.WCD3.WCPPP1* |
| 首选DNS | `LanPri_DNS_text` | text | 114.114.114.114 |  |
| 备选DNS | `LanSec_DNS_text` | text | 8.8.8.8 |  |
| 启动DHCP服务 | `Frm_ServerEnable` | checkbox |  |  |
| 启动Option125服务 | `Frm_tEnableOpt125` | checkbox |  |  |
| 租期 | `Frm_LeaseTime` | select-one | 7200 | minute,hour,day,threedays,week,7200* |
| 起始IP地址 | `Frm_MinAddress` | text | 192.168.1.2 |  |
| 结束IP地址 | `Frm_MaxAddress` | text | 192.168.1.254 |  |
| 缺省网关 | `Frm_IPRouters` | text |  |  |
| 88:88:88:88:87:88 | `hostShow0` | text | qing-home |  |
| 36:b5:13:56:78:b2 | `hostShow1` | text | OnePlus-15 |  |
| f4:2d:06:65:30:17 | `hostShow2` | text | ZXSLC SR7410-f4:2d:06:65:30:17 |  |
|  | `Btn_Prev` | button | 上一页 |  |
|  | `Btn_Next` | button | 最后一页 |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### WLAN配置

URL: `/getpage.gch?pid=1002&nextpage=net_wlan_basic_t1.gch`

页内标签: 上行线路配置、LAN配置、绑定设置、前缀管理、远程管理、主从网关端口绑定、MESH参数配置、无线高级配置(2.4G)、无线基本配置(5G)、无线高级配置(5G)、访问控制列表、Wi-Fi兼容配置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| SSID选择 | `Frm_SSID_SET` | select-one | IGD.LD1.WLAN1 | IGD.LD1.WLAN1*,IGD.LD1.WLAN2,IGD.LD1.WLAN3,IGD.LD1.WLAN4 |
| 广播取消 | `Frm_ESSIDHideEnable` | checkbox |  |  |
| SSID使能 | `Frm_Enable` | checkbox |  |  |
| 访客网络开启 | `Frm_GuestEnbale` | checkbox |  |  |
| 访客wifi隔离 | `Frm_VapIsolationEnable` | checkbox |  |  |
| 最大用户数 | `Frm_MaxUserNum` | text | 64 |  |
| 双频合一 | `Frm_SSIDCombine` | checkbox |  |  |
| SSID名称 | `Frm_ESSID` | text | G7615_2G |  |
| 优先级 | `Frm_Priority` | select-one | 0 | 0*,1,2,3,4,5,6,7 |
| 认证方式 | `Frm_Authentication` | select-one | WPA/WPA2-PSK | Open System,Shared Key,Both,WPA-PSK,WPA2-PSK,WPA/WPA2-PSK*,WPA3-PSK,WPA2/WPA3-PSK |
| WEP加密 | `Frm_BeaconType` | select-one |  |  |
| 密钥长度 | `Frm_WEPEncryptionLevel` | select-one | 40-bit | 104-bit,40-bit* |
| 当前密钥 | `Frm_WEPKeyIndex` | select-one | 1 | 1*,2,3,4 |
| 密钥1 | `Frm_WEPKey0` | password | 11111 |  |
| 密钥2 | `Frm_WEPKey1` | password | 22222 |  |
| 密钥3 | `Frm_WEPKey2` | password | 33333 |  |
| 密钥4 | `Frm_WEPKey3` | password | 44444 |  |
| WPA预共享密钥 | `Frm_KeyPassphrase` | password | g7615av5 |  |
| WPA组密钥更新间隔 | `Frm_WPAGroupRekey` | text | 0 |  |
| WPA加密算法 | `Frm_WPAEncryptType` | select-one | AESEncryption | TKIPEncryption,AESEncryption*,TKIPandAESEncryption |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 绑定设置

URL: `/getpage.gch?pid=1002&nextpage=net_vlan_port_binding_t.gch`

页内标签: 上行线路配置、LAN配置、WLAN配置、前缀管理、远程管理、主从网关端口绑定、MESH参数配置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 绑定模式 | `Frm_Mode` | select-one | 0 | 0*,1 |
| 1 | `Frm_VLAN0a` | text |  |  |
| 1 | `Frm_VLAN0b` | text |  |  |
| 2 | `Frm_VLAN1a` | text |  |  |
| 2 | `Frm_VLAN1b` | text |  |  |
| 3 | `Frm_VLAN2a` | text |  |  |
| 3 | `Frm_VLAN2b` | text |  |  |
| 4 | `Frm_VLAN3a` | text |  |  |
| 4 | `Frm_VLAN3b` | text |  |  |
|  | `modify` | button | 修 改 |  |
|  | `back` | button | 取 消 |  |
| LAN1 | `Btn_Modify0` | button |  |  |
| LAN2 | `Btn_Modify1` | button |  |  |
| LAN3 | `Btn_Modify2` | button |  |  |
| LAN4 | `Btn_Modify3` | button |  |  |
| PON | `Btn_Modify4` | button |  |  |
| SSID1 | `Btn_Modify5` | button |  |  |
| SSID2 | `Btn_Modify6` | button |  |  |
| SSID3 | `Btn_Modify7` | button |  |  |
| SSID4 | `Btn_Modify8` | button |  |  |
| SSID5 | `Btn_Modify9` | button |  |  |
| SSID6 | `Btn_Modify10` | button |  |  |
| SSID7 | `Btn_Modify11` | button |  |  |
| SSID8 | `Btn_Modify12` | button |  |  |

### 前缀管理

URL: `/getpage.gch?pid=1002&nextpage=net_prefix_t.gch`

页内标签: 上行线路配置、LAN配置、WLAN配置、绑定设置、远程管理、主从网关端口绑定、MESH参数配置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 前缀 | `Frm_Prefix` | text |  |  |
| 前缀 | `Frm_PrefixLen` | text |  |  |
| 广域网连接 | `Frm_Wan` | text |  |  |
| 前缀来源 | `Frm_Src` | text |  |  |
| 首选时间 | `Frm_PreferLifetime` | text |  |  |
| 有效时间 | `Frm_ValidLifetime` | text |  |  |
| 下发方式 | `Frm_RA` | checkbox |  |  |
| 下发方式 | `Frm_DHCPV6` | checkbox |  |  |
|  | `Btn_Edit` | button | 修 改 |  |
|  | `Btn_Back` | button | 取 消 |  |
|  | `Line_0_PrefixLen_1` | text | 2408:8262:7e59:5045::/64 |  |
|  | `Line_0_WANCName_2` | text | 2_INTERNET_R_VID_48 |  |
|  | `Line_0_Src_3` | text | PrefixDelegation |  |
|  | `Line_0_ValidLifetime_5` | text | 3600/3600 |  |
|  | `Line_0_Delegation_8` | text | RA/DHCPv6 |  |
|  | `modify0` | button |  |  |
|  | `Btn_ReFresh` | button |  刷 新  |  |

### 远程管理

URL: `/getpage.gch?pid=1002&nextpage=net_tr069_basic_t.gch`

页内标签: 上行线路配置、LAN配置、WLAN配置、绑定设置、前缀管理、主从网关端口绑定、MESH参数配置、上传CA证书

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 广域网连接 | `Frm_DefaultWan` | select-one |  | *,IGD.WD1.WCD1.WCIP1 |
| 网络服务器URL | `Frm_URL` | text |  |  |
| 用户名 | `Frm_UserName` | text | cpe |  |
| 密码 | `Frm_UserPassword` | password | ****** |  |
| 连接请求URL | `Frm_ConnectionRequestURL` | text | http://0.0.0.0:58000/iAiNeUfDfTcL |  |
| 连接请求用户名 | `Frm_ConnectionRequestUsername` | text | acs |  |
| 连接请求密码 | `Frm_ConnectionRequestPassword` | password | ****** |  |
| 使能周期上报 | `Frm_PeriodicInformEnable` | checkbox | false |  |
| 防RMS负载过重开关 | `Frm_PeriodicRandomEnable` | checkbox | false |  |
| 周期上报时间 | `Frm_PeriodicInformInterval` | text | 43200 |  |
| 是否使用证书 | `Frm_SupportCertAuth` | checkbox | false |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 主从网关端口绑定

URL: `/getpage.gch?pid=1002&nextpage=net_slave_bindonport_t.gch`

页内标签: 上行线路配置、LAN配置、WLAN配置、绑定设置、前缀管理、远程管理、MESH参数配置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `IGD.LD1.ETH5` | checkbox | IGD.LD1.ETH5 |  |
|  | `IGD.LD1.ETH1` | checkbox | IGD.LD1.ETH1 |  |
|  | `IGD.LD1.ETH2` | checkbox | IGD.LD1.ETH2 |  |
|  | `IGD.LD1.ETH3` | checkbox | IGD.LD1.ETH3 |  |
|  | `IGD.LD1.ETH4` | checkbox | IGD.LD1.ETH4 |  |
|  | `IGD.LD1.WLAN8` | checkbox | IGD.LD1.WLAN8 |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### MESH参数配置

URL: `/getpage.gch?pid=1002&nextpage=mesh_workmode_switch_t.gch`

页内标签: 上行线路配置、LAN配置、WLAN配置、绑定设置、前缀管理、远程管理、主从网关端口绑定、MESH漫游阈值

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| MESH使能 | `Frm_MeshEnable` | checkbox |  |  |
| 工作模式 | `Frm_WorkMode` | select-one | 2 | 1,2* |
| 11r使能 | `Frm_11Enable` | checkbox |  |  |
| 自组网V2 | `Frm_NetWorking` | checkbox |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 最大接入用户数

> 打开失败或无独立内容页。

### 下挂从网关数量

> 打开失败或无独立内容页。

### 4in6隧道连接设置

> 打开失败或无独立内容页。

### ARP检测

> 打开失败或无独立内容页。

### DHCP清链

> 打开失败或无独立内容页。

## 高级配置  (`#mmAdv`)

入口页: `/getpage.gch?pid=1002&nextpage=sec_url_filter_t.gch`

| 子菜单 | 触发方式 |
|---|---|
| 高级配置 | `href=` |
| QoS功能设置 | `javascript:OnMenuItemClick("mmAdv","smQoS"); openLink_cu("getpage.gch?pid=1002&nextpage=net_qos_qostemplate_t.gch")` |
| DDNS设置 | `javascript:OnMenuItemClick("mmAdv","smDDNS"); openLink_cu("getpage.gch?pid=1002&nextpage=app_ddns_conf_t.gch")` |
| IGMP设置 | `javascript:OnMenuItemClick("mmAdv","smIGMP"); openLink_cu("getpage.gch?pid=1002&nextpage=app_igmp_snoop_t.gch")` |
| 路由配置 | `javascript:OnMenuItemClick("mmAdv","smRoutMgr"); openLink_cu("getpage.gch?pid=1002&nextpage=app_rip_t.gch")` |
| 时间管理 | `javascript:OnMenuItemClick("mmAdv","smSNTP"); openLink_cu("getpage.gch?pid=1002&nextpage=net_sntp_conf_t.gch")` |
| NAT设置 | `javascript:OnMenuItemClick("mmAdv","smFwAlg"); openLink_cu("getpage.gch?pid=1002&nextpage=sec_fw_alg_t.gch")` |
| 语音功能设置 | `javascript:OnMenuItemClick("mmAdv","smVoIP"); openLink_cu("getpage.gch?pid=1002&nextpage=app_voip_sippro_t.gch")` |
| LOID配置 | `javascript:OnMenuItemClick("mmAdv","smLOID"); openLink_cu("getpage.gch?pid=1002&nextpage=pon_net_ponloid_t.gch")` |
| MLD设置 | `javascript:OnMenuItemClick("mmAdv","smMLD"); openLink_cu("getpage.gch?pid=1002&nextpage=app_mld_snoop_t.gch")` |
| 日常应用 | `javascript:OnMenuItemClick("mmAdv","smUSBStor"); openLink_cu("getpage.gch?pid=1002&nextpage=app_ftp_client_t.gch")` |
| 设备命名 | `javascript:OnMenuItemClick("mmAdv","smDNSSer"); openLink_cu("getpage.gch?pid=1002&nextpage=app_dev_domain_t.gch")` |
| 防火墙设置 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=sec_firewall_t.gch')` |
| MAC地址过滤设置 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=sec_macfilter_conf_t.gch')` |
| 端口过滤设置 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=sec_portfilter_conf_t.gch')` |
| IPv4控制 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=sec_ipv4_filterout_conf_t.gch')` |
| IPv6控制 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=sec_ipv6_filterout_conf_t.gch')` |
| IPv4流量控制 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=sec_ipv4_spl_conf_t.gch')` |
| IPv6流量控制 | `javascript:openLink_cu('getpage.gch?pid=1002&nextpage=sec_ipv6_spl_conf_t.gch')` |

### 高级配置

> 打开失败或无独立内容页。

### QoS功能设置

URL: `/getpage.gch?pid=1002&nextpage=net_qos_qostemplate_t.gch`

页内标签: 安全设置、DDNS设置、IGMP设置、路由配置、时间管理、NAT设置、语音功能设置、LOID配置、MLD设置、日常应用、设备命名、基本设置、分类设置、分类类型设置、本地应用业务、拥塞管理设置、入口限速设置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `btn_VOICE` | button |  VOICE  |  |
|  | `btn_iptv` | button |  IPTV  |  |
|  | `btn_tr069` | button |  TR069  |  |
|  | `btn_internet` | button |  INTERNET  |  |
|  | `btn_firstPRI` | button | TR069 |  |
|  | `btn_secondPRI` | button | VOICE |  |
|  | `btn_thirdPRI` | button | IPTV |  |
|  | `btn_fourthPRI` | button | INTERNET |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### DDNS设置

URL: `/getpage.gch?pid=1002&nextpage=app_ddns_conf_t.gch`

页内标签: 安全设置、QoS功能设置、IGMP设置、路由配置、时间管理、NAT设置、语音功能设置、LOID配置、MLD设置、日常应用、设备命名

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 使能 | `Frm_Enable` | checkbox |  |  |
| 服务商 | `(no-id)` | text | 中国联通 |  |
| 服务类型 | `Frm_Name` | select-one | phddns | phddns* |
| 服务器 | `Frm_Server` | text | phddns60.oray.net |  |
| 用户名 | `Frm_Username` | text |  |  |
| 密码 | `Frm_Password` | password | ****** |  |
| 广域网连接 | `Frm_Interface` | select-one |  | IGD.WD1.WCD3.WCPPP1 |
| 端口号 | `Frm_ServerPort` | text | 6060 |  |
| 域 | `Frm_DomainName` | text | http://www.oray.com |  |
| 主机名 | `Frm_HostName` | text |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### IGMP设置

URL: `/getpage.gch?pid=1002&nextpage=app_igmp_snoop_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、路由配置、时间管理、NAT设置、语音功能设置、LOID配置、MLD设置、日常应用、设备命名

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 使能IGMP SNOOPING | `Frm_Enable` | checkbox |  |  |
| 转发条目老化时间 | `Frm_GrpTimeout` | text | 360 |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 路由配置

URL: `/getpage.gch?pid=1002&nextpage=app_rip_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、IGMP设置、时间管理、NAT设置、语音功能设置、LOID配置、MLD设置、日常应用、设备命名、静态路由配置、路由表、默认连接设置、全路由表

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 使能RIP | `Frm_RipEnabled` | checkbox | on |  |
| 使能通告 | `Frm_RipSend` | checkbox | on |  |
| 版本 | `Frm_RipProtocol` | select-one | 1 | 0,1*,2 |
| 认证方式 | `Frm_RipAuthType` | select-one | 0 | 0*,2,3 |
| 认证密钥 | `Frm_RipAuthKey` | password | ****** |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 时间管理

URL: `/getpage.gch?pid=1002&nextpage=net_sntp_conf_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、IGMP设置、路由配置、NAT设置、语音功能设置、LOID配置、MLD设置、日常应用、设备命名

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| SNTP使能 | `Frm_Enable` | checkbox |  |  |
| 时区 | `Frm_LocalTimeZoneandName` | select-one | 26 | 0,1,2,3,4,5,33,34,6,35,36,37,7,38,8,39,9,40,10,41,11,42,12,13,43,46,14,44,45,47,48,15,49,50,51,16,52,17,18,53,19,54,20,21,22,55,23,24,25,56,26*,57,27,58,59,28,29,60,61,62,30,63,31,32 |
| 主服务器地址 | `Frm_NtpServer1` | text | clock.fmt.he.net |  |
| 从服务器地址 | `Frm_NtpServer2` | text | clock.nyc.he.net |  |
| 同步间隔 | `Frm_PollTimeInterval` | text | 86400 |  |
| DSCP值 | `Frm_Dscp` | text |  |  |
| 绑定的WAN连接业务类型 | `Frm_NTPServerType` | select-one | 0 | 0*,1,2,3 |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### NAT设置

URL: `/getpage.gch?pid=1002&nextpage=sec_fw_alg_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、IGMP设置、路由配置、时间管理、语音功能设置、LOID配置、MLD设置、日常应用、设备命名、DMZ配置、虚拟主机配置、NAT

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| ALG开关 | `Frm_IsTFTPAlg` | checkbox | on |  |
|  | `Frm_IsSIPAlg` | checkbox | on |  |
|  | `Frm_IsH323Alg` | checkbox | on |  |
|  | `Frm_IsRTSPAlg` | checkbox | on |  |
|  | `Frm_IsPPTPAlg` | checkbox | on |  |
|  | `Frm_IsL2TPAlg` | checkbox | on |  |
|  | `Frm_IsIPSECAlg` | checkbox | on |  |
|  | `Frm_IsFTPAlg` | checkbox | on |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 语音功能设置

URL: `/getpage.gch?pid=1002&nextpage=app_voip_sippro_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、IGMP设置、路由配置、时间管理、NAT设置、LOID配置、MLD设置、日常应用、设备命名、帐号信息、基本通话控制、补充业务配置、号码表、语音QoS、协议注销、媒体设置、高级设置、来电显示、SLIC参数配置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 启用 | `Frm_Enable` | checkbox |  |  |
| 协议选择 | `Frm_ServerType` | select-one | 0 | 1,0* |
| 本机端口 | `Frm_UserAgentPort` | text | 5060 |  |
| 主用注册服务器 | `Frm_RegistrarServer1` | text | 0.0.0.0 |  |
| 主用代理服务器 | `Frm_ProxyServer1` | text | 0.0.0.0 |  |
| 主用外发代理服务器 | `Frm_OutboundProxy1` | text | 0.0.0.0 |  |
| 主用端口 | `Frm_ProxyServerPort1` | text | 5060 |  |
| 备用注册服务器 | `Frm_RegistrarServer2` | text | 0.0.0.0 |  |
| 备用代理服务器 | `Frm_ProxyServer2` | text | 0.0.0.0 |  |
| 备用外发代理服务器 | `Frm_OutboundProxy2` | text | 0.0.0.0 |  |
| 备用端口 | `Frm_ProxyServerPort2` | text | 5060 |  |
| 注册有效期 | `Frm_RegisterExpires` | text | 600 |  |
| 上电注销 | `Frm_DeRegister` | checkbox |  |  |
| 开启链路测试 | `Frm_LinkTest` | select-one | 0 | 0*,1,2 |
| 链路测试间隔 | `Frm_LinkTestInterval` | text | 900 |  |
| 启用#号转义 | `Frm_Escaped` | checkbox |  |  |
| 注册重试间隔 | `Frm_RegisterRetryInterval` | text | 30 |  |
| 启用会话更新 | `Frm_Timer` | checkbox |  |  |
| 会话更新周期 | `Frm_InviteExpires` | text | 30 |  |
| 订阅开关 | `Frm_SubScribeEnable` | select-one | 1 | 0,1*,2 |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### LOID配置

URL: `/getpage.gch?pid=1002&nextpage=pon_net_ponloid_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、IGMP设置、路由配置、时间管理、NAT设置、语音功能设置、MLD设置、日常应用、设备命名

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| LOID配置 | `Frm_PonLoid` | text | 你的 LOID（最长 24 位） |  |
| 密码 | `Frm_LoidPasswd` | password | ****** |  |
|  | `reg` | button | 认证注册 |  |
|  | `save` | button | 保存 |  |

### MLD设置

URL: `/getpage.gch?pid=1002&nextpage=app_mld_snoop_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、IGMP设置、路由配置、时间管理、NAT设置、语音功能设置、LOID配置、日常应用、设备命名

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 使能MLD侦听 | `Frm_Enable` | checkbox |  |  |
| 启用MLD增强 | `Frm_Enable_increase` | checkbox |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 日常应用

URL: `/getpage.gch?pid=1002&nextpage=app_ftp_client_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、IGMP设置、路由配置、时间管理、NAT设置、语音功能设置、LOID配置、MLD设置、设备命名、IPTV、UPnP配置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 服务器地址(域名或IP地址) | `Frm_ServerUrl` | text |  |  |
| 端口号 | `Frm_ServerPort` | text |  |  |
| 匿名登录 | `Frm_HiddenName` | checkbox | on |  |
| 用户名 | `Frm_UserName` | text |  |  |
| 密码 | `Frm_UserPass` | password | ****** |  |
| 文件下载路径 | `Frm_DownloadFilePath` | text |  |  |
| 文件保存路径 | `Frm_SaveAsPath` | text |  |  |
| 延时时间 | `Frm_DelayTime` | text | 0 |  |
|  | `Btn_StartDown` | button | 开始下载 |  |
|  | `Btn_RefreshDown` | button | 刷新下载状态 |  |
|  | `Btn_StopDown` | button | 取消下载 |  |

### 设备命名

URL: `/getpage.gch?pid=1002&nextpage=app_dev_domain_t.gch`

页内标签: 安全设置、QoS功能设置、DDNS设置、IGMP设置、路由配置、时间管理、NAT设置、语音功能设置、LOID配置、MLD设置、日常应用、主机名设置

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 域名 | `Frm_DomainName` | text |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 防火墙设置

> 打开失败或无独立内容页。

### MAC地址过滤设置

> 打开失败或无独立内容页。

### 端口过滤设置

> 打开失败或无独立内容页。

### IPv4控制

> 打开失败或无独立内容页。

### IPv6控制

> 打开失败或无独立内容页。

### IPv4流量控制

> 打开失败或无独立内容页。

### IPv6流量控制

> 打开失败或无独立内容页。

## 设备管理  (`#mmManager`)

入口页: `/getpage.gch?pid=1002&nextpage=manager_aduser_conf_t.gch`

| 子菜单 | 触发方式 |
|---|---|
| 设备管理 | `href=` |
| 设备重启 | `javascript:OnMenuItemClick("mmManager","smDevReboot"); openLink_cu("getpage.gch?pid=1002&nextpage=manager_devReboot_t.gc` |
| 恢复出厂配置 | `javascript:OnMenuItemClick("mmManager","smReturnFactory"); openLink_cu("getpage.gch?pid=1002&nextpage=manager_devReturnF` |
| 系统日志 | `javascript:OnMenuItemClick("mmManager","smLogMgr"); openLink_cu("getpage.gch?pid=1002&nextpage=manager_log_conf_t.gch")` |
| 语音协议切换 | `javascript:OnMenuItemClick("mmManager","smVoIPSwitch"); openLink_cu("getpage.gch?pid=1002&nextpage=manager_voip_switch_t` |
| 协议开关 | `javascript:OnMenuItemClick("mmManager","smprotclSwitch"); openLink_cu("getpage.gch?pid=1002&nextpage=net_optimizing_swit` |
| 网络诊断 | `javascript:OnMenuItemClick("mmManager","smNetDiag"); openLink_cu("getpage.gch?pid=1002&nextpage=manager_dev_ping_t.gch")` |
| 环回检测配置 | `javascript:OnMenuItemClick("mmManager","smBackloop"); openLink_cu("getpage.gch?pid=1002&nextpage=pon_net_backloop_conf_t` |
| 上行方式 | `javascript:OnMenuItemClick("mmManager","smChangePON"); openLink_cu("getpage.gch?pid=1002&nextpage=manager_Change_PonMode` |
| 从网关管理 | `javascript:OnMenuItemClick("mmManager","smSlaveManager"); openLink_cu("getpage.gch?pid=1002&nextpage=slave_wlan_radio_co` |

### 设备管理

> 打开失败或无独立内容页。

### 设备重启

URL: `/getpage.gch?pid=1002&nextpage=manager_devReboot_t.gch`

页内标签: 用户管理、恢复出厂配置、设备管理、系统日志、语音协议切换、协议开关、网络诊断、环回检测配置、上行方式、从网关管理、定时重启

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Submit1` | button | 设备重启 |  |
|  | `Submit2` | button | 恢复出厂配置 |  |
|  | `Submit3` | button | 重启中间件 |  |

### 恢复出厂配置

URL: `/getpage.gch?pid=1002&nextpage=manager_devReturnFactory_t.gch`

页内标签: 用户管理、设备重启、设备管理、系统日志、语音协议切换、协议开关、网络诊断、环回检测配置、上行方式、从网关管理

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
|  | `Submit2` | button | 恢复出厂配置 |  |
|  | `Submit3` | button | 本地恢复出厂配置 |  |
|  | `Submit1` | button | 设备重启 |  |

### 系统日志

URL: `/getpage.gch?pid=1002&nextpage=manager_log_conf_t.gch`

页内标签: 用户管理、设备重启、恢复出厂配置、设备管理、语音协议切换、协议开关、网络诊断、环回检测配置、上行方式、从网关管理、维护、日志采集授权

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 日志使能 | `Frm_LogEnable` | checkbox | on |  |
| 日志级别 | `Frm_LogLevel` | select-one | 3 | 0,1,2,3*,4,5,6,7 |
|  | `Frm_LogText` | textarea |  |  |
|  | `Btn_Refresh` | submit | 刷 新 |  |
|  | `Btn_download` | button | 下载日志 |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 语音协议切换

URL: `/getpage.gch?pid=1002&nextpage=manager_voip_switch_t.gch`

页内标签: 用户管理、设备重启、恢复出厂配置、设备管理、系统日志、协议开关、网络诊断、环回检测配置、上行方式、从网关管理

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 语音协议 | `Frm_ProtocolSet` | select-one | 4 | 1,4* |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 协议开关

URL: `/getpage.gch?pid=1002&nextpage=net_optimizing_switch_t.gch`

页内标签: 用户管理、设备重启、恢复出厂配置、设备管理、系统日志、语音协议切换、网络诊断、环回检测配置、上行方式、从网关管理

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 游戏优化 | `Frm_GameOptiSwitch` | checkbox |  |  |
| iOS直播优化 | `Frm_LiveOptiSwitch` | checkbox |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 网络诊断

URL: `/getpage.gch?pid=1002&nextpage=manager_dev_ping_t.gch`

页内标签: 用户管理、设备重启、恢复出厂配置、设备管理、系统日志、语音协议切换、协议开关、环回检测配置、上行方式、从网关管理、Trace Route测试、ARP信息表、Inform手动上报、业务仿真、本地测速、镜像功能

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| IP地址或主机名 | `Frm_Host` | text |  |  |
| 广域网连接 | `Frm_Interface` | select-one |  | *,IGD.WD1.WCD1.WCIP1,IGD.WD1.WCD3.WCPPP1 |
| Ping包数 | `Frm_NumofRepeat` | text | 4 |  |
| Ping包大小 | `Frm_DataBlockSize` | text | 56 |  |
| 超时时间 | `Frm_Timeout` | text | 2000 |  |
|  | `(no-id)` | textarea |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 环回检测配置

URL: `/getpage.gch?pid=1002&nextpage=pon_net_backloop_conf_t.gch`

页内标签: 用户管理、设备重启、恢复出厂配置、设备管理、系统日志、语音协议切换、协议开关、网络诊断、上行方式、从网关管理

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 环回检测使能 | `Frm_Enable` | checkbox |  |  |
| 目的MAC | `Frm_DMac` | select-one | 0 | 0*,1 |
| 以太网类型 | `Frm_Ethertype` | text | 0x8300 |  |
| 检测报文发送间隔 | `Frm_Sendinterval` | text | 10 |  |
| 端口关闭时间 | `Frm_RenewTime` | text | 300 |  |
| 环回恢复时间 | `Frm_CheckInterval` | text | 15 |  |
| VLAN | `Frm_VidStr` | text | untagged |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 上行方式

URL: `/getpage.gch?pid=1002&nextpage=manager_Change_PonMode_qgw_t.gch`

页内标签: 用户管理、设备重启、恢复出厂配置、设备管理、系统日志、语音协议切换、协议开关、网络诊断、环回检测配置、从网关管理

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 模式选择 | `Frm_LANMode` | select-one | 1 | 1*,2,4,49,50,51,52 |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### 从网关管理

URL: `/getpage.gch?pid=1002&nextpage=slave_wlan_radio_conf_t.gch`

页内标签: 用户管理、设备重启、恢复出厂配置、设备管理、系统日志、语音协议切换、协议开关、网络诊断、环回检测配置、上行方式

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 无线开关(2.4G): | `Frm_RadioStatus_Second` | select-one | 0 | 0*,1 |
| 无线开关(5G): | `Frm_RadioStatus_Fifth` | select-one | 0 | 0*,1 |
|  | `modify` | button | 修 改 |  |
|  | `back` | button | 取 消 |  |


---

## 附录 · 关键配置页字段明细

### A. 宽带设置（`IPv46_net_wan_conf_t.gch`）

URL: `/getpage.gch?pid=1002&nextpage=IPv46_net_wan_conf_t.gch`

WAN 连接下拉（`#Frm_WANCName0`）：

- `-1|新建WAN连接`
- `IGD.WD1.WCD1.WCIP1|1_TR069_R_VID_3600`
- `IGD.WD1.WCD3.WCPPP1|2_INTERNET_R_VID_48`
- `IGD.WD1.WCD4.WCIP1|3_IPTV_B_VID_3185`

#### INTERNET (PPPoE)（`IGD.WD1.WCD3.WCPPP1`）

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 连接名称 | `Frm_WANCName0` | select-one | IGD.WD1.WCD3.WCPPP1 | -1,IGD.WD1.WCD1.WCIP1,IGD.WD1.WCD3.WCPPP1*,IGD.WD1.WCD4.WCIP1 |
| 使能 | `Frm_WANEnable` | checkbox | on |  |
| 封装类型 | `WanAddress_select` | select-one | PPP | PPP*,IP |
| 连接模式 | `WanConnectMode_select` | select-one | Route | Route*,BRIDGE |
| 业务类型 | `Frm_ServList` | select-one | 1 | 1*,2,3,4,5,6,7,8,16,32 |
| IP协议版本 | `Frm_protocol` | select-one | 3 | 1,2,3* |
| 用户名 | `Frm_UserName` | text | clan2301317426 |  |
| 密码 | `Frm_Password` | password | ****** |  |
| 超级密码 | `Frm_Supassword` | password |  |  |
| MTU | `Frm_MTU` | text | 1480 |  |
| VLAN 模式 | `Frm_WBDMode` | select-one | 2 | 0,1,2* |
| VLAN ID | `Frm_VLANID` | text | 48 |  |
| 802.1p | `Frm_Priority` | select-one | 0 | 0*,1,2,3,4,5,6,7 |
| 使能DSCP | `Frm_DSCP0` | checkbox |  |  |
| DSCP | `Frm_DSCP1` | text |  |  |
| 启用NAT | `Frm_IsNAT` | checkbox |  |  |
| NAT选型 | `Frm_NatMode` | select-one | 1 | 1*,2,3 |
| 启用NPTv6 | `Frm_IsNPT` | checkbox |  |  |
| DHCP服务使能 | `Frm_DHCPEnable` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH1` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH2` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH3` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH4` | checkbox |  |  |
|  | `Frm_PortETH5` | checkbox |  |  |
|  | `Frm_PortWLAN1` | checkbox |  |  |
|  | `Frm_PortWLAN2` | checkbox |  |  |
|  | `Frm_PortWLAN3` | checkbox |  |  |
|  | `Frm_PortWLAN4` | checkbox |  |  |
|  | `Frm_PortWLAN5` | checkbox |  |  |
|  | `Frm_PortWLAN6` | checkbox |  |  |
|  | `Frm_PortWLAN7` | checkbox |  |  |
|  | `Frm_PortWLAN8` | checkbox |  |  |
| 配置全路由使能 | `Frm_IpbindEnable` | checkbox | on |  |
| 目的IP转发列表 | `Frm_Ipbind_Area` | textarea |  |  |
| 启用PassThrough功能 | `Frm_PassThrough` | checkbox | on |  |
| 认证类型 | `Frm_AuthType` | select-one | PAP,CHAP,MS-CHAP | PAP,CHAP,MS-CHAP*,PAP,CHAP |
| 拨号模式 | `Frm_ConnTrigger` | select-one | AlwaysOn | AlwaysOn*,OnDemand,Manual |
| 超时时间 | `Frm_IdleTime` | text | 1200 |  |
|  | `Btn_Connect` | button | 连 接 |  |
|  | `Btn_Disconnect` | button | 断 开 |  |
| 用户名 | `Frm_IPoEUserName` | text |  |  |
| 密码 | `Frm_IPoEPassword` | password |  |  |
| 地址获取方式 | `WanIPv4Address_select` | select-one | PPPoE | PPPoE* |
| 启用PPPoE代理 | `Frm_EnableProxy` | checkbox |  |  |
| 允许最大用户数 | `WanMaxUser_text` | text | 4 |  |
| IP地址 | `Frm_IPAddress` | text |  |  |
| 子网掩码 | `Frm_SubnetMask` | text |  |  |
| 默认网关 | `Frm_GateWay` | text |  |  |
| 主用DNS | `Frm_DNS1` | text |  |  |
| 备用DNS | `Frm_DNS2` | text |  |  |
|  | `Btn_Release` | button | 释 放 |  |
|  | `Btn_Renew` | button | 续 租 |  |
| 全局地址获取方式 | `Frm_GUASrc` | select-one | AutoConfigured | None,AutoConfigured*,DHCPv6,Static,AutoAdaptive |
| IPv6 | `Frm_GUA1` | text | 2408:8262:7e59:2219:d2dd:7cff:fe85:953f |  |
| IPv6 | `Frm_Gua1PrefixLen` | text | 64 |  |
| 网关获取方式 | `Frm_Gatewayv6Src` | select-one | AutoAdaptive | None,AutoConfigured,Static,AutoAdaptive* |
| IPv6 | `Frm_Gatewayv6` | text | fe80::d6c1:c8ff:fe8c:9200 |  |
| DNS获取方式 | `Frm_DNSv6Src` | select-one | AutoConfigured | None,AutoConfigured*,DHCPv6,Static,AutoAdaptive |
| DNS1 | `Frm_DNS1v6` | text | 2408:8662::2 |  |
| DNS2 | `Frm_DNS2v6` | text | 2408:8663::2 |  |
| 前缀获取方式 | `Frm_PrefixSrc` | select-one | PrefixDelegation | None,PrefixDelegation*,Static,PPPoE |
| IPv6 | `Frm_Prefix1` | text | 2408:8262:7e59:5045:: |  |
| IPv6 | `Frm_Prefix1Len` | text | 64 |  |
|  | `Btn_Add` | button |  创 建  |  |
|  | `Btn_Cancel` | button |  取 消  |  |
|  | `Btn_DoEdit` | button |  修 改  |  |
|  | `Btn_Delete` | button |  删 除  |  |

#### IPTV (Bridge) —— 选择失败 Locator.select_option: Timeout 30000ms exceeded.
Call log:
 

#### 新建 WAN 连接（选“新建”后的空表单）

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 连接名称 | `Frm_WANCName0` | select-one | -1 | -1*,IGD.WD1.WCD1.WCIP1,IGD.WD1.WCD3.WCPPP1,IGD.WD1.WCD4.WCIP1 |
| 使能 | `Frm_WANEnable` | checkbox | on |  |
| 封装类型 | `WanAddress_select` | select-one | PPP | PPP*,IP |
| 连接模式 | `WanConnectMode_select` | select-one | Route | Route*,BRIDGE |
| 业务类型 | `Frm_ServList` | select-one | 1 | 1*,4,5,32,8,16 |
| IP协议版本 | `Frm_protocol` | select-one | 1 | 1*,2,3 |
| 用户名 | `Frm_UserName` | text |  |  |
| 密码 | `Frm_Password` | password |  |  |
| 超级密码 | `Frm_Supassword` | password |  |  |
| MTU | `Frm_MTU` | text | 1480 |  |
| VLAN 模式 | `Frm_WBDMode` | select-one | 0 | 0*,1,2 |
| VLAN ID | `Frm_VLANID` | text |  |  |
| 802.1p | `Frm_Priority` | select-one | 0 | 0*,1,2,3,4,5,6,7 |
| 使能DSCP | `Frm_DSCP0` | checkbox |  |  |
| DSCP | `Frm_DSCP1` | text |  |  |
| 启用NAT | `Frm_IsNAT` | checkbox |  |  |
| NAT选型 | `Frm_NatMode` | select-one | 1 | 1*,2,3 |
| 启用NPTv6 | `Frm_IsNPT` | checkbox |  |  |
| DHCP服务使能 | `Frm_DHCPEnable` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH1` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH2` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH3` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH4` | checkbox |  |  |
|  | `Frm_PortETH5` | checkbox |  |  |
|  | `Frm_PortWLAN1` | checkbox |  |  |
|  | `Frm_PortWLAN2` | checkbox |  |  |
|  | `Frm_PortWLAN3` | checkbox |  |  |
|  | `Frm_PortWLAN4` | checkbox |  |  |
|  | `Frm_PortWLAN5` | checkbox |  |  |
|  | `Frm_PortWLAN6` | checkbox |  |  |
|  | `Frm_PortWLAN7` | checkbox |  |  |
|  | `Frm_PortWLAN8` | checkbox |  |  |
| 配置全路由使能 | `Frm_IpbindEnable` | checkbox | on |  |
| 目的IP转发列表 | `Frm_Ipbind_Area` | textarea |  |  |
| 启用PassThrough功能 | `Frm_PassThrough` | checkbox | on |  |
| 认证类型 | `Frm_AuthType` | select-one | PAP,CHAP,MS-CHAP | PAP,CHAP,MS-CHAP*,PAP,CHAP |
| 拨号模式 | `Frm_ConnTrigger` | select-one | AlwaysOn | AlwaysOn*,OnDemand,Manual |
| 超时时间 | `Frm_IdleTime` | text | 1200 |  |
|  | `Btn_Connect` | button | 连 接 |  |
|  | `Btn_Disconnect` | button | 断 开 |  |
| 用户名 | `Frm_IPoEUserName` | text |  |  |
| 密码 | `Frm_IPoEPassword` | password |  |  |
| 地址获取方式 | `WanIPv4Address_select` | select-one | PPPoE | PPPoE* |
| 启用PPPoE代理 | `Frm_EnableProxy` | checkbox |  |  |
| 允许最大用户数 | `WanMaxUser_text` | text | 4 |  |
| IP地址 | `Frm_IPAddress` | text |  |  |
| 子网掩码 | `Frm_SubnetMask` | text |  |  |
| 默认网关 | `Frm_GateWay` | text |  |  |
| 主用DNS | `Frm_DNS1` | text |  |  |
| 备用DNS | `Frm_DNS2` | text |  |  |
|  | `Btn_Release` | button | 释 放 |  |
|  | `Btn_Renew` | button | 续 租 |  |
| 全局地址获取方式 | `Frm_GUASrc` | select-one | None | None*,AutoConfigured,DHCPv6,Static,AutoAdaptive |
| IPv6 | `Frm_GUA1` | text |  |  |
| IPv6 | `Frm_Gua1PrefixLen` | text |  |  |
| 网关获取方式 | `Frm_Gatewayv6Src` | select-one | AutoAdaptive | None,AutoConfigured,Static,AutoAdaptive* |
| IPv6 | `Frm_Gatewayv6` | text |  |  |
| DNS获取方式 | `Frm_DNSv6Src` | select-one | None | None*,AutoConfigured,DHCPv6,Static,AutoAdaptive |
| DNS1 | `Frm_DNS1v6` | text |  |  |
| DNS2 | `Frm_DNS2v6` | text |  |  |
| 前缀获取方式 | `Frm_PrefixSrc` | select-one | None | None*,PrefixDelegation,Static,PPPoE |
| IPv6 | `Frm_Prefix1` | text |  |  |
| IPv6 | `Frm_Prefix1Len` | text |  |  |
|  | `Btn_Add` | button |  创 建  |  |
|  | `Btn_Cancel` | button |  取 消  |  |
|  | `Btn_DoEdit` | button |  修 改  |  |
|  | `Btn_Delete` | button |  删 除  |  |

### B. LAN配置 → RA配置 —— 打开失败 (Locator.click: Timeout 30000ms exceeded.
Call log:)

### B. LAN配置 → DHCPv6配置 —— 打开失败 (Locator.click: Timeout 30000ms exceeded.
Call log:)

### B. LAN配置 → IPv6前缀管理 —— 打开失败 (Locator.click: Timeout 30000ms exceeded.
Call log:)

### B2. 高级配置 → IPv6控制

URL: `/getpage.gch?pid=1002&nextpage=sec_ipv6_filterout_conf_t.gch`

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 使能 | `Frm_Enable` | checkbox |  |  |
| 协议 | `Frm_Protocol` | select-one | 0 | 0*,1,2,3,4 |
| 源起始IP地址 | `Frm_MinSrcIpv6` | text |  |  |
| 源结束IP地址 | `Frm_MaxSrcIpv6` | text |  |  |
| 源起始端口 | `Frm_MinSrcPort` | text |  |  |
| 源结束端口 | `Frm_MaxSrcPort` | text |  |  |
| 目的起始IP地址 | `Frm_MinDstIpv6` | text |  |  |
| 目的结束IP地址 | `Frm_MaxDstIpv6` | text |  |  |
| 目的起始端口 | `Frm_MinDstPort` | text |  |  |
| 目的结束端口 | `Frm_MaxDstPort` | text |  |  |
|  | `Btn_Add` | button | 添 加 |  |
|  | `Btn_Edit` | button | 修 改 |  |
|  | `back` | button | 取 消 |  |

### C. 绑定设置

URL: `/getpage.gch?pid=1002&nextpage=net_vlan_port_binding_t.gch`

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 绑定模式 | `Frm_Mode` | select-one | 0 | 0*,1 |
| 1 | `Frm_VLAN0a` | text |  |  |
| 1 | `Frm_VLAN0b` | text |  |  |
| 2 | `Frm_VLAN1a` | text |  |  |
| 2 | `Frm_VLAN1b` | text |  |  |
| 3 | `Frm_VLAN2a` | text |  |  |
| 3 | `Frm_VLAN2b` | text |  |  |
| 4 | `Frm_VLAN3a` | text |  |  |
| 4 | `Frm_VLAN3b` | text |  |  |
|  | `modify` | button | 修 改 |  |
|  | `back` | button | 取 消 |  |
| LAN1 | `Btn_Modify0` | button |  |  |
| LAN2 | `Btn_Modify1` | button |  |  |
| LAN3 | `Btn_Modify2` | button |  |  |
| LAN4 | `Btn_Modify3` | button |  |  |
| PON | `Btn_Modify4` | button |  |  |
| SSID1 | `Btn_Modify5` | button |  |  |
| SSID2 | `Btn_Modify6` | button |  |  |
| SSID3 | `Btn_Modify7` | button |  |  |
| SSID4 | `Btn_Modify8` | button |  |  |
| SSID5 | `Btn_Modify9` | button |  |  |
| SSID6 | `Btn_Modify10` | button |  |  |
| SSID7 | `Btn_Modify11` | button |  |  |
| SSID8 | `Btn_Modify12` | button |  |  |

连接名下拉：

- `Frm_Mode :: 0*,1`

### D. WLAN配置 → 无线基本配置(2.4G)

URL: `/getpage.gch?pid=1002&nextpage=net_wlan_basic_t1.gch`

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
| SSID选择 | `Frm_SSID_SET` | select-one | IGD.LD1.WLAN1 | IGD.LD1.WLAN1*,IGD.LD1.WLAN2,IGD.LD1.WLAN3,IGD.LD1.WLAN4 |
| 广播取消 | `Frm_ESSIDHideEnable` | checkbox |  |  |
| SSID使能 | `Frm_Enable` | checkbox |  |  |
| 双频合一 | `Frm_SSIDCombine` | checkbox |  |  |
| SSID名称 | `Frm_ESSID` | text | G7615_2G |  |
| WPA预共享密钥 | `Frm_KeyPassphrase` | password | g7615av5 |  |

### D. WLAN配置 → 无线基本配置(5G)

URL: `/getpage.gch?pid=1002&nextpage=net_wlan_basic_t2.gch`

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
| SSID选择 | `Frm_SSID_SET` | select-one | IGD.LD1.WLAN5 | IGD.LD1.WLAN5*,IGD.LD1.WLAN6,IGD.LD1.WLAN7 |
| 广播取消 | `Frm_ESSIDHideEnable` | checkbox |  |  |
| SSID使能 | `Frm_Enable` | checkbox |  |  |
| 双频合一 | `Frm_SSIDCombine` | checkbox |  |  |
| SSID名称 | `Frm_ESSID` | text | G7615_5G |  |
| WPA预共享密钥 | `Frm_KeyPassphrase` | password | g7615av5 |  |

### E. 设备管理 → 上行方式

URL: `/getpage.gch?pid=1002&nextpage=manager_Change_PonMode_qgw_t.gch`

```
设备管理
| 用户管理 | 设备重启 | 恢复出厂配置 | 设备管理 | 系统日志 | 语音协议切换 | 协议开关 | 网络诊断 | 环回检测配置 | 上行方式 | 从网关管理 |
上行方式
业务重启生效
模式选择
1G/XG自适应
GPON
XGPON
网口1
网口2
网口3
网口4
网上营业厅www.10010.com 网关厂商服务电话:800-8301118 客服热线10010 充值专线10011
```


---

## 附录二 · IPTV / IPv6 LAN 侧 / 上行方式

### A. IPTV 桥接连接（`IGD.WD1.WCD4.WCIP1` / `3_IPTV_B_VID_3185`）

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 连接名称 | `Frm_WANCName0` | select-one | IGD.WD1.WCD4.WCIP1 | -1,IGD.WD1.WCD1.WCIP1,IGD.WD1.WCD3.WCPPP1,IGD.WD1.WCD4.WCIP1* |
| 使能 | `Frm_WANEnable` | checkbox | on |  |
| 封装类型 | `WanAddress_select` | select-one | IP | PPP,IP* |
| 连接模式 | `WanConnectMode_select` | select-one | BRIDGE | Route,BRIDGE* |
| 业务类型 | `Frm_ServList` | select-one | 8 | 1,2,3,4,5,6,7,8*,16,32 |
| IP协议版本 | `Frm_protocol` | select-one | 1 | 1*,2,3 |
| 用户名 | `Frm_UserName` | text |  |  |
| 密码 | `Frm_Password` | password |  |  |
| 超级密码 | `Frm_Supassword` | password |  |  |
| MTU | `Frm_MTU` | text |  |  |
| VLAN 模式 | `Frm_WBDMode` | select-one | 2 | 0,1,2* |
| VLAN ID | `Frm_VLANID` | text | 3185 |  |
| 802.1p | `Frm_Priority` | select-one | 0 | 0*,1,2,3,4,5,6,7 |
| 使能DSCP | `Frm_DSCP0` | checkbox |  |  |
| DSCP | `Frm_DSCP1` | text |  |  |
| 启用NAT | `Frm_IsNAT` | checkbox |  |  |
| NAT选型 | `Frm_NatMode` | select-one | 1 | 1*,2,3 |
| 启用NPTv6 | `Frm_IsNPT` | checkbox |  |  |
| DHCP服务使能 | `Frm_DHCPEnable` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH1` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH2` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH3` | checkbox |  |  |
| 端口绑定 | `Frm_PortETH4` | checkbox |  |  |
|  | `Frm_PortETH5` | checkbox |  |  |
|  | `Frm_PortWLAN1` | checkbox |  |  |
|  | `Frm_PortWLAN2` | checkbox |  |  |
|  | `Frm_PortWLAN3` | checkbox |  |  |
|  | `Frm_PortWLAN4` | checkbox |  |  |
|  | `Frm_PortWLAN5` | checkbox |  |  |
|  | `Frm_PortWLAN6` | checkbox |  |  |
|  | `Frm_PortWLAN7` | checkbox |  |  |
|  | `Frm_PortWLAN8` | checkbox |  |  |
| 配置全路由使能 | `Frm_IpbindEnable` | checkbox | on |  |
| 目的IP转发列表 | `Frm_Ipbind_Area` | textarea |  |  |
| 启用PassThrough功能 | `Frm_PassThrough` | checkbox | on |  |
| 认证类型 | `Frm_AuthType` | select-one | PAP,CHAP,MS-CHAP | PAP,CHAP,MS-CHAP*,PAP,CHAP |
| 拨号模式 | `Frm_ConnTrigger` | select-one | AlwaysOn | AlwaysOn*,OnDemand,Manual |
| 超时时间 | `Frm_IdleTime` | text |  |  |
|  | `Btn_Connect` | button | 连 接 |  |
|  | `Btn_Disconnect` | button | 断 开 |  |
| 用户名 | `Frm_IPoEUserName` | text |  |  |
| 密码 | `Frm_IPoEPassword` | password |  |  |
| 地址获取方式 | `WanIPv4Address_select` | select-one | DHCP | Static,DHCP* |
| 启用PPPoE代理 | `Frm_EnableProxy` | checkbox |  |  |
| 允许最大用户数 | `WanMaxUser_text` | text | 4 |  |
| IP地址 | `Frm_IPAddress` | text |  |  |
| 子网掩码 | `Frm_SubnetMask` | text |  |  |
| 默认网关 | `Frm_GateWay` | text |  |  |
| 主用DNS | `Frm_DNS1` | text |  |  |
| 备用DNS | `Frm_DNS2` | text |  |  |
|  | `Btn_Release` | button | 释 放 |  |
|  | `Btn_Renew` | button | 续 租 |  |
| 全局地址获取方式 | `Frm_GUASrc` | select-one | None | None*,AutoConfigured,DHCPv6,Static,AutoAdaptive |
| IPv6 | `Frm_GUA1` | text |  |  |
| IPv6 | `Frm_Gua1PrefixLen` | text |  |  |
| 网关获取方式 | `Frm_Gatewayv6Src` | select-one | None | None*,AutoConfigured,Static,AutoAdaptive |
| IPv6 | `Frm_Gatewayv6` | text |  |  |
| DNS获取方式 | `Frm_DNSv6Src` | select-one | None | None*,AutoConfigured,DHCPv6,Static,AutoAdaptive |
| DNS1 | `Frm_DNS1v6` | text |  |  |
| DNS2 | `Frm_DNS2v6` | text |  |  |
| 前缀获取方式 | `Frm_PrefixSrc` | select-one | None | None*,PrefixDelegation,Static |
| IPv6 | `Frm_Prefix1` | text |  |  |
| IPv6 | `Frm_Prefix1Len` | text |  |  |
|  | `Btn_Add` | button |  创 建  |  |
|  | `Btn_Cancel` | button |  取 消  |  |
|  | `Btn_DoEdit` | button |  修 改  |  |
|  | `Btn_Delete` | button |  删 除  |  |

### B. LAN配置 → RA配置

URL: `/getpage.gch?pid=1002&nextpage=net_v6_ra_server_t.gch`

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 使能 | `Frm_Enable` | checkbox |  |  |
| 最小等待时间 | `Frm_MinWaitTime` | text | 200 |  |
| 最大等待时间 | `Frm_MaxWaitTime` | text | 600 |  |
| M | `Frm_Mangment` | checkbox |  |  |
| O | `Frm_OtherCfg` | checkbox |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### B. LAN配置 → DHCPv6配置

URL: `/getpage.gch?pid=1002&nextpage=net_v6_dhcp_dynamic_t.gch`

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| IP地址 | `Frm_IPv6Addr` | text | fe80::1 |  |
| IP地址 | `Frm_IPv6PrefLen` | text | 64 |  |
| 启动DHCP服务 | `Frm_ServerEnable` | checkbox | on |  |
| 起始IP地址 | `Frm_MinAddress` | text | :: |  |
| 结束IP地址 | `Frm_MaxAddress` | text | :: |  |
| DNS刷新时间 | `Frm_DnsRefreshTime` | text | 86400 |  |
| LAN侧DNS获取方式 | `Frm_IPv6DNSConfigType` | select-one | HGWProxy | WANConnection,Static,HGWProxy* |
| 广域网连接 | `Frm_IPv6DNSWANC` | select-one |  | *,IGD.WD1.WCD3.WCPPP1 |
| DNS1 | `Frm_SerIPv6Address3` | text |  |  |
| DNS2 | `Frm_SerIPv6Address4` | text |  |  |
| DNS3 | `Frm_SerIPv6Address5` | text |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### B. LAN配置 → IPv6前缀管理

URL: `/getpage.gch?pid=1002&nextpage=ipv6_net_prefix_t.gch`

| 标签 | id | 类型 | 当前值 | 选项 |
|---|---|---|---|---|
|  | `help_info` | button | 帮助 |  |
| 前缀 | `Frm_Prefix` | text |  |  |
| 前缀长度 | `Frm_PrefixLen` | text |  |  |
|  | `Btn_Submit` | button |  确 定  |  |
|  | `Btn_Cancel` | button |  取 消  |  |

### C. 上行方式（`manager_Change_PonMode_qgw_t.gch`）

| id | name | value | 选中 | 标签 |
|---|---|---|---|---|


---

## 附录三 · 最终生效配置基线（2026-10-31 实测）

> 本节为交接用的"当前正确状态"，照此可复现。

### 设备基本信息

| 项 | 值 | 来源 |
|---|---|---|
| 设备型号 | ZXHN G7615AV5 | 状态 › 设备信息 |
| 设备标识号 | D0DD7C-<设备SN已脱敏> | 同上 |
| 软件版本 | V3.0.5P1T1 | 同上 |
| 硬件版本 | V2.0 | 同上 |
| 区域 | 重庆 | 同上 |
| **上行方式** | **GPON**（不是 XGPON） | 同上；设备管理 › 上行方式 页可选 `1G/XG自适应 / GPON / XGPON` |
| ONU 注册状态 | 运行状态 (o5)，GPON 认证成功 | 状态 › 设备信息 |
| 光模块输入 | -15.5 dBm（参考 -27 ~ -8） | 状态 › 网络侧信息 › 下行光接口信息 |
| 光模块输出 | 2.3 dBm | 同上 |
| 温度 | 37 ℃ | 同上 |

> **GPON vs XGPON**：本页默认是 GPON。设备管理 › 上行方式 里三个选项是
> `1G/XG自适应 / GPON / XGPON`，切到 XGPON 需要 OLT 侧支持且会断线重注册，
> 本机保持 GPON 即可，不要动。

### 三条 WAN 连接

| 连接名 | 内部 ID | 封装/模式 | 业务 | VLAN模式 | VLAN ID | 802.1p | MTU | NAT | 账号 | 绑定端口 |
|---|---|---|---|---|---|---|---|---|---|---|
| `1_TR069_R_VID_3600` | IGD.WD1.WCD1.WCIP1 | IP / Route | 1 | — | 3600 | — | — | — | — | 未用（已停） |
| `2_INTERNET_R_VID_48` | IGD.WD1.WCD3.WCPPP1 | PPP / Route | 1 | **2 = 改写(tag)** | **48** | **0** | 1480 | 开 | `clan2301317426` | LAN1,LAN2,LAN3,SSID1,SSID5 |
| `3_IPTV_B_VID_3185` | IGD.WD1.WCD4.WCIP1 | IP / **BRIDGE** | 8 (IPTV) | **2 = 改写(tag)** | **3185** | 0 | — | — | — | **仅 LAN4** |

**关于 "VID" 到底在哪填** —— 网页 UI 里**不叫 VID，叫「VLAN ID」**：

| 标签 | id | 说明 |
|---|---|---|
| VLAN 模式 | `Frm_WBDMode` | `0` = 不打标(untag) / `1` = 透传 / `2` = 改写(tag) |
| **VLAN ID** | **`Frm_VLANID`** | ← **VID 就是这个框**，填 48 / 3185 |
| 802.1p | `Frm_Priority` | 优先级 0-7，宽带填 0 |

ITMS 下发的连接名是 `2_INTERNET_R_VID_`（**VID 后缀为空**），且 VLAN 模式=untag、VLAN ID=0
→ PPPoE 必然"连接 ISP 服务器超时"。这就是必须手工补 VLAN 的原因。

### 端口绑定（实测 checkbox 状态）

| 端口 | INTERNET | IPTV |
|---|---|---|
| LAN1 | ✅ | — |
| LAN2 | ✅ | — |
| LAN3 | ✅ | — |
| **LAN4** | — | ✅ **IPTV 专用口** |
| SSID1 (2.4G) | ✅ | — |
| SSID5 (5G) | ✅ | — |

> 绑定列表里 `Frm_PortWLANn` 对应的是 **SSIDn**：2.4G 是 SSID1→`Frm_PortWLAN1`，
> 5G 是 **SSID5→`Frm_PortWLAN5`**（不是 WLAN2）。IPTV 独占 LAN4 后 INTERNET 的
> LAN4 自动被解绑，属正常隔离。

### IPv6（已启用且出网正常）

| 项 | 值 | 位置 |
|---|---|---|
| 全局地址获取 | AutoConfigured | INTERNET 的 `Frm_GUASrc` |
| GUA | `2408:8262:7e59:2219:d2dd:7cff:fe85:953f` /64 | `Frm_GUA1` + `Frm_Gua1PrefixLen` |
| 前缀获取 | PrefixDelegation | `Frm_PrefixSrc` |
| 下发前缀 | `2408:8262:7e59:5045::` /64 | `Frm_Prefix1` |
| 网关 | `fe80::d6c1:c8ff:fe8c:9200`（AutoAdaptive） | `Frm_Gatewayv6Src` / `Frm_Gatewayv6` |
| RA | **已使能**（M=关, O=开） | LAN配置 › RA配置，`Frm_Enable` |
| DHCPv6 服务 | **已启动**，服务器地址 fe80::1 | LAN配置 › DHCPv6配置 |
| **LAN侧DNS来源** | **Static** → `2400:3200::1` / `2606:4700:4700::1111` | `Frm_IPv6DNSConfigType` + `Frm_SerIPv6Address3/4` |

客户端最终拿到：IPv4 DNS `114.114.114.114` / `8.8.8.8`（LAN DHCPv4 静态），
IPv6 DNS `2400:3200::1` / `2606:4700:4700::1111`（RA + DHCPv6 静态），**无需手工改客户端**。

### Wi-Fi

| 频段 | SSID | 密钥 | 选择器 |
|---|---|---|---|
| 2.4G | `G7615_2G` | `g7615av5` | `Frm_SSID_SET` = IGD.LD1.WLAN1 |
| 5G | `G7615_5G` | `g7615av5` | `Frm_SSID_SET` = IGD.LD1.WLAN5 |

> 这两个 SSID 和密钥是**我们改过的**（原厂随机值已被覆盖），复位会丢，改完记得重设。

### 账号层级（双重验证）

| 证据 | Row 0 | Row 1 |
|---|---|---|
| telnet `sendcmd 1 DB p DevAuthInfo` | Level 1（普通） | **Level 2（超管）** |
| 网页 设备管理 › 用户管理 | `Username0=user` / `right1` | `Username1=CUAdmin` / `right2` |

当前凭据：超管 `CUAdmin/CUAdmin`，普通 `user/CUAdmin`。
**以 Level 为准，不要信行号**（移动/联通固件行号语义相反）。

### 遗留问题与处理

| 问题 | 现象 | 处理 |
|---|---|---|
| **UDP DNS 被伪解析器劫持** | 问 `192.168.1.1` / `fe80::1`（光猫代理）→ 任意域名都回 `192.168.1.1`，特征 aa=1 + TTL=0；直连 `114.114.114.114` / `2408:8662::2` 正常 | 客户端绕开光猫代理：LAN DHCPv4 DNS 改 Static，DHCPv6 的 LAN侧DNS改 Static |
| 改 WAN 侧 IPv6 DNS 为 Static | 保存后立刻被重置回 `AutoConfigured` | **无效**，劫持发生在光猫/BRAS 侧的代理路径，只能从客户端侧绕 |
| `curl -6` 报 000 | 走了 `http_proxy` 环境变量 | 加 `--noproxy '*'`；这是假象，IPv6 本身通 |
| `factorymode/nE%jA@5b` 401 | 业务下发后工厂凭据被覆盖 | 只能复位后短暂使用；telnet 备份路径在重注册后失效 |
