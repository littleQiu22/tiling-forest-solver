import sys

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from common import getQML
# QML-decorated Python types
import models.tile


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

    engine = createQmlEngine()
    if not engine.rootObjects():
        return 1

    ex = app.exec()
    del engine
    return ex


if __name__ == "__main__":
    sys.exit(main())
