"""Read-only discovery; transactional, scoped CSS installation on explicit apply."""
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from PySide6.QtGui import QImageReader
from .settings import ROOT, PROFILE, normalize, atomic_write, save_json
from .color_extractor import tab_paint

MARKER='/* Zen Sidebar Studio 2 - managed file */'
IMPORT='@import url("zen-sidebar-studio-v2.css");'


def validate_image(path):
    path=Path(path).expanduser()
    if not path.is_file(): raise ValueError('A imagem não existe. Selecione outro arquivo.')
    reader=QImageReader(str(path)); reader.setAutoTransform(True)
    size=reader.size()
    if not size.isValid() or size.width()*size.height()>100_000_000:
        raise ValueError('Imagem inválida ou grande demais (limite de 100 megapixels).')
    if reader.read().isNull(): raise ValueError('O arquivo não contém uma imagem compatível.')
    return path.resolve()


def variables(s,image_url):
    s=normalize(s)
    return dict(image=f'url("{image_url}")',opacity=f'{s["opacity"]/100:g}',
        blur=f'{s["blur"]/10:g}px',darkness=f'{s["darkness"]/100:g}',controls=f'{s["controls"]}px',
        size={'Largura':f'{s["zoom"]}% auto','Conter':'contain','Preencher':'cover','Esticar':'100% 100%'}[s['sizing']],
        position=f'{s["x"]}% {s["y"]}%',
        effects=f'brightness({s["brightness"]}%) contrast({s["contrast"]}%) grayscale({s["grayscale"]}%)')


def rgba(color):
    r,g,b,a=color
    return f'rgb({r} {g} {b} / {a/255:.6f})'


def build_css(s,image_url):
    s=normalize(s); values=variables(s,image_url)
    for state in ['normal','hover','selected']:
        for kind,value in tab_paint(s,state).items(): values[f'{state}-{kind}']=rgba(value)
    declarations='\n'.join(f'    --zss-{k}: {v} !important;' for k,v in values.items())
    return MARKER+'\n'+(ROOT/'chrome.css').read_text().replace('/* SETTINGS */',declarations)


def merge_import(text):
    active=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    if re.search(r'@import\s+(?:url\(\s*[\"\']?zen-sidebar-studio-v2\.css[\"\']?\s*\)|[\"\']zen-sidebar-studio-v2\.css[\"\'])\s*;',active,re.I): return text
    charset=re.match(r'\ufeff?\s*@charset\s+[\"\'][^\"\']+[\"\'];',text,re.I)
    offset=charset.end() if charset else (1 if text.startswith('\ufeff') else 0)
    return text[:offset]+'\n'+IMPORT+'\n'+text[offset:]


def save_mod(settings,profile=None):
    s=normalize(settings); source=validate_image(s['image'])
    profile=Path(profile or s['profile']).expanduser().resolve()
    if not (profile/'prefs.js').is_file(): raise ValueError('Selecione uma pasta de perfil válida do Zen (com prefs.js).')
    chrome=profile/'chrome'
    if chrome.is_symlink() or (chrome/'backgrounds').is_symlink():
        raise ValueError('A pasta chrome ou backgrounds é um link simbólico. Nenhuma alteração foi aplicada.')
    chrome.mkdir(exist_ok=True)
    target=chrome/'zen-sidebar-studio-v2.css'; user=chrome/'userChrome.css'; userjs=profile/'user.js'
    for f in [target,user,userjs]:
        if f.is_symlink(): raise ValueError(f'{f.name} é um link simbólico; escolha um perfil sem links nesses arquivos.')
    if target.exists() and not target.read_text().startswith(MARKER):
        raise ValueError('Já existe um zen-sidebar-studio-v2.css de outra origem. Ele foi preservado.')
    reader=QImageReader(str(source)); reader.setAutoTransform(True); image=reader.read()
    from PySide6.QtCore import QBuffer,QIODevice
    buffer=QBuffer();buffer.open(QIODevice.WriteOnly);image.save(buffer,'PNG'); data=bytes(buffer.data())
    asset=chrome/'backgrounds'/('zss-'+hashlib.sha256(data).hexdigest()[:20]+'.png')
    old={f:f.read_bytes() if f.exists() else None for f in [target,user,userjs]}
    text=(old[user] or b'').decode('utf-8'); css=build_css(s,asset.as_uri()); merged=merge_import(text)
    userjs_text=(old[userjs] or b'').decode('utf-8')
    pref='toolkit.legacyUserProfileCustomizations.stylesheets'
    enabled=re.findall(r'user_pref\("'+re.escape(pref)+r'",\s*(true|false)\s*\)',(profile/'prefs.js').read_text()+'\n'+userjs_text)
    enable_styles=not enabled or enabled[-1]!='true'
    if enable_styles:
        userjs_text+='\n// Zen Sidebar Studio 2: habilitar estilos locais\nuser_pref("'+pref+'", true);\n'
    backup=profile/'sidebar-studio-backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); backup.mkdir(parents=True)
    for f,content in old.items():
        if content is not None: atomic_write(backup/f.name,content)
    save_json(backup/'studio-settings.json',s)
    try:
        if asset.is_symlink(): raise ValueError('O destino da imagem é um link simbólico.')
        if not asset.exists(): atomic_write(asset,data)
        atomic_write(target,css)
        if merged!=text: atomic_write(user,merged)
        if enable_styles: atomic_write(userjs,userjs_text)
    except Exception:
        for f,content in old.items():
            if content is None: f.unlink(missing_ok=True)
            else: atomic_write(f,content)
        raise
    return backup


def detect_dimensions(profile=PROFILE):
    """No DOM bridge: hints only; an external window is never the sidebar."""
    result={'exact':False,'saved_width':None,'window':None}
    try:
        data=json.loads((Path(profile)/'xulstore.json').read_text())
        item=data['chrome://browser/content/browser.xhtml']['navigator-toolbox']
        width=re.fullmatch(r'(\d+(?:\.\d+)?)px',item.get('width',''))
        if width: result['saved_width']=float(width.group(1))
    except (OSError,ValueError,KeyError,TypeError): pass
    try:
        run=subprocess.run(['hyprctl','-j','clients'],capture_output=True,text=True,timeout=2)
        if run.returncode==0:
            clients=json.loads(run.stdout)
            zen=[c for c in clients if 'zen' in str(c.get('class','')).lower()]
            if zen: result['window']=zen[0].get('size')
    except (OSError,ValueError,subprocess.TimeoutExpired,TypeError): pass
    hint=f'Largura salva do toolbox: {result["saved_width"]:g}px (pode estar desatualizada).' if result['saved_width'] else 'Nenhuma largura interna persistida encontrada.'
    result['message']='Detecção exata indisponível sem acesso ao DOM do Zen. '+hint+' Use largura e altura manuais da área de fundo.'
    if result['window']: result['message']+=' Janela externa detectada; suas medidas não foram usadas como medidas da barra.'
    return result
