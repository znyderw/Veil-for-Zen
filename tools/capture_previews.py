#!/usr/bin/env python3
"""Capture the real application UI offscreen with an original demo image.
All profile/config/data writes are confined to a temporary directory.
"""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QPA_PLATFORMTHEME']=''
import sys,time,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt
from veil_for_zen.core.settings import DEFAULTS,save_json
from veil_for_zen.core.profiles import Profile
from veil_for_zen.ui.main_window import VeilWindow
from veil_for_zen.ui.theme import apply_theme
app=QApplication([]);apply_theme(app)
with tempfile.TemporaryDirectory(prefix='veil-captures-') as directory:
    root=Path(directory)
    os.environ['HOME']=str(root)
    os.environ['XDG_CONFIG_HOME']=str(root/'config')
    os.environ['XDG_DATA_HOME']=str(root/'data')
    os.environ['XDG_CACHE_HOME']=str(root/'cache')
    library=root/'images';library.mkdir()
    image=QImage(1600,1000,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
    painter=QPainter(image);QSvgRenderer(str(ROOT/'docs/assets/demo-background.svg')).render(painter);painter.end()
    image.save(str(library/'Veil-demo.png'))
    profile=root/'Perfil de demonstração';profile.mkdir();(profile/'prefs.js').touch()
    state=DEFAULTS|{'profile':str(profile),'image':str(library/'Veil-demo.png'),'background_mode':'Imagem','sizing':'Preencher','color_mode':'Personalizada'}
    save_json(root/'settings.json',state)
    with patch('veil_for_zen.ui.main_window.discover_profiles',return_value=[Profile(profile,profile.name)]):
        window=VeilWindow(root/'settings.json',root/'presets.json',library_path=library)
    window.show()
    def capture(name):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            app.processEvents()
            if window.preview.wallpaper is not None and not window.preview.running and not window.preview.timer.isActive() and not window.library_busy:break
            time.sleep(.01)
        else:raise RuntimeError('Preview did not finish rendering.')
        app.processEvents()
        if not window.grab().save(str(ROOT/'docs'/name)):raise RuntimeError('Could not save screenshot.')
    capture('veil-image.png')
    window.change('background_scope','Navegador inteiro');capture('veil-full-browser.png')
    window.change('background_scope','Barra lateral');window.change('background_mode','Cor sólida')
    window.change('solid_color','#17243A');window.change('solid_transparency',45);capture('veil-solid.png')
    window.library_timer.stop();window.preview.timer.stop();window.preview.pool.waitForDone();window.pool.waitForDone()
    window.saved=window.state.copy();window.close()
print('Three application screenshots captured using the MIT demo artwork and a temporary profile.')
