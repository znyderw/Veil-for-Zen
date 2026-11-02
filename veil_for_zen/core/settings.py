"""Versioned settings and atomic persistence. No profile writes on import."""
import json
import math
import os
import tempfile
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from .paths import settings_file
PROFILE = ''
DEFAULTS = dict(version=2, profile=str(PROFILE),
    image='', background_scope='Barra lateral', browser_width=1280, browser_height=800, background_mode='Cor sólida', solid_color='#1B1D22', solid_transparency=0, recent_colors=[], opacity=100,
    blur=6, darkness=16, controls=4, shade=38, sizing='Largura', zoom=100,
    x=50, y=100, brightness=100, contrast=100, grayscale=0,
    preview_width=250, preview_height=900, dimension_mode='Manual', fit=True,
    color_mode='Automática', palette=['#79566a', '#53678b', '#577363', '#777981'],
    accent_index=0, tab_style='Combinado', intensity=30)

RANGES = dict(browser_width=(480,7680), browser_height=(320,4320), solid_transparency=(0,100), opacity=(0,100), blur=(0,150), darkness=(0,100), controls=(0,20),
    shade=(0,100), zoom=(20,300), x=(0,100), y=(0,100), brightness=(20,200),
    contrast=(20,200), grayscale=(0,100), preview_width=(100,1000),
    preview_height=(240,3000), intensity=(0,100), accent_index=(0,3))
CHOICES = dict(background_scope=['Barra lateral','Navegador inteiro'], sizing=['Largura','Conter','Preencher','Esticar'],
    dimension_mode=['Manual','Automático'], color_mode=['Automática','Personalizada'],
    tab_style=['Bordas discretas','Preenchimento suave','Combinado'])


def normalize(data):
    if not isinstance(data, dict):
        raise ValueError('As configurações devem ser um objeto JSON.')
    if data.get('version', 1) not in (1, 2):
        raise ValueError('Configuração de uma versão incompatível do Veil.')
    s = deepcopy(DEFAULTS)
    s.update({k:v for k,v in data.items() if k in DEFAULTS})
    if 'background_mode' not in data and data.get('image'): s['background_mode']='Imagem'
    for key, (lo, hi) in RANGES.items():
        value = s[key]
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
            raise ValueError(f'Valor inválido para {key}.')
        s[key] = max(lo, min(hi, round(value)))
    for key, choices in CHOICES.items():
        if s[key] not in choices:
            raise ValueError(f'Opção inválida para {key}.')
    import re
    if not isinstance(s['palette'], list) or not 1 <= len(s['palette']) <= 4:
        raise ValueError('A paleta deve ter entre uma e quatro cores.')
    if not all(isinstance(c,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',c) for c in s['palette']):
        raise ValueError('As cores da paleta precisam usar o formato #RRGGBB.')
    s['accent_index'] = min(s['accent_index'],len(s['palette'])-1)
    if s['background_mode'] not in ['Imagem', 'Cor sólida']:
        raise ValueError('Modo de fundo inválido.')
    if not isinstance(s['solid_color'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', s['solid_color']):
        raise ValueError('Cor sólida inválida: use #RRGGBB.')
    if not isinstance(s['recent_colors'], list) or len(s['recent_colors']) > 12 or not all(isinstance(c,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',c) for c in s['recent_colors']):
        raise ValueError('Cores recentes inválidas.')
    for key in ['image','profile']:
        if s[key] == '': continue

        if not isinstance(s[key], str) or not s[key] or '\x00' in s[key]:
            raise ValueError(f'Caminho inválido: {key}.')
        s[key] = str(Path(s[key]).expanduser().absolute())
    if not isinstance(s['fit'],bool):
        raise ValueError('Opção de ajuste à janela inválida.')
    s['version'] = 2
    return s


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data.encode('utf-8') if isinstance(data,str) else data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def save_json(path, data):
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def load_settings(path=None):
    path = path or settings_file()
    path = Path(path)
    if not path.exists():
        return deepcopy(DEFAULTS)
    try:
        return normalize(json.loads(path.read_text()))
    except (ValueError, TypeError) as exc:
        raise ValueError(f'Não foi possível ler {path.name}: {exc}') from exc


def preview_dimensions(settings):
    if settings['background_scope']=='Navegador inteiro':
        return settings['browser_width'],settings['browser_height']
    return settings['preview_width'],settings['preview_height']
