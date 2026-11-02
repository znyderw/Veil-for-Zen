"""Scoped, reversible profile writes. No browser process is stopped."""
import hashlib
import json
import re
import subprocess
import fcntl
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtGui import QImageReader
from .settings import ROOT, PROFILE, normalize, atomic_write, save_json
from .paths import data_dir
from .profiles import check_writable
from .color_extractor import tab_paint

MARKER='/* Veil for Zen - managed file */'
FILENAME='veil-for-zen.css'
IMPORT='@import url("veil-for-zen.css");'
PREF_BLOCK='// BEGIN Veil for Zen\nuser_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\n// END Veil for Zen\n'


TRANSPARENCY_PREFS=('zen.widget.linux.transparency','browser.tabs.allow_transparent_browser')
TRANS_START='// BEGIN Veil for Zen transparency'
TRANS_END='// END Veil for Zen transparency'
TRANS_PATTERN=re.compile(r'(?m)^'+re.escape(TRANS_START)+r'\n.*?^'+re.escape(TRANS_END)+r'\n?',re.S)


def boolean_prefs(text):
    active=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
    return {key:value=='true' for key,value in re.findall(r'user_pref\(\s*["\']([^"\']+)["\']\s*,\s*(true|false)\s*\)',active)}


def transparency_block(original, values):
    metadata='// Original: '+json.dumps(original,sort_keys=True)
    lines=[f'user_pref("{key}", {str(values[key]).lower()});' for key in TRANSPARENCY_PREFS]
    return TRANS_START+'\n'+metadata+'\n'+'\n'.join(lines)+'\n'+TRANS_END+'\n'


def update_transparency_prefs(text,prefs,enabled):
    blocks=list(TRANS_PATTERN.finditer(text))
    if len(blocks)>1 or text.count(TRANS_START)!=len(blocks) or text.count(TRANS_END)!=len(blocks):
        raise ValueError('Bloco de transparência alterado externamente; user.js foi preservado.')
    outside=TRANS_PATTERN.sub('',text)
    if blocks:
        block=blocks[0].group()
        try: original=json.loads(block.splitlines()[1].removeprefix('// Original: '))
        except (ValueError,IndexError): raise ValueError('Metadados da transparência inválidos; user.js preservado.')
        if set(original)!=set(TRANSPARENCY_PREFS) or any(type(v) is not bool for v in original.values()):
            raise ValueError('Preferências originais inválidas; user.js preservado.')
        if block not in [transparency_block(original,original),transparency_block(original,dict.fromkeys(TRANSPARENCY_PREFS,True))]:
            raise ValueError('Bloco de transparência editado externamente; user.js preservado.')
    else:
        if not enabled:return text
        current=boolean_prefs(prefs+'\n'+outside)
        original={key:current.get(key,False) for key in TRANSPARENCY_PREFS}
        if all(original.values()):return text
    values=dict.fromkeys(TRANSPARENCY_PREFS,True) if enabled else original.copy()
    if not enabled:
        # Honor explicit external user.js preferences changed since first apply.
        external=boolean_prefs(outside)
        values.update({key:external[key] for key in TRANSPARENCY_PREFS if key in external})
        original=values.copy()
    # Keep reset overrides: Firefox persists preferences in prefs.js on exit.
    block=transparency_block(original,values)
    return outside+('' if not outside or outside.endswith('\n') else '\n')+block


def validate_image(path):
    path=Path(path).expanduser()
    if not path.is_file(): raise ValueError('A imagem não existe. Selecione outro arquivo.')
    reader=QImageReader(str(path)); reader.setAutoTransform(True)
    size=reader.size()
    if bytes(reader.format()).lower() not in (b'png',b'jpeg',b'jpg',b'webp',b'bmp'):
        raise ValueError('Use uma imagem PNG, JPEG, WebP ou BMP.')
    if not size.isValid() or size.width()*size.height()>100_000_000:
        raise ValueError('Imagem inválida ou grande demais (limite de 100 megapixels).')
    if reader.read().isNull(): raise ValueError('O arquivo não contém uma imagem compatível.')
    return path.resolve()


