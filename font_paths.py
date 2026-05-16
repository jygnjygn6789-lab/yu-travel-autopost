"""
字型路徑統一管理
Windows 本機用 C:/Windows/Fonts/，Railway/Linux 用 fonts/ 目錄
"""
import os

_DIR = os.path.dirname(__file__)
_FONTS = os.path.join(_DIR, "fonts")

FONT_KAIU  = os.path.join(_FONTS, "kaiu.ttf")
FONT_BOLD  = os.path.join(_FONTS, "msjhbd.ttc")
FONT_REG   = os.path.join(_FONTS, "msjh.ttc")
FONT_EMOJI = os.path.join(_FONTS, "seguiemj.ttf")
