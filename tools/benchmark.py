#!/usr/bin/env python3
"""Reproducible local benchmark; creates no profile changes."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QPA_PLATFORMTHEME']=''
import sys,time,json,resource,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
started=time.perf_counter()
from PySide6.QtWidgets import QApplication
from veil_for_zen.core.rendering import render_wallpaper
from veil_for_zen.core.settings import DEFAULTS
from veil_for_zen.core.image_library import scan_images
from veil_for_zen.core.settings import save_json
from veil_for_zen.ui.main_window import Studio
from veil_for_zen.ui.theme import STYLE
app=QApplication([])
startup=time.perf_counter()-started
with tempfile.TemporaryDirectory() as cache:
    os.environ['XDG_CACHE_HOME']=cache
    os.environ['XDG_DATA_HOME']=str(Path(cache)/'data');os.environ['XDG_CONFIG_HOME']=str(Path(cache)/'config')
    source=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'fn_zen'
    t=time.perf_counter();entries=scan_images(source,48);lib=time.perf_counter()-t
    t=time.perf_counter();scan_images(source,48);libwarm=time.perf_counter()-t
    if not entries: raise SystemExit('Nenhuma imagem compatível na biblioteca informada.')
    s=DEFAULTS|{'background_mode':'Imagem','image':entries[0][0]}
    t=time.perf_counter();render_wallpaper(s);cold=time.perf_counter()-t
    t=time.perf_counter();render_wallpaper(s);warm=time.perf_counter()-t
    t=time.perf_counter();render_wallpaper(s|{'brightness':125});filtered=time.perf_counter()-t
    t=time.perf_counter();render_wallpaper(s|{'background_mode':'Cor sólida'});solid=time.perf_counter()-t
    profile=Path(cache)/'profile';profile.mkdir();(profile/'prefs.js').touch()
    settings=Path(cache)/'settings.json';save_json(settings,s|{'profile':str(profile),'color_mode':'Personalizada'})
    app.setStyle('Fusion');app.setStyleSheet(STYLE)
    t=time.perf_counter();window=Studio(settings,Path(cache)/'presets.json',library_path=source);window.show()
    deadline=time.perf_counter()+15
    while (window.preview.wallpaper is None or window.preview.running or window.library_busy) and time.perf_counter()<deadline:
        app.processEvents();time.sleep(.002)
    window_ready=time.perf_counter()-t
    window.preview.timer.stop();window.preview.pool.waitForDone();window.pool.waitForDone();window.saved=window.state.copy();window.close()
    print(json.dumps(dict(import_qt_seconds=startup,window_ready_seconds=window_ready,library_seconds=lib,library_cached_seconds=libwarm,
        images=len(entries),render_cold_seconds=cold,render_warm_seconds=warm,filtered_seconds=filtered,
        solid_seconds=solid,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),indent=2))
