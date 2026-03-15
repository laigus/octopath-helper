"""Generate app icon and create a desktop shortcut (no console window)."""

from __future__ import annotations

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.ico")
DIST_EXE = os.path.join(BASE_DIR, "dist", "八方旅人小工具.exe")
VENV_PYTHONW = os.path.join(BASE_DIR, ".venv", "Scripts", "pythonw.exe")
MAIN_PY = os.path.join(BASE_DIR, "main.py")


def _generate_icon():
    """Create a simple 8-pointed star icon for the app."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[WARN] Pillow not installed, skipping icon generation.")
        print("       Run: .venv\\Scripts\\pip.exe install Pillow -i https://pypi.tuna.tsinghua.edu.cn/simple")
        return False

    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for sz in sizes:
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        cx, cy = sz / 2, sz / 2
        r = sz * 0.42
        import math
        points = []
        for i in range(8):
            angle = math.radians(i * 45 - 90)
            radius = r if i % 2 == 0 else r * 0.5
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

        draw.polygon(points, fill=(105, 174, 248, 230))

        inner_r = sz * 0.12
        draw.ellipse(
            [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
            fill=(255, 255, 255, 200),
        )
        images.append(img)

    os.makedirs(os.path.dirname(ICON_PATH), exist_ok=True)
    images[0].save(ICON_PATH, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(f"[OK] Icon saved: {ICON_PATH}")
    return True


def _create_shortcut():
    """Create a Windows desktop shortcut using VBScript."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "八方旅人小工具.lnk")

    if os.path.exists(DIST_EXE):
        target = DIST_EXE
        arguments = ""
        work_dir = os.path.dirname(DIST_EXE)
        icon_arg = DIST_EXE
        print(f"[INFO] Using packaged exe: {DIST_EXE}")
    else:
        target = VENV_PYTHONW
        if not os.path.exists(target):
            target = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
        arguments = f'"""{MAIN_PY}"""'
        work_dir = BASE_DIR
        icon_arg = ICON_PATH if os.path.exists(ICON_PATH) else ""
        print(f"[INFO] Using Python: {target}")

    vbs_lines = [
        'Set WshShell = CreateObject("WScript.Shell")',
        f'Set oLink = WshShell.CreateShortcut("{shortcut_path}")',
        f'oLink.TargetPath = "{target}"',
    ]
    if arguments:
        vbs_lines.append(f'oLink.Arguments = {arguments}')
    vbs_lines.append(f'oLink.WorkingDirectory = "{work_dir}"')
    vbs_lines.append('oLink.WindowStyle = 7')
    if icon_arg:
        vbs_lines.append(f'oLink.IconLocation = "{icon_arg},0"')
    vbs_lines.append('oLink.Description = "八方旅人桌面小工具"')
    vbs_lines.append('oLink.Save')

    vbs = "\n".join(vbs_lines) + "\n"

    vbs_path = os.path.join(BASE_DIR, "_create_shortcut.vbs")
    with open(vbs_path, "w", encoding="gbk") as f:
        f.write(vbs)

    os.system(f'cscript //nologo "{vbs_path}"')
    os.remove(vbs_path)
    print(f"[OK] Shortcut created: {shortcut_path}")


if __name__ == "__main__":
    print("=== 八方旅人小工具 - 快捷方式安装 ===\n")
    _generate_icon()
    _create_shortcut()
    print("\n完成！双击桌面上的「八方旅人小工具」图标即可启动。")
