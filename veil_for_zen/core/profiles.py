"""Read-only Zen profile discovery, including profiles.ini custom paths."""
import configparser
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Profile:
    path: Path
    name: str
    default: bool = False
    source: str = 'native'


def valid_profile(path):
    return Path(path).is_dir() and (Path(path)/'prefs.js').is_file()


def profile_roots(home=None):
    home = Path(home or Path.home())
    config = Path(os.environ.get('XDG_CONFIG_HOME', home/'.config'))
    if not config.is_absolute(): config = home/'.config'
    return [(config/'zen', 'native'), (home/'.config/zen', 'native'), (home/'.zen', 'native'),
            (home/'.var/app/app.zen_browser.zen/.zen', 'flatpak'),
            (home/'.var/app/app.zen_browser.zen/config/zen', 'flatpak'),
            (home/'.var/app/io.github.zen_browser.zen/.zen', 'flatpak')]


def discover_profiles(home=None, roots=None):
    found = {}
    for root, source in roots if roots is not None else profile_roots(home):
        root = Path(root)
        parser = configparser.ConfigParser(interpolation=None)
        try:
            with (root/'profiles.ini').open(encoding='utf-8-sig') as stream: parser.read_file(stream)
            defaults = {parser[s].get('Default') for s in parser if s.startswith('Install')}
            for section in parser:
                if not section.startswith('Profile'): continue
                entry = parser[section]; raw = entry.get('Path', '')
                if not raw: continue
                path = (root/raw if entry.get('IsRelative', '1') == '1' else Path(raw).expanduser()).resolve()
                if valid_profile(path):
                    found[path] = Profile(path, entry.get('Name', path.name), entry.get('Default') == '1' or raw in defaults, source)
        except (OSError, ValueError, configparser.Error): pass
        # Also recognize valid profiles when profiles.ini is missing or corrupt.
        try:
            for path in root.iterdir():
                if valid_profile(path) and path.resolve() not in found:
                    found[path.resolve()] = Profile(path.resolve(), path.name, False, source)
        except OSError: pass
    return sorted(found.values(), key=lambda p: (not p.default, p.name.casefold(), str(p.path)))


def check_writable(path):
    path = Path(path)
    if not valid_profile(path): raise ValueError('Escolha um perfil do Zen com prefs.js (veja about:profiles).')
    if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        raise PermissionError('Sem permissão de leitura e escrita no perfil selecionado.')
    return path.resolve()
