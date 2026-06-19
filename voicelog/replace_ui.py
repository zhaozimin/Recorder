#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 AppKit(PyObjC) 的 NSWindow/NSTextView 等；依赖 ui_common 的 BtnTarget/make_label
[OUTPUT]: 对外提供 ReplaceWindow 类(text/close，保存时回调 on_save(text))
[POS]: voicelog 的「关键词纠错管理 UI 面」。一个可编辑文本框承载全部纠错规则(每行 `错误=正确`)，
       增/删/改/批量都在这一个面里编辑——保存时把整段文本交回主文件解析并写回 config。纯展示层，不碰业务。
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

好品味：不为「单条添加」「批量添加」分两套 UI——一个文本框即可，加=敲一行，批量=粘多行，删=删一行。
所有 AppKit 操作必须在主线程(rumps 菜单回调)调用。
"""
from AppKit import (
    NSWindow, NSTextView, NSScrollView, NSButton, NSApp, NSFont,
    NSMakeRect, NSMakeSize, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSBackingStoreBuffered, NSFloatingWindowLevel, NSBezelBorder,
)

from ui_common import BtnTarget, make_label


# ============================================================================
#  关键词纠错窗口：可编辑文本框(每行「错误=正确」) + 保存/取消。
# ============================================================================
class ReplaceWindow:
    def __init__(self, initial_text: str, on_save):
        self.on_save = on_save
        W, H = 560, 520
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, W, H),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered, False)
        win.setTitle_("关键词纠错")
        win.setLevel_(NSFloatingWindowLevel)
        win.center()
        self.win = win
        c = win.contentView()

        c.addSubview_(make_label(
            NSMakeRect(20, H - 70, W - 40, 50),
            "每行一条，格式：错误写法 = 正确写法\n"
            "例：克劳德 = Claude    增 / 删 / 改 / 批量都在这里编辑，「保存」即时生效。", 13))

        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 70, W - 40, H - 150))
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(NSBezelBorder)
        tv = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, W - 40, H - 150))
        tv.setEditable_(True)
        tv.setRichText_(False)
        tv.setTextContainerInset_(NSMakeSize(10, 10))
        tv.setFont_(NSFont.userFixedPitchFontOfSize_(15) or NSFont.systemFontOfSize_(15))
        tv.setString_(initial_text)
        scroll.setDocumentView_(tv)
        self.tv = tv
        c.addSubview_(scroll)

        cancel = NSButton.alloc().initWithFrame_(NSMakeRect(W - 260, 20, 110, 34))
        cancel.setTitle_("取消")
        cancel.setBezelStyle_(1)
        self._t_cancel = BtnTarget.alloc().initWithCallback_(self.close)
        cancel.setTarget_(self._t_cancel)
        cancel.setAction_("invoke:")
        c.addSubview_(cancel)

        save = NSButton.alloc().initWithFrame_(NSMakeRect(W - 140, 20, 110, 34))
        save.setTitle_("保存")
        save.setBezelStyle_(1)
        self._t_save = BtnTarget.alloc().initWithCallback_(self._save)
        save.setTarget_(self._t_save)
        save.setAction_("invoke:")
        c.addSubview_(save)

        NSApp.activateIgnoringOtherApps_(True)
        win.makeKeyAndOrderFront_(None)

    def text(self) -> str:
        try:
            return self.tv.string()
        except Exception:
            return ""

    def _save(self):
        if self.on_save:
            self.on_save(self.text())

    def close(self):
        try:
            self.win.orderOut_(None)
            self.win.close()
        except Exception:
            pass
