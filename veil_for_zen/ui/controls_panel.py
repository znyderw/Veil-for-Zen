from pathlib import Path
from PySide6.QtCore import Qt,Signal,QSignalBlocker,QSize
from PySide6.QtGui import QColor,QIcon,QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QFrame,QToolButton,
    QPushButton,QLabel,QSlider,QSpinBox,QDoubleSpinBox,QComboBox,QCheckBox,QColorDialog,QListWidget,QListWidgetItem,QListView,QLineEdit)
from veil_for_zen.core.color_extractor import PALETTES


class Section(QFrame):
    def __init__(self,title,opened=False):
        super().__init__();self.setObjectName('section')
        box=QVBoxLayout(self);box.setContentsMargins(12,8,12,12)
        head=QToolButton();head.setObjectName('sectionTitle');head.setText(title)
        head.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);head.setCheckable(True);head.setChecked(opened)
        head.setSizePolicy(head.sizePolicy().horizontalPolicy().Expanding,head.sizePolicy().verticalPolicy())
        self.body=QWidget();self.form=QFormLayout(self.body);self.form.setContentsMargins(0,8,0,0)
        self.form.setRowWrapPolicy(QFormLayout.WrapLongRows);self.form.setVerticalSpacing(12)
        def toggle(value):
            self.body.setVisible(value);head.setArrowType(Qt.DownArrow if value else Qt.RightArrow)
        head.toggled.connect(toggle);box.addWidget(head);box.addWidget(self.body);toggle(opened)


