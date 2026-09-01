import sys
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


def solverWorkerMain() -> int:
    from solver.worker import main as workerMain
    return workerMain()


if __name__ == "__main__" and "--solver-worker" in sys.argv:
    sys.exit(solverWorkerMain())


import models.tile
import manager.workspace_manager
import models.workspace
from common import getAsset, getQML
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtCore import QCoreApplication, QSettings


def configure_application() -> None:
    QCoreApplication.setOrganizationName("littleQJY")
    QCoreApplication.setOrganizationDomain("littleQJY.toy")
    QCoreApplication.setApplicationName("TilingForestSolver")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)


def createQmlEngine() -> QQmlApplicationEngine:
    engine = QQmlApplicationEngine()
    engine.addImportPath(getQML())
    engine.loadFromModule("app", "Main")
    return engine


def main() -> int:
    app = QGuiApplication(sys.argv)
    configure_application()
    app.setWindowIcon(QIcon(getAsset("logo.png")))

    engine = createQmlEngine()
    if not engine.rootObjects():
        return 1

    app.aboutToQuit.connect(engine.deleteLater)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
