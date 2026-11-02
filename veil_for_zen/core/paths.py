"""XDG directories. Importing this module never creates files."""
import os
from pathlib import Path

APP_ID = 'veil-for-zen'

def xdg(name, fallback):
    value = os.environ.get(name, '')
    return (Path(value) if value and Path(value).is_absolute() else Path.home()/fallback)/APP_ID

def config_dir(): return xdg('XDG_CONFIG_HOME', '.config')
def data_dir(): return xdg('XDG_DATA_HOME', '.local/share')
def cache_dir(): return xdg('XDG_CACHE_HOME', '.cache')
def settings_file(): return config_dir()/'settings.json'
def presets_file(): return data_dir()/'presets.json'
def library_dir(): return data_dir()/'images'
