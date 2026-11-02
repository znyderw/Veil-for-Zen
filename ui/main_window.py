from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import Qt,QThreadPool,QTimer,QFileSystemWatcher,QUrl
from PySide6.QtGui import QImageReader,QDesktopServices
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QScrollArea,QSplitter,QFileDialog,QMessageBox,QInputDialog,QDialog,QListWidget)
from core.settings import ROOT,DEFAULTS,load_settings,normalize,save_json
from core.presets import Presets
from core.zen_integration import save_mod,detect_dimensions
from core.image_library import scan_images,import_image
from .controls_panel import ControlsPanel
from .preview import Preview,Job


class Studio(QMainWindow):
    def __init__(self,settings_path=ROOT/'settings.json',presets_path=ROOT/'presets.json',library_path=None):
        super().__init__();self.settings_path=Path(settings_path);self.startup_error=None
        try:self.state=load_settings(self.settings_path)
        except (OSError,ValueError) as exc:self.state=deepcopy(DEFAULTS);self.startup_error=str(exc)
        self.saved=deepcopy(self.state);self.pending_palette=None;self.working=False
        self.pool=QThreadPool(self);self.pool.setMaxThreadCount(2);self.jobs=[]
        self.library_path=Path(library_path or self.settings_path.parent/'fn_zen')
        self.library_busy=False;self.library_again=False
        self.library_watcher=QFileSystemWatcher(self)
        if self.library_path.is_dir():self.library_watcher.addPath(str(self.library_path))
        self.library_timer=QTimer(self);self.library_timer.setSingleShot(True);self.library_timer.setInterval(200)
        self.library_timer.timeout.connect(self.reload_library)
        self.library_watcher.directoryChanged.connect(lambda _:self.library_timer.start())
        self.library_watcher.fileChanged.connect(lambda _:self.library_timer.start())
        try:self.presets=Presets(presets_path)
        except (OSError,ValueError) as exc:self.presets=None;self.startup_error=str(exc)
        self.setWindowTitle('Zen Sidebar Studio 2.0');self.resize(1120,850);self.setMinimumSize(760,560)
        self.setAcceptDrops(True)
        root=QWidget();root.setObjectName('root');self.setCentralWidget(root)
        outer=QVBoxLayout(root);outer.setContentsMargins(24,20,24,18);outer.setSpacing(16)
        header=QHBoxLayout();title=QLabel('Zen Sidebar Studio');title.setObjectName('title');header.addWidget(title)
        version=QLabel('2.0');version.setObjectName('muted');header.addWidget(version);header.addStretch()
        self.dirty=QLabel();self.dirty.setObjectName('status');header.addWidget(self.dirty)
        library=QPushButton('Presets e histórico');library.clicked.connect(self.manage_presets);header.addWidget(library)
        outer.addLayout(header)
        split=QSplitter(Qt.Horizontal);outer.addWidget(split,1)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setMinimumWidth(350)
        self.controls=ControlsPanel();scroll.setWidget(self.controls);split.addWidget(scroll)
        right=QWidget();rightbox=QVBoxLayout(right);rightbox.setContentsMargins(12,0,0,0)
        self.geometry_label=QLabel();self.geometry_label.setObjectName('muted');rightbox.addWidget(self.geometry_label)
        self.preview_scroll=QScrollArea();self.preview_scroll.setWidgetResizable(True)
        self.preview=Preview();self.preview_scroll.setWidget(self.preview);rightbox.addWidget(self.preview_scroll,1)
        self.preview_note=QLabel('Abas de exemplo · renderização Qt aproximada do Gecko');self.preview_note.setObjectName('muted')
        self.preview_note.setWordWrap(True);rightbox.addWidget(self.preview_note)
        split.addWidget(right);split.setSizes([430,630]);split.setStretchFactor(1,1)
        self.status=QLabel('Escolha um fundo da biblioteca fn_zen.');self.status.setObjectName('status');self.status.setWordWrap(True)
        outer.addWidget(self.status)
        footer=QHBoxLayout()
        reset=QPushButton('Restaurar alterações');reset.clicked.connect(self.restore);footer.addWidget(reset)
        footer.addStretch();preset=QPushButton('Salvar preset');preset.clicked.connect(self.save_preset);footer.addWidget(preset)
        self.apply=QPushButton('Aplicar no Zen');self.apply.setObjectName('primary');self.apply.clicked.connect(self.apply_settings);footer.addWidget(self.apply)
        outer.addLayout(footer)
        self.controls.changed.connect(self.change);self.controls.pick_image.connect(self.pick_image)
        self.controls.image_selected.connect(self.accept_image)
        self.controls.open_library.connect(self.open_library)
        self.controls.pick_profile.connect(self.pick_profile);self.controls.palette_chosen.connect(self.custom_palette)
        self.controls.refresh_palette.connect(self.refresh_palette);self.controls.detect.connect(self.detect)
        self.preview.palette_ready.connect(self.palette_ready);self.preview.status.connect(self.preview_status)
        self.preview.failed.connect(self.preview_failed)
        self.refresh()
        self.reload_library()
        if self.startup_error:QTimer.singleShot(0,lambda:self.error(self.startup_error))
        if self.state['color_mode']=='Automática':self.pending_palette=self.state['image']
        if self.state['dimension_mode']=='Automático':QTimer.singleShot(0,self.detect)

    def refresh(self):
        self.controls.sync(self.state)
        manual='Manual' if self.state['dimension_mode']=='Manual' else 'Automático indisponível → manual'
        self.geometry_label.setText(f'{self.state["preview_width"]} × {self.state["preview_height"]} px · {manual}')
        if self.state['fit']:self.preview.setMinimumSize(200,240)
        else:self.preview.setMinimumSize(self.state['preview_width']+32,self.state['preview_height']+32)
        self.preview.update_state(self.state)
        changed=self.state!=self.saved
        self.dirty.setText('Alterações não aplicadas' if changed else 'Configuração salva')
        self.setWindowTitle(('• ' if changed else '')+'Zen Sidebar Studio 2.0')

    def change(self,key,value):
        self.state[key]=value
        if key=='color_mode' and value=='Automática':self.refresh_palette()
        self.refresh()
        if key=='dimension_mode' and value=='Automático':self.detect()

    def preview_status(self,text):
        if not self.working:self.preview_note.setText(text+' · abas de exemplo; diferenças de rasterização Qt/Gecko')

    def preview_failed(self,text):
        self.pending_palette=None;self.status.setText(text)

    def error(self,text): QMessageBox.warning(self,'Zen Sidebar Studio',str(text))

    def accept_image(self,path):
        reader=QImageReader(str(path))
        if not reader.canRead():self.error('Selecione uma imagem JPEG, PNG, WebP ou BMP válida.');return
        self.state['image']=str(Path(path).resolve())
        self.preview.render_key=None
        if self.state['color_mode']=='Automática':self.pending_palette=self.state['image']
        self.refresh()

    def pick_image(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Adicionar à biblioteca fn_zen',str(Path.home()),'Imagens e outros arquivos (*)')
        if paths:self.add_images(paths)

    def add_images(self,paths):
        def imported(result,error):
            if error:self.error(error);return
            self.reload_library()
            if result:self.accept_image(result[0])
        self.run_job(lambda:[import_image(path,self.library_path) for path in paths],imported)

    def open_library(self):
        try:self.library_path.mkdir(parents=True,exist_ok=True)
        except OSError as exc:self.error(exc);return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.library_path))):
            self.error('Não foi possível abrir fn_zen no gerenciador de arquivos.')

    def reload_library(self):
        if self.library_busy:self.library_again=True;return
        self.library_busy=True
        def loaded(result,error):
            self.library_busy=False
            if error:self.controls.library_note.setText('Não foi possível ler fn_zen: '+error)
            else:
                self.controls.set_library_images(result)
                paths=self.library_watcher.files()
                if paths:self.library_watcher.removePaths(paths)
                if result:self.library_watcher.addPaths([path for path,_ in result])
                if self.library_path.is_dir() and str(self.library_path) not in self.library_watcher.directories():
                    self.library_watcher.addPath(str(self.library_path))
            if self.library_again:self.library_again=False;self.library_timer.start()
        self.run_job(lambda:scan_images(self.library_path),loaded)

    def pick_profile(self):
        path=QFileDialog.getExistingDirectory(self,'Perfil do Zen',self.state['profile'])
        if path:
            if not (Path(path)/'prefs.js').is_file():self.error('Essa pasta não é um perfil do Zen: prefs.js não encontrado.');return
            self.change('profile',path)

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):event.acceptProposedAction()

    def dropEvent(self,event):
        paths=[url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:self.add_images(paths);event.acceptProposedAction()

    def refresh_palette(self):
        self.state['color_mode']='Automática';self.pending_palette=self.state['image']
        # Force a fresh render even when only the palette is requested.
        self.preview.render_key=None;self.refresh()

    def palette_ready(self,path,palette):
        if self.pending_palette==path and self.state['color_mode']=='Automática':
            self.pending_palette=None;self.state['palette']=palette;self.state['accent_index']=0;self.refresh()

    def custom_palette(self,palette):
        self.pending_palette=None;self.state.update(palette=palette,color_mode='Personalizada',accent_index=min(self.state['accent_index'],len(palette)-1));self.refresh()

    def run_job(self,fn,callback):
        job=Job(len(self.jobs),fn);self.jobs.append(job)
        def done(ident,result,error):
            self.jobs.remove(job);callback(result,error)
        job.signals.done.connect(done);self.pool.start(job)

    def detect(self):
        self.controls.dimension_note.setText('Consultando medidas persistidas e Hyprland…')
        self.run_job(lambda:detect_dimensions(self.state['profile']),lambda result,error:self.controls.dimension_note.setText(error or result['message']))

    def restore(self):
        self.pending_palette=None;self.state=deepcopy(self.saved);self.refresh();self.status.setText('Alterações locais restauradas. O perfil não foi modificado.')

    def save_preset(self):
        if self.presets is None:self.error('O arquivo de presets precisa ser recuperado antes de salvar. O original foi preservado.');return
        name,ok=QInputDialog.getText(self,'Salvar preset','Nome do preset:')
        if ok:
            try:self.presets.add(name,self.state);self.status.setText('Preset salvo.')
            except (OSError,ValueError) as exc:self.error(exc)

    def manage_presets(self):
        if self.presets is None:self.error('Não foi possível abrir os presets; arquivo original preservado.');return
        dialog=QDialog(self);dialog.setWindowTitle('Presets e histórico');dialog.resize(560,430)
        layout=QVBoxLayout(dialog);listing=QListWidget();layout.addWidget(listing)
        note=QLabel('Carregar atualiza o painel. Use Aplicar no Zen para gravar no perfil atual.');note.setWordWrap(True);layout.addWidget(note)
        def populate():
            listing.clear()
            for history,key in [(False,'presets'),(True,'history')]:
                for item in reversed(self.presets.data[key]):
                    listing.addItem(('Histórico · ' if history else 'Preset · ')+item['name'])
                    listing.item(listing.count()-1).setData(Qt.UserRole,(item['id'],history))
        populate();buttons=QHBoxLayout();layout.addLayout(buttons)
        def selected():
            if listing.currentItem():return listing.currentItem().data(Qt.UserRole)
            return None
        def load():
            value=selected()
            if not value:return
            try:
                s=self.presets.get(value[0],value[1],require_image=False);s['profile']=self.state['profile']
                if not Path(s['image']).is_file():
                    replacement,_=QFileDialog.getOpenFileName(dialog,'Imagem ausente — selecionar substituta',str(Path.home()),'Imagens (*.jpg *.jpeg *.png *.webp *.bmp)')
                    if not replacement:return
                    if not QImageReader(replacement).canRead():raise ValueError('Não foi possível abrir a imagem substituta.')
                    s['image']=replacement
                self.pending_palette=None;self.state=s;self.refresh();dialog.accept();self.status.setText('Configuração carregada no painel. Revise e aplique.')
            except (OSError,ValueError,KeyError,StopIteration) as exc:self.error(exc)
        def rename():
            value=selected()
            if not value or value[1]:return
            name,ok=QInputDialog.getText(dialog,'Renomear preset','Novo nome:')
            if ok:
                try:self.presets.rename(value[0],name);populate()
                except (OSError,ValueError) as exc:self.error(exc)
        def delete():
            value=selected()
            if not value or value[1]:return
            if QMessageBox.question(dialog,'Excluir preset','Excluir o preset selecionado? A imagem e os backups serão preservados.')==QMessageBox.Yes:
                try:self.presets.delete(value[0]);populate()
                except OSError as exc:self.error(exc)
        for text,fn in [('Carregar',load),('Renomear',rename),('Excluir',delete)]:
            button=QPushButton(text);button.clicked.connect(fn);buttons.addWidget(button)
        listing.itemDoubleClicked.connect(lambda _:load());dialog.exec()

    def apply_settings(self):
        if self.working:return
        if self.pending_palette:
            self.status.setText('Aguarde a análise da imagem terminar antes de aplicar.');return
        try:s=normalize(self.state)
        except ValueError as exc:self.error(exc);return
        self.working=True;self.apply.setEnabled(False);self.status.setText('Aplicando com backup…')
        def complete(backup,error):
            self.working=False;self.apply.setEnabled(True)
            if error:self.error(error);self.status.setText('Não foi possível aplicar. Consulte o erro; backups existentes foram mantidos.');return
            try:
                if self.presets:
                    self.presets.remember(self.saved);self.presets.remember(s)
                save_json(self.settings_path,s);self.saved=deepcopy(s)
                self.status.setText('Aplicado! Feche e abra o Zen. Backup: '+str(backup))
            except (OSError,ValueError) as exc:
                self.status.setText('CSS aplicado no Zen, mas não foi possível salvar o histórico local: '+str(exc))
            self.refresh()
        self.run_job(lambda:save_mod(s),complete)

    def closeEvent(self,event):
        if self.working:
            self.status.setText('Aguarde a aplicação terminar antes de fechar.');event.ignore();return
        if self.state!=self.saved:
            reply=QMessageBox.question(self,'Alterações não aplicadas','Fechar e descartar as alterações do painel?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if reply!=QMessageBox.Yes:event.ignore();return
        # Worker threads only paint into QImages; await their completion before destruction.
        self.library_timer.stop();self.preview.timer.stop();self.preview.pool.waitForDone();self.pool.waitForDone();event.accept()
