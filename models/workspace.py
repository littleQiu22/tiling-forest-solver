from PySide6.QtCore import QObject
from PySide6.QtQml import QmlElement

QML_IMPORT_NAME = "app.models"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class Workspace(QObject):
    ...
