"""Public beta regression tests. All writes use temporary XDG homes/profiles."""
import json
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from test_studio import Fixture,app
from PySide6.QtCore import Qt,QThread
from PySide6.QtGui import QImage,QColor,QPalette
from PySide6.QtWidgets import QComboBox,QToolButton,QLineEdit,QMessageBox
from veil_for_zen.core import paths
from veil_for_zen.core.profiles import discover_profiles,check_writable
from veil_for_zen.core.settings import DEFAULTS,normalize,save_json,load_settings
from veil_for_zen.core.migration import migrate
from veil_for_zen.core.presets import Presets
from veil_for_zen.core.rendering import render_wallpaper
from veil_for_zen.core.zen_integration import (save_mod,disable_mod,restore_backup,build_css,
    merge_import,remove_import,IMPORT,FILENAME,backup_root)
from veil_for_zen.ui.main_window import Studio

class ProfilesTest(Fixture):
    def test_native_relative_absolute_default_and_spaces(self):
        root=self.root/'native';root.mkdir()
        relative=root/'abc.Default profile';relative.mkdir();(relative/'prefs.js').touch()
        absolute=self.root/'custom Profile';absolute.mkdir();(absolute/'prefs.js').touch()
        (root/'profiles.ini').write_text(f'[Profile0]\nName=Main\nPath={relative.name}\nIsRelative=1\nDefault=1\n[Profile1]\nName=Custom\nPath={absolute}\nIsRelative=0\n')
        profiles=discover_profiles(roots=[(root,'native')])
        self.assertEqual([p.path for p in profiles],[relative,absolute]);self.assertTrue(profiles[0].default)
    def test_flatpak_detection_with_fake_home(self):
        home=self.root/'home';root=home/'.var/app/app.zen_browser.zen/.zen';root.mkdir(parents=True)
        p=root/'test';p.mkdir();(p/'prefs.js').touch()
        found=discover_profiles(home)
        self.assertEqual(len(found),1);self.assertEqual(found[0].source,'flatpak')
    def test_missing_malformed_and_duplicate_profiles(self):
        root=self.root/'native';root.mkdir();p=root/'valid';p.mkdir();(p/'prefs.js').touch()
        (root/'profiles.ini').write_text('malformed')
        self.assertEqual(len(discover_profiles(roots=[(root,'native'),(root,'native')])),1)
        self.assertEqual(discover_profiles(roots=[(root/'absent','native')]),[])
    def test_permission_and_invalid_profile(self):
        with patch('veil_for_zen.core.profiles.os.access',return_value=False),self.assertRaises(PermissionError):check_writable(self.profile)
        with self.assertRaises(ValueError):check_writable(self.root)

class XdgMigrationTest(Fixture):
    def test_xdg_and_relative_env_fallback(self):
        self.assertEqual(paths.settings_file(),self.root/'config/veil-for-zen/settings.json')
        self.assertEqual(paths.library_dir(),self.root/'data/veil-for-zen/images')
        with patch.dict(os.environ,{'XDG_CACHE_HOME':'relative'}),patch('pathlib.Path.home',return_value=self.root):
            self.assertEqual(paths.cache_dir(),self.root/'.cache/veil-for-zen')
    def test_copy_migration_keeps_originals_and_history(self):
        legacy=self.root/'old';legacy.mkdir();save_json(legacy/'settings.json',self.s)
        p=Presets(legacy/'presets.json');ident=p.add('Legacy',self.s);p.remember(self.s)
        original=(legacy/'settings.json').read_bytes()
        result=migrate(legacy)
        self.assertEqual((legacy/'settings.json').read_bytes(),original)
        self.assertTrue(self.image.exists());self.assertTrue(Path(result['image']).is_file())
        self.assertNotEqual(result['image'],self.s['image'])
        migrated=Presets();self.assertEqual(len(migrated.data['history']),1)
        self.assertEqual(migrated.get(ident)['image'],result['image'])
        self.assertEqual(load_settings()['opacity'],self.s['opacity'])
        with self.assertRaises(ValueError):migrate(legacy)
    def test_malformed_migration_never_creates_settings(self):
        legacy=self.root/'bad';legacy.mkdir();(legacy/'settings.json').write_text('{}')
        (legacy/'presets.json').write_text('{"bad":true}')
        with self.assertRaises(ValueError):migrate(legacy)
        self.assertFalse(paths.settings_file().exists())