class ControlsPanel(QWidget):
    changed=Signal(str,object)
    pick_image=Signal()
    image_selected=Signal(str)
    open_library=Signal()
    pick_profile=Signal()
    refresh_palette=Signal()
    detect=Signal()
    palette_chosen=Signal(object)
    def __init__(self):
        super().__init__();self.inputs={};self.swatches=[]
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(10)
        image=Section('Fundo',True);box.addWidget(image);self.background_section=image
        self.combo(image,'background_scope','Aplicar em',['Barra lateral','Navegador inteiro'])
        self.scope_note=QLabel();self.scope_note.setObjectName('muted');self.scope_note.setWordWrap(True);image.form.addRow(self.scope_note)
        self.combo(image,'background_mode','Modo',['Imagem','Cor sólida'])
        self.solid_widget=QWidget();solidbox=QVBoxLayout(self.solid_widget);solidbox.setContentsMargins(0,0,0,0)
        colorrow=QHBoxLayout();self.solid_hex=QLineEdit();self.solid_hex.setPlaceholderText('#1B1D22');self.solid_hex.setMaxLength(7)
        self.solid_hex.editingFinished.connect(self.accept_solid_hex);colorrow.addWidget(self.solid_hex)
        colorpick=QPushButton('Escolher cor…');colorpick.clicked.connect(self.pick_solid);colorrow.addWidget(colorpick);solidbox.addLayout(colorrow)
        self.solid_presets=QComboBox();self.solid_presets.addItems(['Paleta de fundos…','#101010','#1B1D22','#17243A','#29171D','#182720'])
        self.solid_presets.activated.connect(lambda i:self.changed.emit('solid_color',self.solid_presets.itemText(i)) if i else None);solidbox.addWidget(self.solid_presets)
        self.recent=QComboBox();self.recent.activated.connect(lambda i:self.changed.emit('solid_color',self.recent.itemText(i)) if i else None);solidbox.addWidget(self.recent)
        image.form.addRow(self.solid_widget)
        self.number(image,'solid_transparency','Transparência',0,100,'%')
        self.inputs['solid_transparency'].setToolTip('0%: cor opaca. 100%: fundo sem cor. Ao aplicar, o Veil habilita a transparência nativa do Zen no Linux; reinicie o navegador. Abas e controles mantêm o contraste.')
        self.gallery=QListWidget();self.gallery.setViewMode(QListView.IconMode)
        self.gallery.setResizeMode(QListView.Adjust);self.gallery.setMovement(QListView.Static)
        self.gallery.setIconSize(QSize(72,82));self.gallery.setGridSize(QSize(90,108))
        self.gallery.setMinimumHeight(132);self.gallery.setMaximumHeight(236)
        self.gallery.setSpacing(3)
        self.gallery.itemClicked.connect(lambda item:self.image_selected.emit(item.data(Qt.UserRole)))
        self.gallery.itemActivated.connect(lambda item:self.image_selected.emit(item.data(Qt.UserRole)))
        image.form.addRow(self.gallery)
        self.library_note=QLabel('Carregando biblioteca…');self.library_note.setObjectName('muted');image.form.addRow(self.library_note)
        buttons=QWidget();row=QHBoxLayout(buttons);row.setContentsMargins(0,0,0,0)
        pick=QPushButton('Adicionar imagens…');pick.clicked.connect(self.pick_image.emit);row.addWidget(pick)
        folder=QPushButton('Abrir biblioteca');folder.clicked.connect(self.open_library.emit);row.addWidget(folder)
        self.image_buttons=buttons;image.form.addRow(buttons)
        self.filename=QLabel();self.filename.setWordWrap(True);self.filename.setObjectName('muted');image.form.addRow(self.filename)
        self.number(image,'opacity','Opacidade',0,100,'%')
        self.number(image,'darkness','Escurecimento',0,100,'%')
        framing=image
        self.combo(framing,'sizing','Ajuste',['Largura','Conter','Preencher','Esticar'])
        self.inputs['sizing'].setToolTip('Largura permite zoom. Conter mostra tudo. Preencher pode recortar. Esticar pode deformar.')
        self.number(framing,'zoom','Escala',20,300,'%')
        self.number(framing,'x','Horizontal',0,100,'%')
        self.number(framing,'y','Vertical',0,100,'%')
        tabs=Section('Abas');box.addWidget(tabs)
        self.combo(tabs,'color_mode','Cores das abas',['Automática','Personalizada'])
        self.regenerate=regenerate=QPushButton('Atualizar paleta da imagem');regenerate.clicked.connect(self.refresh_palette.emit);tabs.form.addRow(regenerate)
        swatches=QWidget();swatchbox=QHBoxLayout(swatches);swatchbox.setContentsMargins(0,0,0,0)
        for index in range(4):
            button=QPushButton();button.setFixedSize(38,30)
            button.setToolTip('Clique para usar esta cor nas abas. As demais ficam disponíveis na paleta.')
            button.clicked.connect(lambda _,i=index:self.changed.emit('accent_index',i))
            self.swatches.append(button);swatchbox.addWidget(button)
        swatchbox.addStretch();tabs.form.addRow('Cor em uso',swatches)
        self.presets=QComboBox();self.presets.addItems(['Escolher paleta…',*PALETTES])
        self.presets.activated.connect(self.choose_palette);tabs.form.addRow('Paleta pronta',self.presets)
        manual=QPushButton('Editar cor em uso…');manual.clicked.connect(self.edit_color);tabs.form.addRow(manual)
        self.combo(tabs,'tab_style','Estilo',['Bordas discretas','Preenchimento suave','Combinado'])
        self.number(tabs,'intensity','Intensidade',0,100,'%')
        self.number(tabs,'shade','Proteção do texto',0,100,'%')
        info=QLabel('A cor escolhida vale para todas as abas. Seleção e hover têm estados próprios. Cores por site não estão disponíveis: o CSS não recebe um domínio confiável nem analisa favicons.')
        info.setObjectName('muted');info.setWordWrap(True);tabs.form.addRow(info)
        effects=Section('Efeitos');box.addWidget(effects)
        self.effects_section=effects
        self.number(effects,'blur','Blur da imagem',0,150,'px',10)
        self.number(effects,'controls','Blur dos controles',0,20,'px')
        self.number(effects,'brightness','Brilho',20,200,'%')
        self.number(effects,'contrast','Contraste',20,200,'%')
        self.number(effects,'grayscale','Preto e branco',0,100,'%')
        advanced=Section('Avançado');box.addWidget(advanced);self.advanced_section=advanced
        self.combo(advanced,'dimension_mode','Dimensões',['Manual','Automático'])
        self.detect_button=detect=QPushButton('Verificar medidas disponíveis');detect.clicked.connect(self.detect.emit);advanced.form.addRow(detect)
        self.number(advanced,'preview_width','Largura da barra',100,1000,'px',slider=False)
        self.number(advanced,'preview_height','Altura da barra',240,3000,'px',slider=False)
        self.number(advanced,'browser_width','Largura do navegador',480,7680,'px',slider=False)
        self.number(advanced,'browser_height','Altura do navegador',320,4320,'px',slider=False)
        self.inputs['browser_width'].setToolTip('Largura CSS usada apenas para a prévia do fundo inteiro; não redimensiona o Zen.')
        self.inputs['browser_height'].setToolTip('Altura CSS usada apenas para a prévia do fundo inteiro; não redimensiona o Zen.')
        self.inputs['preview_width'].setToolTip('Largura CSS da área da imagem no Zen; não é a largura da janela. Não altera a barra real.')
        self.inputs['preview_height'].setToolTip('Altura CSS da área da imagem no Zen. O padrão é manual, não uma medida detectada.')
        fit=QCheckBox('Ajustar prévia à janela');fit.toggled.connect(lambda v:self.changed.emit('fit',v))
        self.inputs['fit']=fit;advanced.form.addRow(fit)
        self.dimension_note=QLabel('Medidas manuais. A redução visual não altera o enquadramento.');self.dimension_note.setWordWrap(True)
        self.dimension_note.setObjectName('muted');advanced.form.addRow(self.dimension_note)
        profile=QPushButton('Escolher perfil do Zen…');profile.clicked.connect(self.pick_profile.emit);advanced.form.addRow(profile)
        self.profile_label=QLabel();self.profile_label.setWordWrap(True);self.profile_label.setObjectName('muted');advanced.form.addRow(self.profile_label)
        box.addStretch()

    def number(self,section,key,label,lo,hi,unit='',divisor=1,slider=True):
        row=QWidget();layout=QHBoxLayout(row);layout.setContentsMargins(0,0,0,0);layout.setSpacing(8)
        spin=QDoubleSpinBox() if divisor!=1 else QSpinBox()
        if divisor!=1:spin.setDecimals(1);spin.setSingleStep(.1)
        spin.setRange(lo/divisor,hi/divisor);spin.setSuffix(' '+unit);spin.setMinimumWidth(90)
        if slider:
            track=QSlider(Qt.Horizontal);track.setRange(lo,hi)
            track.valueChanged.connect(lambda v:spin.setValue(v/divisor))
            spin.valueChanged.connect(lambda v:track.setValue(round(v*divisor)));layout.addWidget(track)
            spin._track=track
        spin.valueChanged.connect(lambda v:self.changed.emit(key,round(v*divisor)))
        spin._divisor=divisor;self.inputs[key]=spin;layout.addWidget(spin);section.form.addRow(label,row)

    def combo(self,section,key,label,items):
        control=QComboBox();control.addItems(items)
        control.currentTextChanged.connect(lambda v:self.changed.emit(key,v));self.inputs[key]=control
        section.form.addRow(label,control)

    def sync(self,s):
        self.state=s
        for key,control in self.inputs.items():
            blocker=QSignalBlocker(control)
            if isinstance(control,QComboBox):control.setCurrentText(s[key])
            elif isinstance(control,QCheckBox):control.setChecked(s[key])
            else:
                control.setValue(s[key]/control._divisor)
                if hasattr(control,'_track'):
                    block=QSignalBlocker(control._track);control._track.setValue(s[key]);del block
            del blocker
        self.inputs['zoom'].setEnabled(s['sizing']=='Largura')
        self.filename.setText(s['image'].split('/')[-1]);self.filename.setToolTip(s['image'])
        self.select_library_image(s['image'])
        self.profile_label.setText(s['profile'] or 'Nenhum perfil selecionado')
        whole=s['background_scope']=='Navegador inteiro'
        self.advanced_section.form.setRowVisible(self.inputs['dimension_mode'],not whole)
        self.advanced_section.form.setRowVisible(self.detect_button,not whole)
        if whole:self.dimension_note.setText('Dimensões manuais para a prévia da janela inteira; não alteram o tamanho do navegador.')
        self.scope_note.setText('Um único fundo cobre a janela. Páginas com fundo próprio podem cobri-lo.' if whole else 'O fundo é aplicado somente à barra lateral.')
        for key in ['preview_width','preview_height']:
            self.advanced_section.form.setRowVisible(self.inputs[key].parentWidget(),not whole)
        for key in ['browser_width','browser_height']:
            self.advanced_section.form.setRowVisible(self.inputs[key].parentWidget(),whole)
        solid=s['background_mode']=='Cor sólida'
        self.solid_widget.setVisible(solid)
        self.background_section.form.setRowVisible(self.inputs['solid_transparency'].parentWidget(),solid)
        blocker=QSignalBlocker(self.solid_hex);self.solid_hex.setText(s['solid_color']);del blocker
        self.recent.clear();self.recent.addItems(['Cores recentes…',*s['recent_colors']])
        self.regenerate.setEnabled(not solid)
        for field in [self.gallery,self.library_note,self.image_buttons,self.filename]:
            self.background_section.form.setRowVisible(field,not solid)
        for key in ['opacity','darkness','sizing','zoom','x','y']:
            widget=self.inputs[key]
            self.background_section.form.setRowVisible(widget if key=='sizing' else widget.parentWidget(),not solid)
        for key in ['blur','brightness','contrast','grayscale']:
            self.effects_section.form.setRowVisible(self.inputs[key].parentWidget(),not solid)
        for i,button in enumerate(self.swatches):
            button.setEnabled(i<len(s['palette']))
            color=s['palette'][min(i,len(s['palette'])-1)]
            button.setStyleSheet(f'background: {color}; border: {"2px solid #EAEAEA" if i==s["accent_index"] else "1px solid #303238"};')

    def choose_palette(self,index):
        if index:
            self.palette_chosen.emit(PALETTES[self.presets.itemText(index)].copy())
            self.presets.setCurrentIndex(0)

    def set_library_images(self,images,append=False):
        if not append:self.gallery.clear()
        for path,thumb in images:
            item=QListWidgetItem(QIcon(QPixmap.fromImage(thumb)),Path(path).name)
            item.setData(Qt.UserRole,path);item.setToolTip(Path(path).name)
            self.gallery.addItem(item)
        self.library_note.setText((f'{self.gallery.count()} imagem' + (' carregada' if self.gallery.count()==1 else 's carregadas')) if self.gallery.count() else 'Adicione imagens para começar.')
        if hasattr(self,'state'):self.select_library_image(self.state['image'])

    def select_library_image(self,path):
        selected=str(Path(path).resolve())
        for i in range(self.gallery.count()):
            item=self.gallery.item(i);item.setSelected(item.data(Qt.UserRole)==selected)

    def edit_color(self):
        index=self.state['accent_index'];palette=self.state['palette'].copy()
        color=QColorDialog.getColor(QColor(palette[index]),self,'Cor das abas',QColorDialog.DontUseNativeDialog)
        if color.isValid():palette[index]=color.name();self.palette_chosen.emit(palette)

    def accept_solid_hex(self):
        import re
        value=self.solid_hex.text().strip()
        if re.fullmatch(r'#[0-9a-fA-F]{6}',value):
            self.solid_hex.setStyleSheet('');self.changed.emit('solid_color',value.upper())
        else:
            self.solid_hex.setStyleSheet('border: 1px solid #DC8888;')
            self.solid_hex.setToolTip('Use uma cor no formato #RRGGBB.')

    def pick_solid(self):
        color=QColorDialog.getColor(QColor(self.state['solid_color']),self,'Cor do fundo',QColorDialog.DontUseNativeDialog)
        if color.isValid():self.changed.emit('solid_color',color.name().upper())
