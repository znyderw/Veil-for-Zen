import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QPA_PLATFORMTHEME']=''
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QColor
from PySide6.QtWidgets import QApplication,QLineEdit
from veil_for_zen.core.settings import DEFAULTS,normalize,load_settings,save_json
from veil_for_zen.core.rendering import background_rect,render_wallpaper,gaussian
from veil_for_zen.core.color_extractor import extract_palette,tab_paint
from veil_for_zen.core.presets import Presets
from veil_for_zen.core.zen_integration import save_mod,build_css,merge_import,detect_dimensions,MARKER,backup_root
from veil_for_zen.ui.main_window import Studio
from veil_for_zen.ui.theme import STYLE
from veil_for_zen.core.image_library import scan_images,import_image

app=QApplication.instance() or QApplication([])
from veil_for_zen.ui.theme import apply_theme
apply_theme(app)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.root/'config'),'XDG_DATA_HOME':str(self.root/'data'),'XDG_CACHE_HOME':str(self.root/'cache')});self.env.start()
        self.image=self.root/'wall paper.png'
        img=QImage(120,200,QImage.Format_RGBA8888);img.fill(QColor('#59796d'));img.save(str(self.image))
        self.profile=self.root/'profile';self.profile.mkdir();(self.profile/'prefs.js').write_text('/* test */')
        self.s=normalize(DEFAULTS|dict(background_mode='Imagem',image=str(self.image),profile=str(self.profile),preview_width=180,preview_height=400,blur=0,controls=0))
    def tearDown(self):self.env.stop();self.tmp.cleanup()


class LibraryTest(Fixture):
    def test_extensionless_images_and_invalid_files(self):
        library=self.root/'fn_zen';library.mkdir()
        (library/'2').write_bytes(self.image.read_bytes());(library/'1.png').write_bytes(self.image.read_bytes())
        (library/'notes.txt').write_text('not an image')
        entries=scan_images(library)
        self.assertEqual([Path(path).name for path,_ in entries],['1.png','2'])
        self.assertTrue(all(not thumb.isNull() for _,thumb in entries))
    def test_import_preserves_conflicting_files_and_source(self):
        library=self.root/'fn_zen';library.mkdir()
        (library/self.image.name).write_bytes(b'original file')
        imported=Path(import_image(self.image,library))
        self.assertNotEqual(imported.name,self.image.name)
        self.assertEqual((library/self.image.name).read_bytes(),b'original file')
        self.assertEqual(imported.read_bytes(),self.image.read_bytes())
        self.assertEqual(import_image(self.image,library),str(imported))
        self.assertTrue(self.image.exists())
    def test_gallery_selection_updates_wallpaper(self):
        library=self.root/'fn_zen';library.mkdir();image=library/'1';image.write_bytes(self.image.read_bytes())
        settings=self.root/'settings.json';save_json(settings,self.s)
        window=Studio(settings,self.root/'presets.json')
        try:
            deadline=time.monotonic()+5
            while not window.controls.gallery.count() and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            self.assertEqual(window.controls.gallery.count(),1)
            window.controls.gallery.itemClicked.emit(window.controls.gallery.item(0))
            self.assertEqual(window.state['image'],str(image))
        finally:
            window.library_timer.stop();window.preview.timer.stop();window.preview.pool.waitForDone();window.pool.waitForDone()
            window.saved=window.state.copy();window.close();app.processEvents()


class SettingsTest(Fixture):
    def test_legacy_migration(self):
        path=self.root/'legacy.json';old={k:self.s[k] for k in ['image','opacity','blur','sizing','zoom','x','y','preview_width']}
        old.update(opacity=73,blur=36,zoom=259,x=52,preview_width=253)
        save_json(path,old);s=load_settings(path)
        for key,value in old.items():self.assertEqual(s[key],value)
        self.assertEqual(s['version'],2);self.assertEqual(s['dimension_mode'],'Manual')
    def test_invalid_values(self):
        for field,value in [('opacity','oops'),('blur',float('nan')),('version',99),('sizing','Unknown'),('palette',['red']),('fit',1)]:
            with self.subTest(field=field),self.assertRaises(ValueError):normalize(self.s|{field:value})
    def test_atomic_settings_roundtrip(self):
        path=self.root/'settings.json';save_json(path,self.s);self.assertEqual(load_settings(path),self.s)
        self.assertEqual(list(self.root.glob('.settings.json-*')),[])


