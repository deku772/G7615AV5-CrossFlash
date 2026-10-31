#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""硬复位后的"黄金窗口"收网脚本。

流程（光纤保持拔掉）:
  1. 轮询 192.168.1.1 直到 web 起来
  2. CUAdmin/CUAdmin 登录（联通硬复位默认库）
  3. ZTElnet26 开 telnet，捕获临时账号
  4. 用临时账号 dump DevAuthInfo / WLANCfg / WLANPSK / MgtServer 到 .temp/
  5. 可选：关 TR-069、改超密、改 WiFi

用法:
  python tools/recover_after_reset.py --wait 600
  python tools/recover_after_reset.py --wait 600 --apply --ssid MyWiFi --wifi-pass 12345678
  python tools/recover_after_reset.py --telnet-user root --telnet-pass Zte521   # 手工指定临时账号
"""
import argparse, hashlib, http.cookiejar, os, random, re, subprocess, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".temp")
BASE = "http://192.168.1.1"
ZTE = os.path.join(ROOT, "third_party", "ZTElnet26-windows-amd64.exe")


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


# ---------------- 1. 等设备上线 ----------------
def wait_online(seconds):
    log("等待光猫上线（最多 %ds）..." % seconds)
    end = time.time() + seconds
    while time.time() < end:
        try:
            r = urllib.request.urlopen(BASE + "/", timeout=3)
            body = r.read()
            if b"Frm_Loginchecktoken" in body:
                log("web 已就绪（%d 字节登录页）" % len(body))
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


# ---------------- 2. 登录 ----------------
def web_login(password, acct="adm"):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", "Mozilla/5.0")]
    html = op.open(BASE + "/", timeout=10).read().decode("gb2312", "replace")
    tok = re.search(r'Frm_Loginchecktoken"\)\.value\s*=\s*"([^"]+)"', html)
    st = re.search(r'var Status\s*=\s*"(\d+)"', html)
    rs = re.search(r'var Result\s*=\s*"(\d+)"', html)
    log("页面状态: Status=%s Result=%s token=%s" % (st.group(1) if st else "?", rs.group(1) if rs else "?", tok.group(1) if tok else "MISSING"))
    if not tok:
        return False, html
    num = random.randint(10000000, 99999999)
    pw = hashlib.sha256((password + str(num)).encode()).hexdigest()
    f = {"Frm_Logintoken": "0", "Frm_Loginchecktoken": tok.group(1),
         "_cu_url": "1" if acct == "adm" else "0", "Right": "1" if acct == "adm" else "2",
         "Username": "", "UserRandomNum": str(num), "Password": pw,
         "action": "login", "accountType": acct}
    req = urllib.request.Request(BASE + "/", data=urllib.parse.urlencode(f).encode(), headers={"Referer": BASE + "/"})
    body = op.open(req, timeout=15).read().decode("gb2312", "replace")
    if "Frm_Loginchecktoken" in body:
        ln = re.search(r"var\s+Lognumber\s*=\s*(\d+)", body)
        return False, "失败 Lognumber=%s" % (ln.group(1) if ln else "?")
    return True, "OK"


# ---------------- 3. 开 telnet ----------------
def open_telnet(pc_mac):
    log("ZTElnet26 -m %s ..." % pc_mac)
    try:
        p = subprocess.run([ZTE, "-i", "192.168.1.1", "-m", pc_mac, "-p", "80",
                            "-u", "factorymode", "-pw", "nE%jA@5b"],
                           capture_output=True, timeout=60)
    except Exception as e:
        return None, None, "执行异常: %s" % e
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    print(out.strip())
    if "401" in out or "Error" in out:
        return None, None, out.strip()
    user = re.search(r'(?i)(?:user|account|用户名|账号)\s*[:：=]\s*(\S{2,32})', out)
    pwd = re.search(r'(?i)(?:pass|pwd|密码)\s*[:：=]\s*(\S{2,32})', out)
    return (user.group(1) if user else None), (pwd.group(1) if pwd else None), out.strip()


# ---------------- 4. telnet 执行 ----------------
def telnet_run(user, pwd, commands, wait_default=3.0):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from telnet_session import TelnetSession
    s = TelnetSession("192.168.1.1")
    out_all = []
    try:
        if not s.wait_for("ogin", 12):
            s.close(); return None
        s.send_line(user)
        if not s.wait_for("assword", 12):
            s.close(); return None
        s.send_line(pwd)
        ok = False
        end = time.time() + 15
        while time.time() < end:
            d = s.read_for(0.5)
            out_all.append(d)
            if any(k in d for k in ("incorrect", "failed", "denied")):
                s.close(); return None
            if d.rstrip().endswith(("#", ">", "$")):
                ok = True; break
        if not ok:
            s.close(); return None
        for c in commands:
            w = wait_default
            if "@@" in c:
                c, ws = c.rsplit("@@", 1); w = float(ws)
            log("telnet> %s" % c)
            s.send_line(c)
            d = s.read_for(w)
            out_all.append(d)
        try:
            s.send_line("exit"); s.read_for(0.5)
        except Exception:
            pass
    finally:
        s.close()
    return "".join(out_all)


DUMP_CMDS = [
    "sendcmd 1 DB p DevAuthInfo@@3",
    "sendcmd 1 DB p DevAuthInfo@@3",
    "sendcmd 1 DB p WLANPSK@@3",
    "sendcmd 1 DB p WLANCfg@@4",
    "sendcmd 1 DB p MgtServer@@3",
    "cat /proc/csp/versionstates@@2",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=int, default=600)
    ap.add_argument("--pc-mac", default="888888888788")
    ap.add_argument("--admin-pass", default="CUAdmin")
    ap.add_argument("--telnet-user", default=None)
    ap.add_argument("--telnet-pass", default=None)
    ap.add_argument("--apply", action="store_true", help="同时关闭 TR-069 并保存")
    ap.add_argument("--ssid", default=None)
    ap.add_argument("--wifi-pass", default=None)
    a = ap.parse_args()

    os.makedirs(TMP, exist_ok=True)

    if not wait_online(a.wait):
        log("超时：设备未上线"); sys.exit(1)

    log("尝试登录 CUAdmin/%s" % a.admin_pass)
    ok, msg = web_login(a.admin_pass)
    log("登录结果: %s" % ("成功" if ok else msg))
    if not ok:
        log("→ 默认库密码不是 CUAdmin，先别插光纤，手工在浏览器确认（最多再试 2 次，每次间隔 60s）")
        sys.exit(2)

    user, pwd = a.telnet_user, a.telnet_pass
    if not user:
        user, pwd, raw = open_telnet(a.pc_mac)
        if not user:
            log("开 telnet 失败: %s" % raw)
            sys.exit(3)
        log("临时账号: %s / %s" % (user, pwd))

    out = telnet_run(user, pwd, DUMP_CMDS)
    if not out:
        log("telnet 登录失败"); sys.exit(4)
    path = os.path.join(TMP, "ont_dump.txt")
    open(path, "w", encoding="utf-8", errors="replace").write(out)
    log("已 dump → %s (%d 字符)" % (path, len(out)))

    rows = re.findall(r'<Row No="(\d+)">\s*<DM name="(?:User|Level)"[^/]*/>', out)
    log("DevAuthInfo 行数: %d" % len(set(rows)))

    if a.apply:
        cmds = ['sendcmd 1 DB set MgtServer 0 URL ""@@2',
                'sendcmd 1 DB set MgtServer 0 PeriodicInformEnable 0@@2',
                'sendcmd 1 DB save@@4']
        if a.ssid:
            cmds += ['sendcmd 1 DB set WLANCfg 0 ESSID "%s"@@2' % a.ssid,
                     'sendcmd 1 DB set WLANCfg 4 ESSID "%s"@@2' % a.ssid]
        if a.wifi_pass:
            for idx in (0, 4):
                cmds += ['sendcmd 1 DB set WLANPSK %d KeyPassphrase "%s"@@2' % (idx, a.wifi_pass)]
                cmds += ['sendcmd 1 DB set WLANPSK %d PreSharedKey "%s"@@2' % (idx, a.wifi_pass)]
        cmds += ['sendcmd 1 DB save@@4']
        log("开始应用改动 ...")
        out2 = telnet_run(user, pwd, cmds)
        if out2:
            open(os.path.join(TMP, "ont_apply.txt"), "w", encoding="utf-8", errors="replace").write(out2)
            log("改动已应用，回执见 .temp/ont_apply.txt")
        else:
            log("改动阶段 telnet 掉线，重开账号再执行一次")
            sys.exit(5)

    log("完成。下一步：拔掉的还是光纤 ×  先别插，按 README Step 9.5 建 WAN 后再插。")
    print("\n临时 telnet 账号（仅本次有效）: %s / %s" % (user, pwd))


if __name__ == "__main__":
    main()
