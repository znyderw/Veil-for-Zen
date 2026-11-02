STYLE='''
QWidget { color: #EAEAEA; font-family: "Inter", "Noto Sans", sans-serif; font-size: 13px; }
QMainWindow, #root { background: #101114; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QFrame#section { background: #191A1F; border: 1px solid #303238; border-radius: 10px; }
QLabel#title { font-size: 23px; font-weight: 600; }
QLabel#muted { color: #9699A3; }
QLabel#status { color: #B5C3EF; }
QPushButton, QToolButton, QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
 background: #24262C; border: 1px solid #303238; border-radius: 6px; padding: 7px 9px;
}
QPushButton:hover, QToolButton:hover { background: #30343F; border-color: #8196D8; }
QSpinBox QLineEdit, QDoubleSpinBox QLineEdit { background: transparent; border: none; padding: 0; }
QPushButton:disabled, QSpinBox:disabled { color: #62656E; }
QPushButton#primary { background: #8196D8; color: #101114; font-weight: 600; }
QToolButton#sectionTitle { background: transparent; border: none; font-weight: 600; text-align: left; }
QSlider::groove:horizontal { background: #303238; height: 4px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #8196D8; border-radius: 2px; }
QSlider::handle:horizontal { background: #B5C3EF; width: 12px; margin: -4px 0; border-radius: 6px; }
QCheckBox { spacing: 7px; }
QListWidget { background: #101114; border: 1px solid #303238; border-radius: 7px; padding: 4px; }
QListWidget::item { border: 1px solid transparent; border-radius: 5px; }
QListWidget::item:selected { background: #242C44; border: 1px solid #8196D8; }
QScrollBar:vertical { background: #191A1F; width: 8px; }
QScrollBar::handle:vertical { background: #40434D; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #24262C; border: 1px solid #303238; padding: 6px; }
QSplitter::handle { background: #101114; width: 14px; }
'''
