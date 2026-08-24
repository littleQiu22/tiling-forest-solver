from PySide6.QtCore import QObject
from PySide6.QtQml import QmlElement

QML_IMPORT_NAME = "app.manager"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class WorkspaceManager(QObject):
    ...
