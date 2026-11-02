STYLE='''
QWidget { color: #EAEAEA; font-family: "Inter", "Noto Sans", sans-serif; }
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
QListWidget::item:selected { color: #EAEAEA; background: #242C44; border: 1px solid #8196D8; }
QScrollBar:vertical { background: #191A1F; width: 8px; }
QScrollBar::handle:vertical { background: #40434D; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #24262C; border: 1px solid #303238; padding: 6px; }
QSplitter::handle { background: #101114; width: 14px; }
'''

# Explicit palette covers popup windows and controls that do not inherit QSS.
def apply_theme(app):
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    roles = {'Window':'#101114', 'WindowText':'#EAEAEA', 'Base':'#191A1F',
             'AlternateBase':'#24262C', 'Text':'#EAEAEA', 'Button':'#24262C',
             'ButtonText':'#EAEAEA', 'Highlight':'#8196D8', 'HighlightedText':'#101114',
             'ToolTipBase':'#24262C', 'ToolTipText':'#EAEAEA', 'PlaceholderText':'#A0A3AD'}
    for role, color in roles.items():
        palette.setColor(getattr(QPalette, role), QColor(color))
    for role in ('Text','WindowText','ButtonText'):
        palette.setColor(QPalette.Disabled, getattr(QPalette, role), QColor('#858894'))
    app.setStyle('Fusion'); app.setPalette(palette); app.setStyleSheet(STYLE)

STYLE += '''
QAbstractItemView, QComboBox QAbstractItemView, QMenu {
 background-color: #191A1F; color: #EAEAEA; border: 1px solid #303238;
 selection-background-color: #8196D8; selection-color: #101114; outline: 0;
}
QComboBox QAbstractItemView::item { min-height: 28px; padding: 4px 8px; }
QMenu::item { padding: 7px 20px; }
QMenu::item:selected { background: #8196D8; color: #101114; }
QWidget:disabled, QMenu::item:disabled { color: #858894; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
 border: 1px solid #8196D8;
}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #8196D8; }
QToolTip { color: #EAEAEA; background-color: #24262C; }
QScrollBar:horizontal { background: #191A1F; height: 10px; }
QScrollBar::handle:horizontal { background: #50535D; min-width: 28px; border-radius: 4px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: #191A1F; }
QLabel#title { font-size: 18px; }
'''