def variables(s,image_url):
    s=normalize(s)
    solid=s['background_mode']=='Cor sólida'
    if not solid and ((not image_url.startswith('file:') and not re.fullmatch(r'backgrounds/veil-[0-9a-f]{20}\.[a-z]+',image_url)) or any(c in image_url for c in '\n\r"{};')):
        raise ValueError('URL de imagem inválida.')
    color=s['solid_color']
    if solid and s['solid_transparency']:
        r,g,b=(int(color[i:i+2],16) for i in (1,3,5))
        color=f'rgb({r} {g} {b} / {1-s["solid_transparency"]/100:g})'
    return dict(image='none' if solid else f'url("{image_url}")',
        background=color if solid else '#050505',
        opacity='0' if solid else f'{s["opacity"]/100:g}',
        blur='0px' if solid else f'{s["blur"]/10:g}px',
        darkness='0' if solid else f'{s["darkness"]/100:g}',controls=f'{s["controls"]}px',
        size={'Largura':f'{s["zoom"]}% auto','Conter':'contain','Preencher':'cover','Esticar':'100% 100%'}[s['sizing']],
        position=f'{s["x"]}% {s["y"]}%',
        effects=f'brightness({s["brightness"]}%) contrast({s["contrast"]}%) grayscale({s["grayscale"]}%)')


def rgba(color):
    r,g,b,a=color
    return f'rgb({r} {g} {b} / {a/255:.6f})'


def uses_native_backdrop(s):
    return s['background_scope']=='Navegador inteiro' or (s['background_mode']=='Cor sólida' and s['solid_transparency']>0)


def build_css(s,image_url=''):
    s=normalize(s); values=variables(s,image_url)
    for state in ['normal','hover','selected']:
        for kind,value in tab_paint(s,state).items(): values[f'{state}-{kind}']=rgba(value)
    declarations='\n'.join(f'    --zss-{k}: {v} !important;' for k,v in values.items())
    template=(ROOT/'chrome.css').read_text()
    if s['background_scope']=='Navegador inteiro':
        template=template.replace('#main-window #navigator-toolbox #titlebar > #zen-toolbar-background', '#main-window:not([popup-window]) #zen-browser-background')
    css=MARKER+'\n'+template.replace('/* SETTINGS */',declarations)
    if s['background_scope']=='Navegador inteiro':
        css+='\n'+(ROOT/'full-browser.css').read_text()
    elif s['background_mode']=='Cor sólida' and s['solid_transparency']>0:
        css+='\n'+(ROOT/'transparency.css').read_text()
    css+='\n'+(ROOT/'controls.css').read_text()
    css+='\n'+(ROOT/'library.css').read_text()
    if uses_native_backdrop(s):
        css+='\n'+(ROOT/'compatibility.css').read_text()
    if css.count('{')!=css.count('}') or '/* SETTINGS */' in css: raise ValueError('CSS inválido.')
    return css


def import_spans(text, filename=FILENAME):
    # Mask comments without changing offsets: commented imports are never activated/removed.
    active=re.sub(r'/\*.*?\*/',lambda m:' '*len(m.group()),text,flags=re.S)
    pattern=r'@import\s+(?:url\(\s*["\']?'+re.escape(filename)+r'["\']?\s*\)|["\']'+re.escape(filename)+r'["\'])\s*;'
    return [m.span() for m in re.finditer(pattern,active,re.I)]


def remove_import(text, filename=FILENAME):
    for start,end in reversed(import_spans(text,filename)): text=text[:start]+text[end:]
    return text


def merge_import(text):
    if import_spans(text): return text
    charset=re.match(r'\ufeff?\s*@charset\s+["\'][^"\']+["\'];',text,re.I)
    offset=charset.end() if charset else (1 if text.startswith('\ufeff') else 0)
    return text[:offset]+'\n'+IMPORT+'\n'+text[offset:]


def digest(content): return hashlib.sha256(content).hexdigest() if content is not None else None

def backup_root(profile):
    return data_dir()/'backups'/hashlib.sha256(str(profile).encode()).hexdigest()[:20]