class RenderingTest(Fixture):
    def test_geometry_reference_values(self):
        for sizing,expected in [('Largura',(0,100,200,400)),('Conter',(0,100,200,400)),('Preencher',(-25,0,250,500)),('Esticar',(0,0,200,500))]:
            with self.subTest(mode=sizing):
                rect=background_rect(100,200,200,500,self.s|dict(sizing=sizing,zoom=100,x=50,y=100))
                self.assertEqual(rect.getRect(),expected)
        rect=background_rect(100,200,200,500,self.s|dict(zoom=200,x=25,y=80))
        self.assertEqual(rect.getRect(),(-50,-240,400,800))
    def test_multiple_aspect_ratios(self):
        for iw,ih in [(800,100),(100,800),(200,200)]:
            img=QImage(iw,ih,QImage.Format_RGB32);img.fill(QColor('red'));img.save(str(self.image))
            for mode in ['Largura','Conter','Preencher','Esticar']:
                out,glass,_=render_wallpaper(self.s|{'sizing':mode})
                self.assertEqual(out.width(),180);self.assertEqual(out.height(),400);self.assertFalse(glass.isNull())
    def test_opacity_and_darkness(self):
        out,_,_=render_wallpaper(self.s|dict(opacity=0,darkness=0));self.assertEqual(out.pixelColor(90,200).name(),'#050505')
        out,_,_=render_wallpaper(self.s|dict(darkness=100));self.assertEqual(out.pixelColor(90,200).name(),'#000000')
    def test_effects_change_pixels(self):
        a,_,_=render_wallpaper(self.s)
        b,_,_=render_wallpaper(self.s|dict(grayscale=100,brightness=150))
        self.assertNotEqual(a.pixelColor(90,300),b.pixelColor(90,300))
        color=b.pixelColor(90,300);self.assertEqual(color.red(),color.green());self.assertEqual(color.red(),color.blue())
    def test_gaussian_spreads_energy(self):
        image=QImage(41,41,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent);image.setPixelColor(20,20,QColor('white'))
        blurred=gaussian(image,2)
        self.assertGreater(blurred.pixelColor(19,20).alpha(),0)
        self.assertLess(blurred.pixelColor(20,20).alpha(),255)
    def test_gaussian_preserves_constant_brightness(self):
        image=QImage(160,160,QImage.Format_ARGB32_Premultiplied);image.fill(QColor('#808080'))
        for sigma in [1,4,20]:
            self.assertEqual(gaussian(image,sigma).pixelColor(80,80).getRgb(),(128,128,128,255))
    def test_missing_image(self):
        with self.assertRaises(ValueError):render_wallpaper(self.s|{'image':str(self.root/'missing.png')})


class PaletteTest(Fixture):
    def test_muted_dominant_palette(self):
        for color in ['#59796d','#ff0000','#ffffff','#000000']:
            img=QImage(60,60,QImage.Format_RGB32);img.fill(QColor(color));palette=extract_palette(img)
            self.assertEqual(palette,extract_palette(img));self.assertEqual(len(palette),4)
            for value in palette:
                c=QColor(value);self.assertLessEqual(c.hsvSaturationF(),.33);self.assertLess(c.valueF(),.65)
    def test_states_and_intensity(self):
        normal,hover,selected=[tab_paint(self.s,state) for state in ['normal','hover','selected']]
        self.assertLess(normal['neutral'][3],hover['neutral'][3]);self.assertLess(hover['neutral'][3],selected['neutral'][3])
        off=tab_paint(self.s|{'intensity':0});self.assertEqual(off['border'][3],0);self.assertEqual(off['tint'][3],0)
        borders=tab_paint(self.s|{'tab_style':'Preenchimento suave'});self.assertEqual(borders['border'][3],0)
    def test_text_contrast_over_white_wallpaper(self):
        def luminance(rgb):
            parts=[v/255 for v in rgb]
            linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in parts]
            return sum(a*b for a,b in zip(linear,[.2126,.7152,.0722]))
        for state in ['normal','hover','selected']:
            style=tab_paint(self.s|dict(palette=['#ffffff'],shade=0,intensity=100),state)
            a=style['neutral'][3]/255;t=style['tint'][3]/255
            background=[(255*(1-a)+style['neutral'][i]*a)*(1-t)+style['tint'][i]*t for i in range(3)]
            ratio=(luminance([245]*3)+.05)/(luminance(background)+.05)
            self.assertGreaterEqual(ratio,4.5)


