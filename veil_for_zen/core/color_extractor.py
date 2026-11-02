"""Deterministic, muted dominant colors using a small weighted histogram."""
import colorsys
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

PALETTES = {'Vinho escuro':['#845d70','#695260','#92727b','#635865'],
    'Azul noturno':['#627da1','#566681','#71879d','#646d86'],
    'Cinza neutro':['#737780','#656a73','#85868e','#62656c'],
    'Verde floresta':['#5c806b','#526c64','#758778','#626f66']}


def extract_palette(image):
    if image.isNull():
        raise ValueError('Não foi possível analisar a imagem.')
    image = image.scaled(96,96,Qt.KeepAspectRatio,Qt.SmoothTransformation)
    bins = {}
    for y in range(image.height()):
        for x in range(image.width()):
            c=image.pixelColor(x,y)
            if c.alphaF()<.5: continue
            h,s,v=colorsys.rgb_to_hsv(c.redF(),c.greenF(),c.blueF())
            if v<.06 or v>.94: continue
            weight=(1-abs(v-.40))*(.2 if s>.85 else 1)*(.35 if s<.1 else 1)
            key=(int(h*18)%18, int(s*4), int(v*4))
            entry=bins.setdefault(key,[0,0,0,0])
            entry[0]+=weight
            for i,value in enumerate([c.redF(),c.greenF(),c.blueF()]): entry[i+1]+=value*weight
    result=[]
    for _,entry in sorted(bins.items(),key=lambda kv:-kv[1][0]):
        rgb=[v/entry[0] for v in entry[1:]]
        h,s,v=colorsys.rgb_to_hsv(*rgb)
        c=QColor.fromHsvF(h,min(.32,max(.08,s*.45)),.48)
        if all(sum((a-b)**2 for a,b in zip(c.getRgb()[:3],QColor(old).getRgb()[:3]))>500 for old in result):
            result.append(c.name())
        if len(result)==4: break
    if not result: result=['#737780']
    base=QColor(result[0]); h,s,v,_=base.getHsvF()
    while len(result)<4:
        i=len(result)
        result.append(QColor.fromHsvF((max(h,0)+i*.055)%1,min(s,.25),.40+i*.035).name())
    return result


def tab_paint(s, state='normal'):
    """One source of truth for CSS and preview state colors (RGBA tuples)."""
    c=QColor(s['palette'][s['accent_index']]); amount=s['intensity']/100
    hue,saturation,value,_=c.getHsvF()
    c=QColor.fromHsvF(max(0,hue),min(.4,saturation),min(.52,value))
    # Keep alpha independent of wallpaper contrast. Shadow + neutral scrim protects text.
    fill=amount*{'normal':.24,'hover':.40,'selected':.57}[state]
    border=amount*{'normal':.72,'hover':.95,'selected':1.25}[state]
    if s['tab_style']=='Bordas discretas': fill*=.18
    if s['tab_style']=='Preenchimento suave': border=0
    floor={'normal':.64,'hover':.70,'selected':.77}[state]
    neutral=floor+(1-floor)*s['shade']/100
    if amount==0: fill=border=0
    return dict(tint=(*c.getRgb()[:3],min(255,round(fill*255))),
        border=(*c.getRgb()[:3],min(255,round(border*255))),
        neutral=(8,8,8,round(neutral*255)))