def safe_paths(profile):
    profile=check_writable(profile)
    for directory in [profile/'chrome', profile/'chrome/backgrounds']:
        if directory.is_symlink(): raise ValueError('Pasta de estilos é link simbólico; operação recusada.')
    paths=[profile/'chrome'/FILENAME,profile/'chrome/userChrome.css',profile/'user.js']
    for path in paths:
        if path.is_symlink(): raise ValueError(f'{path.name} é link simbólico; operação recusada.')
    return profile,paths


@contextmanager
def locked(profile):
    root=backup_root(profile);root.mkdir(parents=True,exist_ok=True)
    with (root/'operation.lock').open('a') as stream:
        try: fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('Outra operação do Veil está em andamento neste perfil.')
        try: yield root
        finally: fcntl.flock(stream,fcntl.LOCK_UN)


def transaction(profile, changes, operation, settings=None, expected=None):
    old={p:p.read_bytes() if p.exists() else None for p in changes}
    if expected is not None and any(old[p]!=expected[p] for p in changes):
        raise ValueError('Arquivo alterado externamente durante a preparação; nenhuma alteração foi aplicada.')
    root=backup_root(profile)
    backup=root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
    files=[]
    for index,(path,content) in enumerate(old.items()):
        name=f'{index}.before'
        if content is not None: atomic_write(backup/name,content)
        files.append({'path':str(path.relative_to(profile)), 'before':name if content is not None else None,
                      'before_hash':digest(content),'after_hash':digest(changes[path])})
    manifest={'profile':str(profile),'operation':operation,'files':files}
    save_json(backup/'manifest.json',manifest)
    if settings is not None: save_json(backup/'settings.json',settings)
    written=[]
    try:
        for path,content in changes.items():
            current=path.read_bytes() if path.exists() else None
            if current!=old[path]: raise ValueError('Arquivo alterado externamente durante a operação: '+path.name)
            if path.is_symlink(): raise ValueError('Destino tornou-se link simbólico.')
            if content is None: path.unlink(missing_ok=True)
            else: atomic_write(path,content)
            written.append(path)
        latest=root/'latest.json'
        previous=json.loads(latest.read_text()) if latest.exists() else {}
        managed=profile/'chrome'/FILENAME
        managed_hash=digest(changes[managed]) if managed in changes else previous.get('managed_hash',digest(managed.read_bytes() if managed.exists() else None))
        save_json(latest,{'backup':str(backup),'managed_hash':managed_hash})
    except Exception:
        for path in reversed(written):
            current=path.read_bytes() if path.exists() else None
            if current!=changes[path]: continue  # Never overwrite an external edit during rollback.
            if old[path] is None: path.unlink(missing_ok=True)
            else: atomic_write(path,old[path])
        raise
    return backup


def save_mod(settings,profile=None):
    s=normalize(settings)
    source=validate_image(s['image']) if s['background_mode']=='Imagem' else None
    profile,paths=safe_paths(profile or s['profile']);target,user,userjs=paths
    with locked(profile):
        expected={p:p.read_bytes() if p.exists() else None for p in paths}
        if target.exists() and not target.read_text().startswith(MARKER):
            raise ValueError('Arquivo CSS de outra origem preservado.')
        # Detect edits to our managed CSS after the last successful operation.
        latest=backup_root(profile)/'latest.json'
        if latest.exists():
            expected_hash=json.loads(latest.read_text()).get('managed_hash')
            if digest(target.read_bytes() if target.exists() else None)!=expected_hash:
                raise ValueError('O CSS gerenciado foi alterado externamente. Preserve ou recupere a edição antes de aplicar.')
        text=(expected[user] or b'').decode('utf-8')
        legacy=profile/'chrome/zen-sidebar-studio-v2.css'
        if legacy.is_file() and legacy.read_text().startswith('/* Zen Sidebar Studio 2 - managed file */'):
            text=remove_import(text,'zen-sidebar-studio-v2.css')
        changes={}
        image_url=''
        if source:
            # Content-addressed copy: the browser can read it even in Flatpak.
            content=source.read_bytes()
            suffix=QImageReader(str(source)).format().data().decode('ascii')
            asset=profile/'chrome/backgrounds'/('veil-'+hashlib.sha256(content).hexdigest()[:20]+'.'+suffix)
            if asset.is_symlink(): raise ValueError('Destino da imagem é link simbólico.')
            asset_before=asset.read_bytes() if asset.exists() else None
            if asset_before is not None and asset_before!=content: raise ValueError('Imagem gerenciada alterada externamente.')
            expected[asset]=asset_before
            changes[asset]=content;image_url=asset.relative_to(profile/'chrome').as_posix()
        css=build_css(s,image_url)
        merged=merge_import(text)
        usertext=(expected[userjs] or b'').decode('utf-8')
        pref='toolkit.legacyUserProfileCustomizations.stylesheets'
        prefs=(profile/'prefs.js').read_text()+'\n'+usertext
        enabled=re.findall(r'user_pref\(\s*["\']'+re.escape(pref)+r'["\']\s*,\s*(true|false)\s*\)',re.sub(r'/\*.*?\*/|//[^\n]*','',prefs,flags=re.S))
        if not enabled or enabled[-1]!='true':
            usertext=usertext.replace(PREF_BLOCK,'')+'\n'+PREF_BLOCK
        usertext=update_transparency_prefs(usertext,(profile/'prefs.js').read_text(),uses_native_backdrop(s))
        changes.update({target:css.encode(),user:merged.encode(),userjs:usertext.encode()})
        return transaction(profile,changes,'apply',s,expected=expected)


