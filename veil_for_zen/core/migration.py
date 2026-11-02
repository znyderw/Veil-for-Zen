"""Explicit, copy-only migration. Originals are never changed."""
import json
import shutil
from pathlib import Path
from .paths import config_dir, data_dir, settings_file, presets_file, library_dir
from .settings import normalize, save_json
from .image_library import import_image


def legacy_candidates():
    return [Path(__file__).resolve().parents[2],
            Path.home()/'Projects/zen-sidebar-studio',
            Path.home()/'.config/zen-sidebar-studio']


def find_legacy():
    return next((p for p in legacy_candidates() if (p/'settings.json').is_file()), None)


def migrate(source):
    source = Path(source)
    if settings_file().exists() or presets_file().exists():
        raise ValueError('Já existem dados do Veil. Migração recusada para preservar os arquivos atuais.')
    config_dir().mkdir(parents=True, exist_ok=True)
    data_dir().mkdir(parents=True, exist_ok=True)
    def legacy_settings(data):
        if isinstance(data,dict) and data.get('image') and not Path(data['image']).is_absolute():
            data=dict(data,image=str(source/data['image']))
        return normalize(data)
    settings = legacy_settings(json.loads((source/'settings.json').read_text()))
    raw = json.loads((source/'presets.json').read_text()) if (source/'presets.json').exists() else {'presets': [], 'history': []}
    # Validate everything before copying or publishing the new settings.
    from .presets import Presets
    if (source/'presets.json').exists(): Presets(source/'presets.json')
    copied = {}
    def copy_image(value):
        if not value: return value
        path = Path(value)
        if not path.is_absolute(): path = source/path
        if not path.is_file(): return str(path)
        if str(path) not in copied: copied[str(path)] = import_image(path, library_dir())
        return copied[str(path)]
    library = source/'fn_zen'
    if library.is_dir():
        for image in library.iterdir():
            if image.is_file():
                try: copy_image(str(image))
                except ValueError: pass
    settings['image'] = copy_image(settings['image'])
    for key in ('presets','history'):
        for item in raw[key]:
            item['settings'] = legacy_settings(item['settings'])
            item['settings']['image'] = copy_image(item['settings']['image'])
    # Keep an independent original-data snapshot for manual recovery.
    backup = data_dir()/'migration-original'
    backup.mkdir(exist_ok=True)
    for name in ('settings.json','presets.json'):
        if (source/name).exists(): shutil.copy2(source/name, backup/name)
    save_json(presets_file(), raw)
    try: save_json(settings_file(), settings)
    except Exception:
        presets_file().unlink(missing_ok=True)
        raise
    return settings
