"""Veil entry point. All writes require an explicit user action."""
import argparse
import os
import sys
from . import __version__, DISPLAY_VERSION


def main():
    parser=argparse.ArgumentParser(description='Veil for Zen — personalização independente da barra lateral')
    parser.add_argument('--version',action='version',version='Veil for Zen '+DISPLAY_VERSION)
    parser.add_argument('--legacy-dir',help='Diretório antigo para oferecer migração por cópia')
    args=parser.parse_args()
    # Fusion + an explicit palette avoid platform theme popup contrast issues.
    if os.environ.get('QT_QPA_PLATFORMTHEME')=='gtk3':os.environ['QT_QPA_PLATFORMTHEME']=''
    from PySide6.QtWidgets import QApplication,QMessageBox,QProgressDialog
    from PySide6.QtGui import QIcon
    from .ui.theme import apply_theme
    from .core.paths import settings_file
    from .core.migration import find_legacy,migrate
    from .ui.main_window import VeilWindow
    from pathlib import Path
    app=QApplication(sys.argv[:1]);app.setApplicationName('Veil for Zen')
    app.setApplicationVersion(__version__);app.setOrganizationName('veil-for-zen')
    app.setDesktopFileName('veil-for-zen');app.setWindowIcon(QIcon(str(Path(__file__).parent/'assets/veil-for-zen.svg')))
    apply_theme(app)
    if not settings_file().exists():
        legacy=Path(args.legacy_dir).expanduser() if args.legacy_dir else find_legacy()
        if legacy:
            answer=QMessageBox.question(None,'Migrar para o Veil?',
                'Foram encontrados dados do Zen Sidebar Studio em:\n'+str(legacy)+'\nCopiar configurações, imagens, presets e histórico? Os originais serão preservados.',
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if answer==QMessageBox.Yes:
                from PySide6.QtCore import QEventLoop,QThreadPool,Qt
                from .ui.preview import Job
                progress=QProgressDialog('Copiando dados antigos…','',0,0)
                progress.setCancelButton(None);progress.setWindowTitle('Veil for Zen');progress.setWindowModality(Qt.ApplicationModal);progress.show()
                loop=QEventLoop();pool=QThreadPool();errors=[]
                job=Job(0,lambda:migrate(legacy))
                def migrated(ident,result,error):
                    if error:errors.append(error)
                    loop.quit()
                job.signals.done.connect(migrated);pool.start(job);loop.exec();pool.waitForDone();progress.close()
                if errors:QMessageBox.warning(None,'Migração não concluída',errors[0])
    window=VeilWindow();window.show()
    return app.exec()

if __name__=='__main__':sys.exit(main())
