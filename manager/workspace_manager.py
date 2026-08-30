from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtQml import QmlElement

from common import TEMPLATE_DIR
from models.workspace import Workspace


QML_IMPORT_NAME = "app.manager"
QML_IMPORT_MAJOR_VERSION = 1
COMPACT_JSON_KEYS = {"tiles", "emptyGrids", "placedGrids", "tilePool"}


def dumpsWorkspaceJson(data: dict[str, Any]) -> str:
    return _dumpsJson(data, 0, None) + "\n"


def _dumpsJson(value: Any, level: int, key: str | None) -> str:
    if key in COMPACT_JSON_KEYS:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(", ", ": "),
        )

    if isinstance(value, dict):
        if not value:
            return "{}"
        indent = "  " * level
        childIndent = "  " * (level + 1)
        lines = ["{"]
        items = sorted(value.items())
        for index, (childKey, childValue) in enumerate(items):
            comma = "," if index < len(items) - 1 else ""
            keyText = json.dumps(childKey, ensure_ascii=False)
            valueText = _dumpsJson(childValue, level + 1, str(childKey))
            lines.append(f"{childIndent}{keyText}: {valueText}{comma}")
        lines.append(f"{indent}}}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"
        indent = "  " * level
        childIndent = "  " * (level + 1)
        lines = ["["]
        for index, item in enumerate(value):
            comma = "," if index < len(value) - 1 else ""
            lines.append(f"{childIndent}{_dumpsJson(item, level + 1, None)}{comma}")
        lines.append(f"{indent}]")
        return "\n".join(lines)

    return json.dumps(value, ensure_ascii=False)


@QmlElement
class WorkspaceManager(QObject):
    filePathChanged = Signal()
    templateNameChanged = Signal()
    displayNameChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workspace = Workspace(self)
        self._filePath = ""
        self._templateName = ""
        self._templates = self._discoverTemplates()

    @Property(QObject, constant=True)
    def workspace(self) -> Workspace:
        return self._workspace

    @Property(str, notify=filePathChanged)
    def filePath(self) -> str:
        return self._filePath

    @Property(str, notify=templateNameChanged)
    def templateName(self) -> str:
        return self._templateName

    @Property(str, notify=displayNameChanged)
    def displayName(self) -> str:
        if self._filePath:
            return self._filePath
        if self._templateName:
            return self._templateName
        return "Untitled"

    @Property("QStringList", constant=True)
    def templates(self) -> list[str]:
        return self._templates

    @Slot()
    def new(self) -> None:
        self._workspace.newDocument()
        self._setFilePath("")
        self._setTemplateName("")

    @Slot(result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def save(self, filePath: str | None = None) -> dict[str, Any]:
        path = self._filePath if filePath is None else str(filePath)
        return self._saveToPath(path)

    @Slot(str, result="QVariantMap")
    def load(self, filePath: str) -> dict[str, Any]:
        path = str(filePath)
        if not path:
            return self._response(False, "No file path was provided.")

        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self._workspace.loadJson(data)
            self._setFilePath(path)
            self._setTemplateName("")
        except Exception as error:
            return self._response(False, f"Failed to load workspace: {error}")

        return self._response(True, "")

    @Slot(str, result="QVariantMap")
    def loadTemplate(self, templateName: str) -> dict[str, Any]:
        templatePath = self._templatePath(templateName)
        if templatePath is None:
            return self._response(False, f"Template not found: {templateName}")

        try:
            data = json.loads(templatePath.read_text(encoding="utf-8"))
            self._workspace.loadJson(data)
            self._setFilePath("")
            self._setTemplateName(templatePath.stem)
        except Exception as error:
            return self._response(False, f"Failed to load template: {error}")

        return self._response(True, "")

    @Slot(result="QVariantMap")
    def revert(self) -> dict[str, Any]:
        if self._filePath:
            return self.load(self._filePath)
        if self._templateName:
            return self.loadTemplate(self._templateName)

        self._workspace.newDocument()
        return self._response(True, "")

    def _saveToPath(self, path: str) -> dict[str, Any]:
        if not path:
            return self._response(False, "No file path was provided.")

        try:
            filePath = Path(path)
            filePath.parent.mkdir(parents=True, exist_ok=True)
            filePath.write_text(
                dumpsWorkspaceJson(self._workspace.toJson()),
                encoding="utf-8",
            )
            self._setFilePath(str(filePath))
            self._setTemplateName("")
            self._workspace.markClean()
        except Exception as error:
            return self._response(False, f"Failed to save workspace: {error}")

        return self._response(True, "")

    def _setFilePath(self, filePath: str) -> None:
        if self._filePath == filePath:
            return
        self._filePath = filePath
        self.filePathChanged.emit()
        self.displayNameChanged.emit()

    def _setTemplateName(self, templateName: str) -> None:
        if self._templateName == templateName:
            return
        self._templateName = templateName
        self.templateNameChanged.emit()
        self.displayNameChanged.emit()

    def _discoverTemplates(self) -> list[str]:
        if not TEMPLATE_DIR.exists():
            return []
        return sorted(path.stem for path in TEMPLATE_DIR.glob("*.json"))

    def _templatePath(self, templateName: str) -> Path | None:
        if not TEMPLATE_DIR.exists():
            return None

        directPath = TEMPLATE_DIR / templateName
        if directPath.suffix.lower() != ".json":
            directPath = directPath.with_suffix(".json")
        return directPath if directPath.exists() else None

    def _response(self, status: bool, message: str) -> dict[str, Any]:
        return {"status": status, "message": message}
