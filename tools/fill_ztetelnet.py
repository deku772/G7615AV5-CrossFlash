#!/usr/bin/env python3
"""拉起 ZteTelnet.exe，切到基本配置页，填入 factorymode 凭据并保持窗口打开。

用户随后手动操作：捅 reset → 开机 → 点「使能」→ 弹窗看临时账号 → 点「固化Telnet」。
"""
import sys
import time

from pywinauto import Application, Desktop

EXE = r"E:\projects\g7615av5\ZteTelnet.exe"
USER = "factorymode"
PWD = "nE%jA@5b"

print("[1] 启动 ZteTelnet ...", flush=True)
# 若已有实例先不复用，直接再起一个可能冲突；先查找现有窗口
existing = Desktop(backend="uia").windows()
tel = None
for w in existing:
    if "ZTE" in (w.window_text() or "") or "Telnet" in (w.window_text() or ""):
        tel = w
        print("发现已有窗口:", w.window_text())
        break
if tel is None:
    app = Application(backend="uia").start(EXE)
    time.sleep(3)
    tel = app.top_window()
    tel.set_focus()
    time.sleep(1)
    print("已启动:", tel.window_text())
else:
    tel.set_focus()

print("[2] 切换到「基本配置」标签 ...", flush=True)
try:
    tel.click_input(coords=(50, 40))
    time.sleep(1)
except Exception as e:
    print("切标签失败(可能已在基本配置):", e)

print("[3] 填用户名/密码 ComboBox ...", flush=True)


def set_combo(win, x, y, text, label):
    try:
        combo = win.child_window(control_type="ComboBox")
        # 用坐标点击聚焦该输入行，再定位可见 Edit
    except Exception:
        pass
    # 直接坐标点击输入框内部
    win.click_input(coords=(x, y))
    time.sleep(0.5)
    # 找该 ComboBox 内部的 Edit
    edits = win.descendants(control_type="Edit")
    target = None
    for e in edits:
        try:
            rect = e.rectangle()
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
            if abs(cx - (win.rectangle().left + x)) < 200 and abs(cy - (win.rectangle().top + y)) < 40:
                target = e
                break
        except Exception:
            continue
    if target is None:
        # 退化：找带文本框特征的所有 Edit，按 y 排序取第 index 个
        cands = []
        for e in edits:
            try:
                r = e.rectangle()
                if r.height() < 40 and (r.bottom - r.top) > 10:
                    cands.append((r.top, e))
            except Exception:
                continue
        cands.sort(key=lambda t: t[0])
        idx = 0 if label == "user" else 1
        if len(cands) > idx:
            target = cands[idx][1]
    if target is None:
        print("!! 未找到 %s 输入框" % label)
        return False
    try:
        target.set_edit_text(text)
        print("  %s <- %s" % (label, text))
        return True
    except Exception as ex:
        print("  set_edit_text 失败(%s): %s" % (label, str(ex)[:80]))
        return False


ok1 = set_combo(tel, 368, 509, USER, "user")
ok2 = set_combo(tel, 924, 509, PWD, "pwd")
print("[4] 填写结果: user=%s pwd=%s" % (ok1, ok2), flush=True)

# 截图留证
tel.capture_as_image().save(r"E:\projects\g7615av5\.temp\ztetelnet_filled.png")
print("截图: E:/projects/g7615av5/.temp/ztetelnet_filled.png")
print("DONE - 窗口保持打开，等待用户操作")
