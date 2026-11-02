from copy import deepcopy
from PySide6.QtCore import Qt,QRectF,QObject,Signal,QRunnable,QThreadPool,QTimer
from PySide6.QtGui import QColor,QPainter,QPen,QFont,QPainterPath
from PySide6.QtWidgets import QWidget
from core.rendering import render_wallpaper
from core.color_extractor import tab_paint


class Signals(QObject):
    done=Signal(int,object,object)


class Job(QRunnable):
    def __init__(self,ident,fn):
        super().__init__();self.ident=ident;self.fn=fn;self.signals=Signals()
    def run(self):
        try:self.signals.done.emit(self.ident,self.fn(),None)
        except Exception as exc:self.signals.done.emit(self.ident,None,str(exc))


class Preview(QWidget):
    palette_ready=Signal(str,object)
    status=Signal(str)
    failed=Signal(str)
    def __init__(self):
        super().__init__();self.setMinimumSize(200,240)
        self.state=None;self.wallpaper=None;self.glass=None;self.running=False
        self.serial=0;self.job=None;self.render_key=None
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(80)
        self.timer.timeout.connect(self.start_render)
        self.pool=QThreadPool(self);self.pool.setMaxThreadCount(1)

    def update_state(self,state):
        if self.state and state['image']!=self.state['image']:
            self.wallpaper=self.glass=None
        self.state=deepcopy(state);self.serial+=1
        keys=['image','opacity','blur','darkness','controls','sizing','zoom','x','y','brightness','contrast','grayscale','preview_width','preview_height']
        key=tuple(state[k] for k in keys)
        if key!=self.render_key:
            self.render_key=key;self.timer.start()
        self.update()

    def start_render(self):
        if self.running:return
        self.running=True;s=deepcopy(self.state);serial=self.serial
        self.job=Job(serial,lambda:render_wallpaper(s))
        self.job.signals.done.connect(lambda ident,result,error:self.finish(ident,result,error,s))
        self.pool.start(self.job);self.status.emit('Atualizando a prévia…')

    def finish(self,ident,result,error,state):
        self.running=False
        if ident==self.serial:
            if error:
                self.wallpaper=self.glass=None;self.status.emit(error);self.failed.emit(error)
            else:
                self.wallpaper,self.glass,palette=result
                self.palette_ready.emit(state['image'],palette)
                self.status.emit('Prévia atualizada')
            self.update()
        else:self.timer.start()

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(),QColor('#101114'))
        if not self.state:return
        s=self.state;w,h=s['preview_width'],s['preview_height']
        factor=min((self.width()-32)/w,(self.height()-32)/h) if s['fit'] else 1
        # Fit permits shrinking only, so physical pixels retain a clear interpretation.
        factor=max(.01,min(1,factor));p.translate(max(16,(self.width()-w*factor)/2),16);p.scale(factor,factor)
        area=QRectF(0,0,w,h);p.setClipRect(area);p.fillRect(area,QColor('#050505'))
        if self.wallpaper is not None:p.drawImage(area,self.wallpaper)
        font=QFont('Noto Sans');font.setPixelSize(13);p.setFont(font)
        def row(rect,text,state='normal',control=False,icon='○',center=False):
            path=QPainterPath();path.addRoundedRect(rect,8,8)
            p.save();p.setClipPath(path,Qt.IntersectClip)
            if self.glass is not None:
                p.drawImage(area,self.glass)
            if control:
                p.fillRect(rect,QColor(48,48,48,199))
            else:
                style=tab_paint(s,state)
                p.fillRect(rect,QColor(*style['neutral']));p.fillRect(rect,QColor(*style['tint']))
            p.restore()
            if not control:
                p.setPen(QPen(QColor(*tab_paint(s,state)['border']),1));p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(rect.adjusted(.5,.5,-.5,-.5),8,8)
            textrect=rect.adjusted(12,0,-10,0)
            label=(icon+'   ' if icon else '')+text
            label=p.fontMetrics().elidedText(label,Qt.ElideRight,int(textrect.width()))
            alignment=Qt.AlignCenter if center else Qt.AlignVCenter
            p.setPen(QColor('#000'));p.drawText(textrect.translated(0,1),alignment,label)
            p.setPen(QColor('#f5f5f5'));p.drawText(textrect,alignment,label)
        p.setPen(QColor('#9699a3'));p.drawText(QRectF(12,8,w-24,22),Qt.AlignVCenter,'···')
        row(QRectF(8,38,w-16,34),'Pesquisar…',control=True,icon='⌕')
        ew=(w-24)/2
        row(QRectF(8,80,ew,44),'M',icon='',center=True);row(QRectF(16+ew,80,ew,44),'◉',icon='',center=True)
        p.setPen(QColor('#b1b4bd'));p.drawText(QRectF(14,140,w-28,24),Qt.AlignVCenter,'Pessoal')
        row(QRectF(8,174,w-16,34),'Aba fixada',icon='◇')
        p.setPen(QPen(QColor(255,255,255,25),1));p.drawLine(10,220,w-10,220)
        for i,(text,state) in enumerate([('Página selecionada','selected'),('Aba em hover','hover'),('Documentação','normal'),('Música e vídeos','normal'),('Configurações','normal')]):
            row(QRectF(8,232+i*40,w-16,34),text,state)
        p.setPen(QColor('#ddd'));p.drawText(QRectF(18,440,w-36,30),Qt.AlignVCenter,'+  Nova aba')
        p.drawText(QRectF(14,h-36,w-28,28),Qt.AlignVCenter,'▣    ◉                              +')
        p.setClipping(False);p.setPen(QPen(QColor('#303238'),1));p.setBrush(Qt.NoBrush);p.drawRoundedRect(area,9,9)
