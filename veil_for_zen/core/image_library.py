"""Wallpaper library. Content detection supports images without extensions."""
import hashlib
import os
from pathlib import Path
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QImageReader,QImage
from .paths import cache_dir
from .settings import atomic_write


def scan_images(directory, limit=None, offset=0):
    directory=Path(directory)
    if not directory.exists():return []
    images=[]
    seen=0
    for path in sorted(directory.iterdir(),key=lambda p:(not p.stem.isdecimal(),int(p.stem) if p.stem.isdecimal() else p.name.casefold())):
        if not path.is_file() or path.name.startswith('.'):continue
        reader=QImageReader(str(path));reader.setAutoTransform(True)
        size=reader.size()
        if bytes(reader.format()).lower() not in (b'png',b'jpeg',b'jpg',b'webp',b'bmp') or not reader.canRead() or not size.isValid() or size.width()*size.height()>100_000_000:continue
        if seen<offset: seen+=1;continue
        if limit is not None and len(images)>=limit: break
        seen+=1
        stamp=path.stat()
        key=hashlib.sha256(f'{path.resolve()}:{stamp.st_mtime_ns}:{stamp.st_size}'.encode()).hexdigest()
        cached=cache_dir()/'thumbnails'/(key+'.png')
        thumb=QImage(str(cached)) if cached.is_file() else QImage()
        if thumb.isNull():
            reader.setScaledSize(size.scaled(QSize(90,100),Qt.KeepAspectRatio))
            thumb=reader.read()
            if not thumb.isNull():
                try:
                    from PySide6.QtCore import QBuffer,QIODevice
                    buffer=QBuffer();buffer.open(QIODevice.WriteOnly);thumb.save(buffer,'PNG')
                    atomic_write(cached,bytes(buffer.data()))
                except OSError: pass
        if not thumb.isNull():images.append((str(path.resolve()),thumb))
    return images


def import_image(source,directory):
    source=Path(source).expanduser().resolve();directory=Path(directory).resolve()
    from .zen_integration import validate_image
    validate_image(source)
    reader=QImageReader(str(source))
    size=reader.size()
    if not source.is_file() or not reader.canRead() or not size.isValid() or size.width()*size.height()>100_000_000:
        raise ValueError('Selecione uma imagem válida de até 100 megapixels.')
    if source.parent==directory:return str(source)
    directory.mkdir(parents=True,exist_ok=True)
    data=source.read_bytes();dest=directory/source.name
    if dest.is_symlink(): raise ValueError('Destino é um link simbólico.')
    if dest.exists():
        if dest.read_bytes()==data:return str(dest)
        dest=directory/(source.stem+'-'+hashlib.sha256(data).hexdigest()[:12]+source.suffix)
    try:
        with dest.open('xb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
    except FileExistsError:
        if dest.read_bytes()!=data:raise ValueError('Já existe outra imagem com esse nome na biblioteca.')
    return str(dest)