def disable_mod(profile):
    profile,paths=safe_paths(profile);target,user,userjs=paths
    with locked(profile):
        expected={p:p.read_bytes() if p.exists() else None for p in paths}
        changes={}
        if expected[user] is not None: changes[user]=remove_import(expected[user].decode('utf-8')).encode()
        if userjs.exists():
            changes[userjs]=update_transparency_prefs(expected[userjs].decode('utf-8'),(profile/'prefs.js').read_text(),False).encode()
        # Keep the stylesheets preference enabled: another mod may now rely on it.
        return transaction(profile,changes,'disable',expected=expected)


def restore_backup(profile, backup=None):
    profile,paths=safe_paths(profile)
    with locked(profile):
        root=backup_root(profile)
        backup=Path(backup or json.loads((root/'latest.json').read_text())['backup']).resolve()
        if backup.parent!=root.resolve(): raise ValueError('Backup não pertence ao perfil selecionado.')
        manifest=json.loads((backup/'manifest.json').read_text())
        if manifest['profile']!=str(profile): raise ValueError('Perfil do backup não corresponde ao selecionado.')
        changes={};expected={}
        for record in manifest['files']:
            relative=Path(record['path'])
            allowed=str(relative) in ('chrome/'+FILENAME,'chrome/userChrome.css','user.js') or bool(re.fullmatch(r'chrome/backgrounds/veil-[0-9a-f]{20}\.[a-z]+',str(relative)))
            if relative.is_absolute() or '..' in relative.parts or not allowed: raise ValueError('Caminho inválido no backup.')
            if record['before'] is not None and not re.fullmatch(r'\d+\.before',record['before']): raise ValueError('Arquivo de backup inválido.')
            path=profile/relative
            current=path.read_bytes() if path.exists() else None
            if path.is_symlink() or digest(current)!=record['after_hash']:
                raise ValueError('Restauração recusada: arquivo alterado após o backup: '+path.name)
            content=(backup/record['before']).read_bytes() if record['before'] else None
            if digest(content)!=record['before_hash']: raise ValueError('Backup corrompido.')
            changes[path]=content;expected[path]=current
        userjs=profile/'user.js'
        if userjs in changes and userjs.exists():
            current=(expected[userjs] or b'').decode();restored=(changes[userjs] or b'').decode()
            if TRANS_PATTERN.search(current) and not TRANS_PATTERN.search(restored):
                reset=update_transparency_prefs(current,(profile/'prefs.js').read_text(),False)
                # Restore the previous effective values even after Zen persisted our flags.
                block=TRANS_PATTERN.search(reset).group()
                changes[userjs]=(restored+('' if not restored or restored.endswith('\n') else '\n')+block).encode()
        return transaction(profile,changes,'restore',expected=expected)


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