class IntegrationTest(Fixture):
    def test_preserve_imports_and_third_party_css(self):
        chrome=self.profile/'chrome';chrome.mkdir()
        original='@charset "UTF-8";\n@import url("other.css");\n/* third party */\n#urlbar { color: hotpink !important; }\n'
        (chrome/'userChrome.css').write_text(original)
        (chrome/'sidebar-background.css').write_text('legacy CSS, do not touch')
        backup=save_mod(self.s)
        updated=(chrome/'userChrome.css').read_text()
        self.assertTrue(updated.startswith('@charset "UTF-8";'))
        self.assertIn(original.split(';',1)[1],updated)
        manifest=json.loads((backup/'manifest.json').read_text())
        entry=next(f for f in manifest['files'] if f['path']=='chrome/userChrome.css')
        self.assertEqual((backup/entry['before']).read_text(),original)
        self.assertEqual((chrome/'sidebar-background.css').read_text(),'legacy CSS, do not touch')
        save_mod(self.s);self.assertEqual((chrome/'userChrome.css').read_text(),updated)
        self.assertEqual(len(list(backup_root(self.profile).glob('*/manifest.json'))),2)
        self.assertTrue((chrome/'veil-for-zen.css').read_text().startswith(MARKER))
        self.assertIn('toolkit.legacyUserProfileCustomizations.stylesheets', (self.profile/'user.js').read_text())
    def test_preserve_userjs_and_existing_enabled_preference(self):
        original='// unrelated\nuser_pref("network.dns.disablePrefetch", false);\nuser_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\n'
        (self.profile/'user.js').write_text(original);save_mod(self.s)
        self.assertEqual((self.profile/'user.js').read_text(),original)
    def test_css_variables_and_selectors(self):
        css=build_css(self.s,'file:///tmp/image.png')
        self.assertNotIn('/* SETTINGS */',css)
        defined=set(re.findall(r'(--zss-[\w-]+)\s*:',css));used=set(re.findall(r'var\((--zss-[\w-]+)\)',css))
        self.assertEqual(used-defined,set());self.assertEqual(css.count('{'),css.count('}'))
        for selector in ['[selected]','[visuallyselected]','[zen-essential]',':hover']:
            self.assertIn(selector,css)
        self.assertNotIn('[image*=',css)
    def test_disabled_import_does_not_prevent_install(self):
        original='/* @import url("veil-for-zen.css"); */\n@import url("other.css");\n'
        merged=merge_import(original)
        self.assertTrue(merged.endswith(original));self.assertEqual(merged.count('@import url("veil-for-zen.css");'),2)
    def test_missing_image_does_not_write(self):
        with self.assertRaises(ValueError):save_mod(self.s|{'image':str(self.root/'missing.png')})
        self.assertFalse((self.profile/'chrome').exists())
    def test_conflicting_file_preserved(self):
        chrome=self.profile/'chrome';chrome.mkdir();target=chrome/'veil-for-zen.css';target.write_text('foreign')
        with self.assertRaises(ValueError):save_mod(self.s)
        self.assertEqual(target.read_text(),'foreign')
    def test_rollback_on_write_failure(self):
        chrome=self.profile/'chrome';chrome.mkdir();user=chrome/'userChrome.css';user.write_text('original')
        from veil_for_zen.core.settings import atomic_write as real_write
        failed=False
        def failing(path,data):
            nonlocal failed
            if Path(path)==user and not failed:failed=True;raise OSError('simulated failure')
            real_write(path,data)
        with patch('veil_for_zen.core.zen_integration.atomic_write',side_effect=failing),self.assertRaises(OSError):save_mod(self.s)
        self.assertEqual(user.read_text(),'original');self.assertFalse((chrome/'veil-for-zen.css').exists())
    def test_external_window_not_used_as_sidebar(self):
        (self.profile/'xulstore.json').write_text(json.dumps({'chrome://browser/content/browser.xhtml':{'navigator-toolbox':{'width':'178px'}}}))
        result=type('Result',(),dict(returncode=0,stdout=json.dumps([{'class':'zen','size':[1760,990]}])))()
        with patch('veil_for_zen.core.zen_integration.subprocess.run',return_value=result):detected=detect_dimensions(self.profile)
        self.assertFalse(detected['exact']);self.assertEqual(detected['saved_width'],178)
        self.assertEqual(detected['window'],[1760,990]);self.assertNotIn('height',detected)


