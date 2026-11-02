"""CSS background geometry and raster effects, safe to run in a worker thread."""
import math
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QImageReader, QPainter, QColor
from .color_extractor import extract_palette
from .settings import preview_dimensions


def background_rect(iw,ih,w,h,s):
    if s['sizing']=='Esticar': rw,rh=w,h
    else:
        scale={'Largura':w/iw*s['zoom']/100,'Conter':min(w/iw,h/ih),'Preencher':max(w/iw,h/ih)}[s['sizing']]
        rw,rh=iw*scale,ih*scale
    # CSS percentages resolve against the remaining space, including negative space.
    return QRectF((w-rw)*s['x']/100,(h-rh)*s['y']/100,rw,rh)


@lru_cache(maxsize=3)
def load_image(path,mtime):
    reader=QImageReader(path);reader.setAutoTransform(True)
    size=reader.size()
    if not size.isValid() or size.width()*size.height()>100_000_000:
        raise ValueError('Imagem inválida ou maior que 100 megapixels.')
    if max(size.width(),size.height())>2400:
        reader.setScaledSize(size.scaled(2400,2400,Qt.KeepAspectRatio))
    img=reader.read()
    if img.isNull(): raise ValueError('Não foi possível abrir a imagem selecionada.')
    return img,extract_palette(img)


def gaussian(image,sigma):
    if sigma<.15:return image.copy()
    radius=math.ceil(3*sigma)
    weights=[math.exp(-i*i/(2*sigma*sigma)) for i in range(-radius,radius+1)]
    total=sum(weights);weights=[v/total for v in weights]
    current=image.convertToFormat(QImage.Format_RGBA64_Premultiplied)
    for vertical in [False,True]:
        out=QImage(image.size(),QImage.Format_RGBA64_Premultiplied);out.fill(Qt.transparent)
        p=QPainter(out);p.setCompositionMode(QPainter.CompositionMode_Plus)
        for i,weight in zip(range(-radius,radius+1),weights):
            # Plus + painter opacity interpolates the destination too. Instead,
            # premultiply a 16-bit source by the kernel weight before summing.
            weighted=current.copy();q=QPainter(weighted)
            q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            q.fillRect(weighted.rect(),QColor.fromRgbF(0,0,0,weight));q.end()
            p.drawImage(0 if vertical else i,i if vertical else 0,weighted)
        p.end();current=out
    return current


def filters(image,s):
    out=image.convertToFormat(QImage.Format_RGBA8888)
    if s['brightness']==100 and s['contrast']==100 and s['grayscale']==0:return out
    brightness,contrast,gray=s['brightness']/100,s['contrast']/100,s['grayscale']/100
    lut=[max(0,min(255,round((min(255,v*brightness)-127.5)*contrast+127.5))) for v in range(256)]
    bits=out.bits()
    for i in range(0,out.sizeInBytes(),4):
        if not bits[i+3]:continue
        r,g,b=lut[bits[i]],lut[bits[i+1]],lut[bits[i+2]]
        if gray:
            lum=.2126*r+.7152*g+.0722*b
            r,g,b=(round(v*(1-gray)+lum*gray) for v in (r,g,b))
        bits[i]=r;bits[i+1]=g;bits[i+2]=b
    return out


RENDER_KEYS = ('background_mode','solid_color','image','opacity','blur','darkness','controls','sizing','zoom','x','y','brightness','contrast','grayscale','preview_width','preview_height')

def render_wallpaper(s):
    width,height=preview_dimensions(s)
    s=dict(s,preview_width=width,preview_height=height)
    if s.get('background_mode')=='Cor sólida':
        factor=min(1,1400/max(width,height))
        base=QImage(max(1,round(width*factor)),max(1,round(height*factor)),QImage.Format_ARGB32_Premultiplied)
        color=QColor(s['solid_color']);color.setAlpha(round(255*(1-s['solid_transparency']/100)))
        base.fill(color)
        return base,base,s['palette']
    path=Path(s['image'])
    stamp=path.stat().st_mtime_ns if path.is_file() else 0
    return _render_cached(tuple(s[k] for k in RENDER_KEYS),stamp)

@lru_cache(maxsize=3)
def _render_cached(values,stamp):
    s=dict(zip(RENDER_KEYS,values))
    path=Path(s['image'])
    if not path.is_file():raise ValueError('Imagem não encontrada. Selecione outro arquivo.')
    img,palette=load_image(str(path),path.stat().st_mtime_ns)
    w,h=s['preview_width'],s['preview_height']
    factor=min(1,1400/max(w,h))
    rw,rh=max(1,round(w*factor)),max(1,round(h*factor))
    raw=QImage(rw,rh,QImage.Format_ARGB32_Premultiplied);raw.fill(Qt.transparent)
    p=QPainter(raw);p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(factor,factor);p.drawImage(background_rect(img.width(),img.height(),w,h,s),img);p.end()
    # CSS filter runs on the sidebar pseudo-element (clipped at its bounds).
    raw=filters(gaussian(raw,s['blur']/10*factor),s)
    base=QImage(rw,rh,QImage.Format_ARGB32_Premultiplied);base.fill(QColor('#050505'))
    p=QPainter(base);p.setOpacity(s['opacity']/100);p.drawImage(0,0,raw)
    p.setOpacity(1);p.fillRect(base.rect(),QColor(0,0,0,round(255*s['darkness']/100)));p.end()
    glass=gaussian(base,s['controls']*factor)
    return base,glass,palette
