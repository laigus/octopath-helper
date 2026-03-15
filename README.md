# 八方旅人桌面小工具

悬浮在桌面顶层的轻量面板，为《八方旅人》游戏提供快捷勾选工具。

## 功能

- **指令打勾** — 白天/晚上 × 打倒人/获取NPC道具/拉人进队/获取情报
- **弱点打勾** — 武器（剑/长枪/短剑/斧头/弓/杖）+ 元素（火/冰/雷/风/光/暗）
- **标签页切换** — 指令/弱点两页切换，节省空间
- **一键清空** — 清空当前页所有勾选
- **黑/白主题** — 一键切换
- **磨砂透明** — Windows Acrylic 磨砂效果 + DWM 圆角阴影
- **状态记忆** — 勾选状态、窗口位置、主题偏好自动保存
- **无命令行启动** — 桌面快捷方式双击即用

## 环境要求

- Windows 10/11
- Python 3.10+

## 首次安装

在 PowerShell 中执行：

```powershell
cd d:\AI\octopath-helper

# 创建虚拟环境
python -m venv .venv

# 安装依赖
$env:NO_PROXY="*"
.venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 启动方式

### 方式一：桌面快捷方式（推荐）

运行一次安装脚本，自动生成图标和桌面快捷方式：

```powershell
.venv\Scripts\python.exe setup_shortcut.py
```

之后双击桌面上的 **「八方旅人小工具」** 图标即可启动，无需打开终端。

### 方式二：双击 run.bat

直接双击项目目录下的 `run.bat`，会自动安装依赖并启动（会有命令行窗口）。

### 方式三：命令行启动

```powershell
.venv\Scripts\python.exe main.py
```

## 使用方法

1. 启动后面板出现在屏幕右上角
2. 拖动顶部栏可移动窗口
3. 点击「指令」/「弱点」切换页面
4. 勾选/取消勾选对应项目
5. 点击「清空」一键清除当前页
6. 点击月亮/太阳图标切换黑白主题
7. 点击「–」最小化到任务栏，点击「×」关闭

## 数据文件

- `data/state.json` — 勾选状态、窗口位置、主题偏好（自动生成）

## 技术栈

- Python + PyQt6（无边框置顶窗口）
- Windows DWM API（Acrylic 磨砂 + 圆角阴影）
- HarmonyOS Sans SC（华为鸿蒙字体）
- SVG 图标渲染（月亮/太阳主题切换）
