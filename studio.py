#!/usr/bin/env python3
"""Zen Sidebar Studio 2.0 entry point. Local configuration is loaded only on launch."""
import os
import sys

if os.environ.get('QT_QPA_PLATFORMTHEME')=='gtk3':os.environ['QT_QPA_PLATFORMTHEME']=''
if os.environ.get('WAYLAND_DISPLAY') and not os.environ.get('QT_QPA_PLATFORM'):
    os.environ['QT_QPA_PLATFORM']='wayland'

from core.settings import PROFILE,ROOT,DEFAULTS,load_settings
from core.zen_integration import variables,save_mod
from ui.preview import Preview
from ui.main_window import Studio


def main():
    from PySide6.QtWidgets import QApplication
    from ui.theme import STYLE
    app=QApplication(sys.argv);app.setApplicationName('Zen Sidebar Studio');app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    window=Studio();window.show()
    return app.exec()


if __name__=='__main__':sys.exit(main())