class SolidAndPresetsTest(Fixture):
    def test_solid_never_loads_an_image(self):
        s=self.s|{'background_mode':'Cor sólida','image':'/not/an/image','solid_color':'#17243A'}
        with patch('veil_for_zen.core.rendering.load_image',side_effect=AssertionError('image decoded')):
            base,glass,_=render_wallpaper(s)
        self.assertEqual(base.pixelColor(10,10).name(),'#17243a')
        css=build_css(s);self.assertIn('--zss-background: #17243A',css);self.assertIn('--zss-image: none',css)
        save_mod(s);self.assertFalse((self.profile/'chrome/backgrounds').exists())
    def test_solid_transparency_matches_css_and_pixel_alpha(self):
        for transparency,alpha,css_color in [(0,255,'#17243A'),(50,128,'rgb(23 36 58 / 0.5)'),(100,0,'rgb(23 36 58 / 0)')]:
            with self.subTest(transparency=transparency):
                s=self.s|{'background_mode':'Cor sólida','solid_color':'#17243A','solid_transparency':transparency}
                base,glass,_=render_wallpaper(s)
                self.assertEqual(base.pixelColor(10,10).alpha(),alpha)
                self.assertEqual(glass.pixelColor(10,10).alpha(),alpha)
                self.assertIn('--zss-background: '+css_color,build_css(s))
        save_mod(s)
        self.assertIn('--zss-background: rgb(23 36 58 / 0)',(self.profile/'chrome'/FILENAME).read_text())

    def test_transparency_defaults_validation_and_portable_presets(self):
        self.assertEqual(normalize({'version':2})['solid_transparency'],0)
        with self.assertRaises(ValueError):normalize(self.s|{'solid_transparency':float('nan')})
        with self.assertRaises(ValueError):normalize(self.s|{'solid_transparency':'50%'})
        s=self.s|{'background_mode':'Cor sólida','solid_transparency':65,'opacity':82}
        save_json(self.root/'settings.json',s)
        self.assertEqual(load_settings(self.root/'settings.json')['solid_transparency'],65)
        p=Presets(self.root/'presets.json');ident=p.add('Glass',s)
        p.export_preset(ident,self.root/'export.json')
        q=Presets(self.root/'other.json');new=q.import_preset(self.root/'export.json')
        self.assertEqual(q.get(new)['solid_transparency'],65)
        self.assertEqual(q.get(new)['opacity'],82)

    def test_colors_and_imported_settings_are_validated(self):
        for changes in [{'solid_color':'red'},{'solid_color':'#123456;}'},{'recent_colors':['white']},{'background_mode':'HTML'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):normalize(self.s|changes)
    def test_portable_preset_roundtrip_and_missing_images(self):
        p=Presets(self.root/'a.json');ident=p.add('Portable',self.s);target=self.root/'export.json'
        p.export_preset(ident,target);data=json.loads(target.read_text())
        self.assertEqual(data['settings']['profile'],'');self.assertEqual(data['settings']['image'],'')
        self.assertNotIn(str(self.root),target.read_text())
        self.image.unlink();q=Presets(self.root/'b.json');new=q.import_preset(target,self.root/'imported')
        self.assertTrue(Path(q.get(new)['image']).is_file())
        self.assertEqual(q.get(new)['profile'],'')
    def test_bad_preset_preserves_existing_data(self):
        p=Presets(self.root/'p.json');p.add('Keep',self.s)
        before=p.path.read_bytes();bad=self.root/'bad.json';bad.write_text('{"format":"unknown"}')
        with self.assertRaises(ValueError):p.import_preset(bad)
        self.assertEqual(p.path.read_bytes(),before)
    def test_solid_preset_needs_no_image(self):
        p=Presets(self.root/'p.json');ident=p.add('Solid',self.s|{'background_mode':'Cor sólida','image':''})
        p.export_preset(ident,self.root/'s.json');q=Presets(self.root/'q.json')
        imported=q.import_preset(self.root/'s.json');self.assertEqual(q.get(imported)['background_mode'],'Cor sólida')

class CandidateFlowTest(Fixture):
    def test_four_background_cases_apply_restore_disable_and_preserve_other_mods(self):
        from veil_for_zen.core.zen_integration import boolean_prefs,uses_native_backdrop
        for index,(scope,mode) in enumerate((('Barra lateral','Imagem'),('Navegador inteiro','Imagem'),('Barra lateral','Cor sólida'),('Navegador inteiro','Cor sólida'))):
            with self.subTest(scope=scope,mode=mode):
                case=self.root/str(index);profile=case/'profile';chrome=profile/'chrome';chrome.mkdir(parents=True)
                (profile/'prefs.js').write_text('// fictitious profile')
                original='@import "other-mod.css";\n/* user styles */\n'
                (chrome/'userChrome.css').write_text(original)
                (chrome/'other-mod.css').write_text('body { color: hotpink; }')
                userjs='user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\nuser_pref("unrelated.preference", true);\n'
                (profile/'user.js').write_text(userjs)
                state=self.s|{'profile':str(profile),'background_scope':scope,'background_mode':mode,'solid_transparency':70,'color_mode':'Personalizada','browser_width':960,'browser_height':600}
                settings=case/'settings.json';save_json(settings,state)
                w=Studio(settings,case/'presets.json');errors=[];w.error=errors.append;w.show()
                try:
                    w.apply.click();deadline=time.monotonic()+10
                    while w.working and time.monotonic()<deadline:app.processEvents();time.sleep(.005)
                    self.assertFalse(w.working);self.assertEqual(errors,[])
                    self.assertIn(IMPORT,(chrome/'userChrome.css').read_text())
                    first=Path(json.loads((backup_root(profile)/'latest.json').read_text())['backup'])
                    # Simulate preference persistence after a manual browser restart.
                    persisted=boolean_prefs((profile/'user.js').read_text())
                    (profile/'prefs.js').write_text('\n'.join(f'user_pref("{k}", {str(v).lower()});' for k,v in persisted.items()))
                    restore_backup(profile,first)
                    self.assertEqual((chrome/'userChrome.css').read_text(),original)
                    self.assertFalse((chrome/FILENAME).exists())
                    self.assertTrue((profile/'user.js').read_text().startswith(userjs))
                    if uses_native_backdrop(state):
                        self.assertFalse(boolean_prefs((profile/'user.js').read_text())['zen.widget.linux.transparency'])
                    save_mod(state);before_disable=(chrome/'userChrome.css').read_bytes()
                    disabled=disable_mod(profile)
                    self.assertNotIn(IMPORT,(chrome/'userChrome.css').read_text())
                    restore_backup(profile,disabled)
                    self.assertEqual((chrome/'userChrome.css').read_bytes(),before_disable)
                    disable_mod(profile)
                    self.assertEqual((chrome/'other-mod.css').read_text(),'body { color: hotpink; }')
                    self.assertIn(original,(chrome/'userChrome.css').read_text())
                finally:
                    w.library_timer.stop();w.preview.timer.stop();w.preview.pool.waitForDone();w.pool.waitForDone();app.processEvents()
                    w.saved=w.state.copy();w.close();app.processEvents()

class LibraryContrastTest(Fixture):
    def test_library_gets_its_own_dark_palette_and_protected_surface(self):
        for scope in ['Barra lateral','Navegador inteiro']:
            css=build_css(self.s|{'background_scope':scope,'background_mode':'Cor sólida','solid_transparency':100})
            self.assertIn('#main-window zen-library {',css)
            self.assertIn('--toolbar-color-scheme: dark !important;',css)
            self.assertIn('#main-window zen-library #zen-library-panel',css)
            self.assertIn('background: rgb(16 17 20 / 0.9)',css)
            self.assertIn('#main-window zen-library input::placeholder',css)

    def test_library_fix_preserves_native_visibility_and_favicons(self):
        from veil_for_zen.core.settings import ROOT
        css=(ROOT/'library.css').read_text()
        for forbidden in ['visibility:','display:','filter: invert(','.tab-icon-image',' img {','opacity: 1 !important;\n  }\n  #main-window zen-library']:
            self.assertNotIn(forbidden,css)
        self.assertIn('toolbarbutton:not([disabled])',css)

class BrowserControlsContrastTest(Fixture):
    def test_controls_colors_are_scoped_outside_titlebar_for_all_modes(self):
        for scope in ['Barra lateral','Navegador inteiro']:
            for mode in ['Imagem','Cor sólida']:
                css=build_css(self.s|{'background_scope':scope,'background_mode':mode,'solid_transparency':100},'file:///tmp/image.png')
                self.assertIn('--toolbox-textcolor: #f5f5f5 !important;',css)
                self.assertIn('#main-window #navigator-toolbox #urlbar-input::placeholder',css)
                self.assertIn('#main-window #navigator-toolbox #urlbar:not([breakout-extend]) .urlbar-background',css)
                self.assertIn('toolbarbutton:not([disabled]) > .toolbarbutton-icon',css)

    def test_icon_fix_does_not_recolor_favicons_or_unhide_controls(self):
        from veil_for_zen.core.settings import ROOT
        css=(ROOT/'controls.css').read_text()
        self.assertNotIn('.tab-icon-image',css)
        self.assertNotIn('visibility:',css);self.assertNotIn('display:',css)
        self.assertNotIn('brightness(',css);self.assertNotIn('invert(',css)
        self.assertIn('toolbarbutton:not([disabled])',css)

class BackdropCompatibilityTest(Fixture):
    def test_known_decorative_background_suppressed_only_when_veil_controls_backdrop(self):
        for s in [self.s|{'background_scope':'Navegador inteiro'},self.s|{'background_mode':'Cor sólida','solid_transparency':100}]:
            css=build_css(s,'file:///tmp/image.png')
            self.assertIn('@media -moz-pref("mod.sameerasw.zen_bg_img_enabled")',css)
            self.assertIn(':root#main-window:not([popup-window])::before',css)
        self.assertNotIn('mod.sameerasw.zen_bg_img_enabled',build_css(self.s,'file:///tmp/image.png'))

    def test_apply_keeps_other_mod_files_and_preferences_unchanged(self):
        chrome=self.profile/'chrome';chrome.mkdir()
        foreign=chrome/'other-mod.css';foreign.write_text('#main-window::before { background: url("wave.png"); }')
        prefs='user_pref("mod.sameerasw.zen_bg_img_enabled", true);\n'
        (self.profile/'prefs.js').write_text(prefs)
        backup=save_mod(self.s|{'background_mode':'Cor sólida','solid_transparency':100})
        self.assertEqual((self.profile/'prefs.js').read_text(),prefs)
        self.assertIn('wave.png',foreign.read_text())
        self.assertIn('mod.sameerasw.zen_bg_img_enabled',(chrome/FILENAME).read_text())
        restore_backup(self.profile,backup)
        self.assertEqual((self.profile/'prefs.js').read_text(),prefs)
        self.assertIn('wave.png',foreign.read_text())

class BackgroundScopeTest(Fixture):
    def test_legacy_default_and_validation(self):
        self.assertEqual(normalize({'version':2})['background_scope'],'Barra lateral')
        with self.assertRaises(ValueError):normalize(self.s|{'background_scope':'Unknown'})

    def test_full_css_targets_one_global_background(self):
        full=build_css(self.s|{'background_scope':'Navegador inteiro'},'file:///tmp/image.png')
        sidebar=build_css(self.s,'file:///tmp/image.png')
        self.assertIn('#main-window:not([popup-window]) #zen-browser-background::before',full)
        self.assertEqual(full.count('background: var(--zss-image)'),1)
        self.assertIn('#titlebar > #zen-toolbar-background::before',sidebar)
        self.assertNotIn('Veil full-window backdrop',sidebar)
        self.assertEqual(full.count('url("file:///tmp/image.png")'),1)
        self.assertNotIn('@-moz-document url("about:',full)
        self.assertEqual(full.count('{'),full.count('}'))

    def test_transparent_scope_has_no_forced_opaque_content_base(self):
        for scope in ['Barra lateral','Navegador inteiro']:
            css=build_css(self.s|{'background_scope':scope,'background_mode':'Cor sólida','solid_transparency':100})
            self.assertNotIn('background-color: var(--zen-colors-tertiary',css)
            self.assertIn('#zen-appcontent-wrapper',css)
            self.assertIn('--zss-background: rgb(',css)

    def test_full_render_geometry_and_bounded_solid_canvas(self):
        full=self.s|{'background_scope':'Navegador inteiro','browser_width':960,'browser_height':600}
        base,_,_=render_wallpaper(full)
        self.assertEqual((base.width(),base.height()),(960,600))
        solid=full|{'background_mode':'Cor sólida','browser_width':7680,'browser_height':4320}
        base,_,_=render_wallpaper(solid)
        self.assertLessEqual(max(base.width(),base.height()),1400)
        self.assertAlmostEqual(base.width()/base.height(),7680/4320,places=2)

    def test_full_image_apply_and_switch_back_restore_flags(self):
        from veil_for_zen.core.zen_integration import boolean_prefs
        save_mod(self.s|{'background_scope':'Navegador inteiro'})
        css=(self.profile/'chrome'/FILENAME).read_text()
        self.assertIn('Veil full-window backdrop',css)
        self.assertTrue(boolean_prefs((self.profile/'user.js').read_text())['browser.tabs.allow_transparent_browser'])
        save_mod(self.s)
        self.assertNotIn('Veil full-window backdrop',(self.profile/'chrome'/FILENAME).read_text())
        self.assertFalse(boolean_prefs((self.profile/'user.js').read_text())['browser.tabs.allow_transparent_browser'])

    def test_scope_and_dimensions_survive_portable_preset(self):
        p=Presets(self.root/'p.json')
        ident=p.add('Entire',self.s|{'background_scope':'Navegador inteiro','browser_width':1440,'browser_height':900})
        p.export_preset(ident,self.root/'export.json');q=Presets(self.root/'q.json')
        s=q.get(q.import_preset(self.root/'export.json'))
        self.assertEqual(s['background_scope'],'Navegador inteiro');self.assertEqual(s['browser_width'],1440)

class NativeTransparencyTest(Fixture):
    def solid(self):return self.s|{'background_mode':'Cor sólida','solid_transparency':70}

    def test_native_flags_enabled_only_after_explicit_apply(self):
        from veil_for_zen.core.zen_integration import boolean_prefs,TRANSPARENCY_PREFS
        original='// other mod\nuser_pref("unrelated.preference", true);\nuser_pref("zen.widget.linux.transparency", false);\n'
        (self.profile/'user.js').write_text(original)
        build_css(self.solid());self.assertEqual((self.profile/'user.js').read_text(),original)
        save_mod(self.solid());text=(self.profile/'user.js').read_text()
        self.assertTrue(text.startswith(original))
        for key in TRANSPARENCY_PREFS:self.assertTrue(boolean_prefs(text)[key])
        save_mod(self.solid());self.assertEqual((self.profile/'user.js').read_text(),text)

    def test_opaque_css_does_not_clear_native_background_layers(self):
        transparent=build_css(self.solid())
        self.assertIn('#zen-browser-background::before',transparent)
        self.assertIn('--zen-themed-toolbar-bg-transparent: transparent',transparent)
        self.assertIn('#zen-appcontent-wrapper',transparent)
        for s in [self.s,self.solid()|{'solid_transparency':0}]:
            self.assertNotIn('Veil native transparency',build_css(s,'file:///tmp/image.png'))

    def test_disable_restores_flags_even_after_zen_persisted_them(self):
        from veil_for_zen.core.zen_integration import boolean_prefs,TRANSPARENCY_PREFS
        save_mod(self.solid())
        (self.profile/'prefs.js').write_text('\n'.join(f'user_pref("{key}", true);' for key in TRANSPARENCY_PREFS))
        disable_mod(self.profile)
        prefs=boolean_prefs((self.profile/'user.js').read_text())
        for key in TRANSPARENCY_PREFS:self.assertFalse(prefs[key])

    def test_changing_back_to_image_restores_previous_flags(self):
        from veil_for_zen.core.zen_integration import boolean_prefs
        (self.profile/'prefs.js').write_text('user_pref("zen.widget.linux.transparency", true);')
        save_mod(self.solid());save_mod(self.s)
        prefs=boolean_prefs((self.profile/'user.js').read_text())
        self.assertTrue(prefs['zen.widget.linux.transparency'])
        self.assertFalse(prefs['browser.tabs.allow_transparent_browser'])

    def test_restore_resets_flags_and_preserves_external_userjs(self):
        from veil_for_zen.core.zen_integration import boolean_prefs
        original='// external style settings\nuser_pref("unrelated.preference", true);\n'
        (self.profile/'user.js').write_text(original)
        backup=save_mod(self.solid())
        (self.profile/'prefs.js').write_text('user_pref("zen.widget.linux.transparency", true);')
        restore_backup(self.profile,backup)
        text=(self.profile/'user.js').read_text();self.assertTrue(text.startswith(original))
        self.assertFalse(boolean_prefs(text)['zen.widget.linux.transparency'])
        self.assertFalse((self.profile/'chrome'/FILENAME).exists())

    def test_modified_preference_block_refused(self):
        save_mod(self.solid());path=self.profile/'user.js'
        text=path.read_text().replace('// Original: ', '// Original edited: ');path.write_text(text)
        with self.assertRaises(ValueError):disable_mod(self.profile)
        self.assertEqual(path.read_text(),text)

class TransactionRaceTest(Fixture):
    def test_external_edit_during_css_preparation_is_never_overwritten(self):
        from veil_for_zen.core.zen_integration import build_css as real_build_css
        chrome=self.profile/'chrome';chrome.mkdir();user=chrome/'userChrome.css';user.write_text('/* original */')
        edited='/* original */\n/* edited by another app during generation */'
        def edit_during_generation(*args):
            result=real_build_css(*args);user.write_text(edited);return result
        with patch('veil_for_zen.core.zen_integration.build_css',side_effect=edit_during_generation),self.assertRaises(ValueError):
            save_mod(self.s)
        self.assertEqual(user.read_text(),edited)

class SafeCssTest(Fixture):
    def test_applied_image_url_is_profile_relative(self):
        save_mod(self.s)
        css=(self.profile/'chrome'/FILENAME).read_text()
        self.assertIn('url("backgrounds/veil-',css)
        self.assertNotIn(str(self.root),css)

    def test_restore_recovers_exact_bytes_and_absent_files(self):
        chrome=self.profile/'chrome';chrome.mkdir();original=b'/* other */\n@import "other.css";\n'
        (chrome/'userChrome.css').write_bytes(original)
        backup=save_mod(self.s);restore_backup(self.profile,backup)
        self.assertEqual((chrome/'userChrome.css').read_bytes(),original)
        self.assertFalse((chrome/FILENAME).exists());self.assertFalse((self.profile/'user.js').exists())
    def test_restore_refuses_external_edits(self):
        backup=save_mod(self.s);user=self.profile/'chrome/userChrome.css';user.write_text(user.read_text()+'/* edited later */')
        with self.assertRaises(ValueError):restore_backup(self.profile,backup)
        self.assertIn('edited later',user.read_text())
    def test_apply_refuses_external_managed_css_edits(self):
        save_mod(self.s);target=self.profile/'chrome'/FILENAME;target.write_text(target.read_text()+'/* edit */')
        with self.assertRaises(ValueError):save_mod(self.s)
        self.assertTrue(target.read_text().endswith('/* edit */'))
    def test_disable_only_removes_owned_import(self):
        save_mod(self.s);user=self.profile/'chrome/userChrome.css'
        external='\n@import "other.css";\n/* @import url("veil-for-zen.css"); */\n#urlbar { color: red; }'
        user.write_text(user.read_text()+external);disable_mod(self.profile)
        self.assertTrue(user.read_text().endswith(external));self.assertNotIn(IMPORT,user.read_text().split(external)[0])
        disable_mod(self.profile);self.assertTrue(user.read_text().endswith(external))
    def test_import_variants_bom_charset_comments(self):
        text='\ufeff@charset "UTF-8";\n/* comment */\n@import "other.css";'
        merged=merge_import(text);self.assertTrue(merged.startswith('\ufeff@charset "UTF-8";'))
        self.assertEqual(merge_import(merged),merged)
        for variant in ['@import "veil-for-zen.css";',"@import url( 'veil-for-zen.css' );"]:
            self.assertEqual(merge_import(variant),variant);self.assertEqual(remove_import(variant),'')
    def test_disable_does_not_hide_external_css_edits(self):
        save_mod(self.s);target=self.profile/'chrome'/FILENAME
        target.write_text(target.read_text()+'/* external */')
        disable_mod(self.profile)
        with self.assertRaises(ValueError):save_mod(self.s)

    def test_css_rejects_injection_in_url(self):
        with self.assertRaises(ValueError):build_css(self.s,'file:///tmp/foo");body{color:red}')
    def test_symlink_profile_files_refused(self):
        chrome=self.profile/'chrome';chrome.mkdir();external=self.root/'external';external.write_text('keep')
        (chrome/'userChrome.css').symlink_to(external)
        with self.assertRaises(ValueError):save_mod(self.s)
        self.assertEqual(external.read_text(),'keep')
    def test_legacy_import_is_replaced_only_when_owned(self):
        chrome=self.profile/'chrome';chrome.mkdir();old=chrome/'zen-sidebar-studio-v2.css'
        old.write_text('/* Zen Sidebar Studio 2 - managed file */\nbody {}')
        user=chrome/'userChrome.css';original='@import "zen-sidebar-studio-v2.css";\n@import "other.css";';user.write_text(original)
        backup=save_mod(self.s);self.assertNotIn('@import "zen-sidebar-studio-v2.css";',user.read_text())
        self.assertTrue(old.exists());restore_backup(self.profile,backup);self.assertEqual(user.read_text(),original)
    def test_permission_failure_preserves_external_styles(self):
        chrome=self.profile/'chrome';chrome.mkdir();user=chrome/'userChrome.css';user.write_text('external')
        with patch('veil_for_zen.core.zen_integration.atomic_write',side_effect=PermissionError('denied')),self.assertRaises(PermissionError):save_mod(self.s)
        self.assertEqual(user.read_text(),'external');self.assertFalse((chrome/FILENAME).exists())

class PublicInterfaceTest(Fixture):
    def window(self):
        path=self.root/'settings.json';save_json(path,self.s|{'color_mode':'Personalizada'})
        w=Studio(path,self.root/'presets.json');w.show();app.processEvents()
        self.addCleanup(self.cleanup_window,w)
        return w
    def cleanup_window(self,w):
        w.library_timer.stop();w.preview.timer.stop();w.preview.pool.waitForDone();w.pool.waitForDone();app.processEvents()
        w.saved=w.state.copy();w.close();app.processEvents()
    def test_solid_mode_switch_keeps_image_and_controls(self):
        w=self.window();image=w.state['image'];w.change('background_mode','Cor sólida');app.processEvents()
        self.assertTrue(w.controls.solid_widget.isVisible());self.assertTrue(w.controls.gallery.isHidden())
        w.change('solid_color','#29171D');self.assertEqual(w.state['recent_colors'][0],'#29171D')
        w.change('background_mode','Imagem');self.assertEqual(w.state['image'],image);self.assertTrue(w.controls.solid_widget.isHidden())
    def test_transparency_control_is_independent_and_mode_specific(self):
        w=self.window();original_opacity=w.state['opacity']
        control=w.controls.inputs['solid_transparency']
        self.assertTrue(control.parentWidget().isHidden())
        w.change('background_mode','Cor sólida');app.processEvents()
        self.assertTrue(control.isVisible());control.setValue(55)
        self.assertEqual(w.state['solid_transparency'],55)
        self.assertEqual(w.state['opacity'],original_opacity)
        w.change('background_mode','Imagem');w.change('background_mode','Cor sólida')
        self.assertEqual(control.value(),55)

    def test_background_scope_updates_controls_and_preview(self):
        w=self.window();old_dimensions=(w.state['preview_width'],w.state['preview_height'])
        w.controls.inputs['background_scope'].setCurrentText('Navegador inteiro');app.processEvents()
        self.assertIn('Navegador inteiro',w.geometry_label.text())
        self.assertFalse(w.controls.inputs['browser_width'].parentWidget().isHidden())
        self.assertTrue(w.controls.inputs['preview_width'].parentWidget().isHidden())
        deadline=time.monotonic()+10
        while (w.preview.wallpaper is None or w.preview.running or w.preview.timer.isActive()) and time.monotonic()<deadline:
            app.processEvents();time.sleep(.005)
        self.assertFalse(w.grab().isNull())
        self.assertEqual(w.preview.wallpaper.width(),1280)
        w.change('background_scope','Barra lateral')
        self.assertEqual((w.state['preview_width'],w.state['preview_height']),old_dimensions)

    def test_responsive_splitter_and_four_sections(self):
        w=self.window()
        self.assertEqual([b.text() for b in w.controls.findChildren(QToolButton) if b.objectName()=='sectionTitle'],['Fundo','Abas','Efeitos','Avançado'])
        w.resize(600,740);app.processEvents();self.assertEqual(w.split.orientation(),Qt.Vertical)
        w.resize(1200,850);app.processEvents();self.assertEqual(w.split.orientation(),Qt.Horizontal)
        self.assertFalse(w.grab().isNull())
    def test_popup_has_contrast(self):
        w=self.window();combo=w.controls.inputs['sizing'];combo.showPopup();app.processEvents()
        palette=combo.view().palette()
        self.assertLess(palette.color(QPalette.Base).lightness(),80)
        self.assertGreater(palette.color(QPalette.Text).lightness(),180)
        combo.hidePopup()
    def test_job_callback_runs_on_gui_thread(self):
        w=self.window();threads=[];w.run_job(lambda:42,lambda result,error:threads.append(QThread.currentThread()))
        deadline=time.monotonic()+5
        while not threads and time.monotonic()<deadline:app.processEvents();time.sleep(.005)
        self.assertEqual(threads,[app.thread()])
    def test_progressive_gallery(self):
        library=self.root/'fn_zen';library.mkdir()
        for i in range(55):(library/f'{i}.png').write_bytes(self.image.read_bytes())
        w=self.window();deadline=time.monotonic()+10
        while w.library_busy and time.monotonic()<deadline:app.processEvents();time.sleep(.005)
        self.assertEqual(w.controls.gallery.count(),48)
        w.reload_library(True)
        while w.library_busy and time.monotonic()<deadline:app.processEvents();time.sleep(.005)
        self.assertEqual(w.controls.gallery.count(),55)

if __name__=='__main__':unittest.main()