class PresetsTest(Fixture):
    def test_crud_and_history(self):
        p=Presets(self.root/'presets.json');ident=p.add('Noite',self.s);p.rename(ident,'Floresta')
        self.assertEqual(p.data['presets'][0]['name'],'Floresta');self.assertEqual(p.get(ident),self.s)
        p.remember(self.s);p.remember(self.s);self.assertEqual(len(p.data['history']),1)
        p.delete(ident);self.assertEqual(p.data['presets'],[]);self.assertTrue(self.image.exists())
        self.assertEqual(len(Presets(p.path).data['history']),1)
    def test_missing_image_and_future_version(self):
        p=Presets(self.root/'presets.json');ident=p.add('A',self.s);self.image.unlink()
        with self.assertRaises(ValueError):p.get(ident)
        with self.assertRaises(ValueError):p.add('B',self.s|{'version':99})


class InterfaceTest(Fixture):
    def test_apply_flow_uses_only_temporary_profile(self):
        path=self.root/'settings.json';save_json(path,self.s|{'color_mode':'Personalizada'})
        w=Studio(path,self.root/'presets.json');w.show()
        try:
            w.change('opacity',55);w.apply_settings()
            deadline=time.monotonic()+10
            while w.working and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            self.assertFalse(w.working)
            self.assertTrue((self.profile/'chrome/veil-for-zen.css').exists())
            self.assertEqual(load_settings(path)['opacity'],55)
            self.assertEqual(len(w.presets.data['history']),2)
        finally:
            w.preview.timer.stop();w.preview.pool.waitForDone();w.pool.waitForDone();w.saved=w.state.copy();w.close();app.processEvents()
    def test_startup_controls_and_sizes(self):
        path=self.root/'settings.json';save_json(path,self.s)
        w=Studio(path,self.root/'presets.json');w.show()
        try:
            deadline=time.monotonic()+10
            while time.monotonic()<deadline and (w.preview.wallpaper is None or w.preview.running):
                app.processEvents();time.sleep(.01)
            self.assertIsNotNone(w.preview.wallpaper)
            self.assertGreater(w.controls.inputs['opacity'].findChild(QLineEdit).width(),40)
            before=(w.state['preview_width'],w.state['preview_height'])
            for width,height in [(800,600),(1120,850),(1440,950)]:
                w.resize(width,height);app.processEvents();self.assertFalse(w.grab().isNull())
                self.assertEqual((w.state['preview_width'],w.state['preview_height']),before)
            w.controls.inputs['opacity'].setValue(31);self.assertEqual(w.state['opacity'],31)
            self.assertIn('não aplicadas',w.dirty.text());w.restore();self.assertEqual(w.state['opacity'],100)
            w.controls.palette_chosen.emit(['#53678b']);self.assertEqual(w.state['color_mode'],'Personalizada')
        finally:
            w.preview.timer.stop();w.preview.pool.waitForDone();w.pool.waitForDone();w.saved=w.state.copy();w.close();app.processEvents()


if __name__=='__main__':unittest.main(verbosity=2)
