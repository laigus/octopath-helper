"""Octopath Traveler desktop helper — compact floating checklist."""

from __future__ import annotations

import json
import os
import sys

from PyQt6.QtCore import QEvent, QPoint, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QColor, QFontDatabase, QIcon, QPainter, QPainterPath, QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.acrylic import disable_acrylic, enable_acrylic

if getattr(sys, "frozen", False):
    BUNDLE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BUNDLE_DIR

DATA_DIR = os.path.join(APP_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
FONT_PATH = os.path.join(BUNDLE_DIR, "assets", "fonts", "HarmonyOS_SansSC_Medium.ttf")
ICON_PATH = os.path.join(BUNDLE_DIR, "assets", "icon.ico")

COMMAND_COLS = ["打倒人", "获取NPC道具", "拉人进队", "获取情报"]
DAY_ROWS = [
    [("剑士", "#ff4d4f"), ("盗贼2", "#8b5cf6"), ("神官", "#a0aec0"), ("学者2", "#d08a35")],
    [("猎人", "#86c854"), ("商人4", "#f6ad55"), ("舞娘", "#ff7bc4"), ("药师1", "#4da3ff")],
]
NIGHT_ROWS = [
    [("盗贼", "#8b5cf6"), ("学者3", "#d08a35"), ("猎人", "#86c854"), ("神官3", "#a0aec0")],
    [("药师", "#4da3ff"), ("舞娘1", "#ff7bc4"), ("商人", "#f6ad55"), ("剑士4", "#ff4d4f")],
]
WEAPON_ITEMS = ["剑", "长枪", "短剑", "斧头", "弓", "杖"]
ELEMENT_ITEMS = [
    ("火", "#f2b7a4"), ("冰", "#9ec1de"), ("雷", "#e6d08f"),
    ("风", "#d4ebc7"), ("光", "#f1edd2"), ("暗", "#b6adc7"),
]

FONT_FAMILY = "HarmonyOS Sans SC"

SVG_MOON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>"""
SVG_SUN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>"""


def _svg_icon(svg_template: str, color: str, size: int = 18) -> QIcon:
    svg_bytes = svg_template.format(color=color).encode("utf-8")
    pm = QPixmap(QSize(size, size))
    pm.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtSvg import QSvgRenderer
    renderer = QSvgRenderer(svg_bytes)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return QIcon(pm)


def _s(tpl: str, **kw) -> str:
    for k in sorted(kw, key=len, reverse=True):
        tpl = tpl.replace(f"${k}", kw[k])
    return tpl


class HelperWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._drag_offset: QPoint | None = None
        self._acrylic_applied = False
        self._boxes: dict[str, QCheckBox] = {}
        self._groups: dict[str, list[QCheckBox]] = {"cmd": []}
        self._weak_pages: list[dict] = []  # [{widget, boxes, group, tab_btn, del_btn}]
        self._state = self._load_state()
        self._theme: str = self._state.get("theme", "dark")
        if self._theme not in ("dark", "light"):
            self._theme = "dark"

        self._load_font()
        self._build()
        self._restore_checks()

    def _load_font(self):
        if os.path.exists(FONT_PATH):
            QFontDatabase.addApplicationFont(FONT_PATH)

    def _build(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("八方旅人小工具")
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumSize(500, 170)
        self.resize(570, 200)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 7, 10, 10)
        root.setSpacing(4)

        # --- toolbar ---
        bar = QHBoxLayout()
        bar.setSpacing(3)

        self._tab_btns: list[QPushButton] = []
        self._tab_bar = bar

        btn_cmd = QPushButton("指令")
        btn_cmd.setObjectName("tabBtn")
        btn_cmd.setCheckable(True)
        btn_cmd.clicked.connect(lambda: self._switch_tab(0))
        bar.addWidget(btn_cmd)
        self._tab_btns.append(btn_cmd)

        self._weak_tab_layout = QHBoxLayout()
        self._weak_tab_layout.setSpacing(2)
        bar.addLayout(self._weak_tab_layout)

        self._add_weak_btn = QPushButton("+")
        self._add_weak_btn.setObjectName("toolBtn")
        self._add_weak_btn.setFixedSize(24, 24)
        self._add_weak_btn.setToolTip("新增怪物弱点页")
        self._add_weak_btn.clicked.connect(self._add_weakness_page)
        bar.addWidget(self._add_weak_btn)

        bar.addStretch()

        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("toolBtn")
        self._theme_btn.setToolTip("切换黑/白主题")
        self._theme_btn.setFixedSize(28, 24)
        self._theme_btn.setIconSize(QSize(16, 16))
        self._theme_btn.clicked.connect(self._toggle_theme)
        bar.addWidget(self._theme_btn)

        self._clear_btn = QPushButton("清空")
        self._clear_btn.setObjectName("toolBtn")
        self._clear_btn.clicked.connect(self._clear_current)
        bar.addWidget(self._clear_btn)

        for text, tip, slot, obj_name in [
            ("–", "最小化", self.showMinimized, "toolBtn"),
            ("×", "关闭", self.close, "closeBtn"),
        ]:
            b = QPushButton(text)
            b.setObjectName(obj_name)
            b.setFixedSize(24, 24)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            bar.addWidget(b)

        root.addLayout(bar)

        # --- stacked pages ---
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_commands())
        root.addWidget(self._stack)

        weak_count = max(1, self._state.get("weak_page_count", 1))
        for _ in range(weak_count):
            self._add_weakness_page(restore=True)

        self._switch_tab(0)
        self._apply_theme()
        self._restore_pos()

    # ── pages ──

    def _page_commands(self) -> QWidget:
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        for c, title in enumerate(COMMAND_COLS, start=1):
            lbl = QLabel(title)
            lbl.setObjectName("colHeader")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, 0, c)

        row = 1
        for section, rows, prefix in [("白天", DAY_ROWS, "day"), ("晚上", NIGHT_ROWS, "night")]:
            lbl = QLabel(section)
            lbl.setObjectName("rowHeader")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, row, 0, len(rows), 1)
            for ri, cells in enumerate(rows):
                for ci, (name, color) in enumerate(cells, start=1):
                    key = f"cmd_{prefix}_{ri}_{ci}"
                    cb = self._cb(name, key, "cmd", color)
                    cb.setMinimumWidth(80)
                    grid.addWidget(cb, row + ri, ci, alignment=Qt.AlignmentFlag.AlignCenter)
            row += len(rows)

        grid.setColumnStretch(0, 1)
        for c in range(1, 5):
            grid.setColumnStretch(c, 2)
        return page

    def _page_weakness(self, page_idx: int) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(0, 2, 0, 0)
        vbox.setSpacing(4)

        boxes: list[QCheckBox] = []

        w_row = QHBoxLayout()
        w_row.setSpacing(0)
        for i, name in enumerate(WEAPON_ITEMS):
            key = f"weak{page_idx}_w_{i}"
            cell = self._weak_cell(name, key, None, boxes)
            w_row.addWidget(cell)
        vbox.addLayout(w_row)

        e_row = QHBoxLayout()
        e_row.setSpacing(0)
        for i, (name, bg) in enumerate(ELEMENT_ITEMS):
            key = f"weak{page_idx}_e_{i}"
            cell = self._weak_cell(name, key, bg, boxes)
            e_row.addWidget(cell)
        vbox.addLayout(e_row)

        return page, boxes

    def _weak_cell(self, name: str, key: str, bg: str | None, boxes: list[QCheckBox]) -> QWidget:
        cell = QWidget()
        vb = QVBoxLayout(cell)
        vb.setContentsMargins(2, 3, 2, 3)
        vb.setSpacing(4)
        vb.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(name)
        lbl.setObjectName("weakLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if bg:
            lbl.setStyleSheet(
                f"QLabel#weakLabel {{ background: {bg}; color: #232323; border-radius: 3px; padding: 1px 6px; }}"
            )
        vb.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        cb = self._cb("", key, None)
        cb.setObjectName("weakBox")
        boxes.append(cb)
        vb.addWidget(cb, alignment=Qt.AlignmentFlag.AlignCenter)
        return cell

    def _cb(self, text: str, key: str, group: str | None, color: str | None = None) -> QCheckBox:
        cb = QCheckBox(text)
        if color:
            cb.setStyleSheet(f"QCheckBox {{ color: {color}; }}")
        cb.toggled.connect(self._save)
        self._boxes[key] = cb
        if group:
            self._groups[group].append(cb)
        return cb

    # ── weakness page management ──

    def _add_weakness_page(self, restore: bool = False):
        page_idx = len(self._weak_pages)
        page_widget, boxes = self._page_weakness(page_idx)
        stack_idx = self._stack.addWidget(page_widget)

        tab_container = QWidget()
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(1)

        label = f"弱点" if page_idx == 0 else f"弱点{page_idx + 1}"
        tab_btn = QPushButton(label)
        tab_btn.setObjectName("tabBtn")
        tab_btn.setCheckable(True)
        tab_btn.clicked.connect(lambda _, si=stack_idx: self._switch_tab(si))
        tab_layout.addWidget(tab_btn)
        self._tab_btns.append(tab_btn)

        del_btn = None
        if page_idx > 0:
            del_btn = QPushButton("×")
            del_btn.setObjectName("weakDelBtn")
            del_btn.setFixedSize(18, 18)
            del_btn.setToolTip("删除此弱点页")
            del_btn.clicked.connect(lambda _, pi=page_idx: self._remove_weakness_page(pi))
            tab_layout.addWidget(del_btn)

        self._weak_tab_layout.addWidget(tab_container)

        info = {
            "widget": page_widget,
            "boxes": boxes,
            "tab_btn": tab_btn,
            "del_btn": del_btn,
            "tab_container": tab_container,
            "stack_idx": stack_idx,
        }
        self._weak_pages.append(info)

        if not restore:
            self._save()
            self._switch_tab(stack_idx)

    def _remove_weakness_page(self, page_idx: int):
        if page_idx <= 0 or page_idx >= len(self._weak_pages):
            return

        info = self._weak_pages[page_idx]

        for cb in info["boxes"]:
            key = next((k for k, v in self._boxes.items() if v is cb), None)
            if key:
                del self._boxes[key]

        self._tab_btns.remove(info["tab_btn"])
        self._stack.removeWidget(info["widget"])
        info["widget"].deleteLater()
        info["tab_container"].deleteLater()
        self._weak_pages.pop(page_idx)

        self._rebuild_weak_tabs()
        self._switch_tab(0)
        self._save()

    def _rebuild_weak_tabs(self):
        """Rebuild tab labels and reconnect signals after a page removal."""
        for i, info in enumerate(self._weak_pages):
            label = "弱点" if i == 0 else f"弱点{i + 1}"
            info["tab_btn"].setText(label)
            stack_idx = self._stack.indexOf(info["widget"])
            info["stack_idx"] = stack_idx

            try:
                info["tab_btn"].clicked.disconnect()
            except TypeError:
                pass
            info["tab_btn"].clicked.connect(lambda _, si=stack_idx: self._switch_tab(si))

            if info["del_btn"]:
                try:
                    info["del_btn"].clicked.disconnect()
                except TypeError:
                    pass
                info["del_btn"].clicked.connect(lambda _, pi=i: self._remove_weakness_page(pi))

            old_keys = [k for k, v in self._boxes.items() if v in info["boxes"]]
            for k in old_keys:
                del self._boxes[k]
            for j, cb in enumerate(info["boxes"]):
                if j < len(WEAPON_ITEMS):
                    new_key = f"weak{i}_w_{j}"
                else:
                    new_key = f"weak{i}_e_{j - len(WEAPON_ITEMS)}"
                self._boxes[new_key] = cb

    # ── tab switching ──

    def _switch_tab(self, stack_idx: int):
        self._stack.setCurrentIndex(stack_idx)
        self._tab_btns[0].setChecked(stack_idx == 0)
        for info in self._weak_pages:
            info["tab_btn"].setChecked(
                self._stack.indexOf(info["widget"]) == stack_idx
            )

    def _clear_current(self):
        si = self._stack.currentIndex()
        if si == 0:
            for cb in self._groups["cmd"]:
                cb.setChecked(False)
        else:
            for info in self._weak_pages:
                if self._stack.indexOf(info["widget"]) == si:
                    for cb in info["boxes"]:
                        cb.setChecked(False)
                    break
        self._save()

    # ── theme ──

    def _toggle_theme(self):
        self._theme = "light" if self._theme == "dark" else "dark"
        self._apply_theme()
        self._apply_acrylic()
        self.update()
        self._save()

    def _apply_theme(self):
        dark = self._theme == "dark"
        icon_color = "#c8d4e4" if dark else "#4a5568"
        self._theme_btn.setIcon(
            _svg_icon(SVG_MOON if dark else SVG_SUN, icon_color, 16)
        )

        if dark:
            fg = "rgba(230,236,248,220)"
            fg2 = "rgba(200,210,225,130)"
            sel = "rgba(255,255,255,22)"
            hover = "rgba(255,255,255,14)"
            ind_bg = "rgba(255,255,255,8)"
            ind_bdr = "rgba(180,200,220,110)"
            ind_hov = "rgba(80,120,170,45)"
            ind_chk = "#69aef8"
            ind_chk_bdr = "#b9dbff"
            close_hov = "rgba(232,60,60,90)"
        else:
            fg = "rgba(18,22,28,220)"
            fg2 = "rgba(60,70,85,140)"
            sel = "rgba(0,0,0,12)"
            hover = "rgba(0,0,0,8)"
            ind_bg = "rgba(0,0,0,6)"
            ind_bdr = "rgba(80,95,115,130)"
            ind_hov = "rgba(200,218,235,50)"
            ind_chk = "#4f90e8"
            ind_chk_bdr = "#3f78c5"
            close_hov = "rgba(232,60,60,90)"

        self.setStyleSheet(_s("""
            QWidget {
                font-family: "$font", "Segoe UI", "Microsoft YaHei UI", sans-serif;
                color: $fg;
                font-size: 13px;
            }
            QPushButton#tabBtn {
                border: none;
                border-radius: 5px;
                background: transparent;
                padding: 4px 16px;
                font-size: 14px;
                font-weight: 600;
                color: $fg2;
            }
            QPushButton#tabBtn:checked {
                background: $sel;
                color: $fg;
                font-weight: 700;
            }
            QPushButton#tabBtn:hover:!checked {
                background: $hover;
            }
            QPushButton#toolBtn {
                border: none;
                border-radius: 5px;
                background: transparent;
                padding: 2px 8px;
                font-size: 12px;
                font-weight: 600;
                color: $fg2;
            }
            QPushButton#toolBtn:hover {
                background: $hover;
                color: $fg;
            }
            QPushButton#closeBtn {
                border: none;
                border-radius: 5px;
                background: transparent;
                font-size: 15px;
                color: $fg2;
            }
            QPushButton#closeBtn:hover {
                background: $close_hov;
                color: #fff;
            }
            QPushButton#weakDelBtn {
                border: none;
                border-radius: 3px;
                background: transparent;
                font-size: 12px;
                font-weight: 700;
                color: $fg2;
                padding: 0;
            }
            QPushButton#weakDelBtn:hover {
                background: $close_hov;
                color: #fff;
            }
            QLabel#colHeader {
                font-size: 12px;
                font-weight: 600;
                color: $fg2;
                padding: 0px 2px;
                border: none;
            }
            QLabel#rowHeader {
                font-size: 14px;
                font-weight: 700;
                color: $fg;
                padding: 0 6px;
                border: none;
            }
            QLabel#weakLabel {
                font-size: 14px;
                font-weight: 600;
                color: $fg;
                padding: 2px 6px;
            }
            QCheckBox {
                spacing: 3px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 1px;
            }
            QCheckBox#weakBox {
                spacing: 0;
                padding: 0;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid $ind_bdr;
                background: $ind_bg;
            }
            QCheckBox::indicator:hover {
                background: $ind_hov;
            }
            QCheckBox::indicator:checked {
                background: $ind_chk;
                border: 1px solid $ind_chk_bdr;
            }
        """,
            font=FONT_FAMILY,
            fg=fg, fg2=fg2, sel=sel, hover=hover,
            ind_bg=ind_bg, ind_bdr=ind_bdr, ind_hov=ind_hov,
            ind_chk=ind_chk, ind_chk_bdr=ind_chk_bdr,
            close_hov=close_hov,
        ))

    # ── persistence ──

    def _load_state(self) -> dict:
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _restore_checks(self):
        checks = self._state.get("checks", {})
        for k, v in checks.items():
            mapped_key = k
            if k.startswith("weak_w_") or k.startswith("weak_e_"):
                mapped_key = k.replace("weak_", "weak0_", 1)
            cb = self._boxes.get(mapped_key)
            if cb:
                cb.setChecked(bool(v))

    def _restore_pos(self):
        pos = self._state.get("window_pos")
        if isinstance(pos, list) and len(pos) == 2:
            self.move(pos[0], pos[1])
        else:
            g = QApplication.primaryScreen().geometry()
            self.move(g.width() - self.width() - 28, 40)

    def _save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "window_pos": [self.x(), self.y()],
                "checks": {k: cb.isChecked() for k, cb in self._boxes.items()},
                "theme": self._theme,
                "weak_page_count": len(self._weak_pages),
            }, f, ensure_ascii=False, indent=2)

    # ── acrylic / painting ──

    def _apply_acrylic(self):
        hwnd = int(self.winId())
        tint = 0x01F0F0F0 if self._theme == "light" else 0x01080A10
        self._acrylic_applied = enable_acrylic(hwnd, tint, dark_mode=(self._theme == "dark"))
        if not self._acrylic_applied:
            disable_acrylic(hwnd, dark_mode=(self._theme == "dark"))

    def showEvent(self, event):
        super().showEvent(event)
        if not self._acrylic_applied:
            self._apply_acrylic()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 10, 10)
        if self._theme == "light":
            p.fillPath(path, QColor(255, 255, 255, 1))
            p.setPen(QPen(QColor(0, 0, 0, 14), 0.5))
        else:
            p.fillPath(path, QColor(0, 0, 0, 1))
            p.setPen(QPen(QColor(255, 255, 255, 14), 0.5))
        p.drawPath(path)
        p.end()

    # ── drag ──

    def _begin_drag(self, gp: QPoint):
        self._drag_offset = gp - self.frameGeometry().topLeft()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() <= 34:
            self._begin_drag(e.globalPosition().toPoint())
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_offset and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_offset = None

    def closeEvent(self, e):
        self._save()
        super().closeEvent(e)


def main():
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        ctypes.c_wchar_p("laigus.octopath-helper")
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    w = HelperWindow()
    if os.path.exists(ICON_PATH):
        w.setWindowIcon(QIcon(ICON_PATH))
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
