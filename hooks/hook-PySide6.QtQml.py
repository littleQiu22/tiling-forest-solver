from __future__ import annotations

from pathlib import Path, PurePath

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)


QML_IMPORTS = [
    "QtCore",
    "QtQml",
    "QtQml/Models",
    "QtQuick",
    "QtQuick/Window",
    "QtQuick/Templates",
    "QtQuick/Controls",
    "QtQuick/Controls/Basic",
    "QtQuick/Controls/Basic/impl",
    "QtQuick/Controls/impl",
    "QtQuick/Dialogs",
    "QtQuick/Dialogs/quickimpl",
    "QtQuick/Layouts",
    "QtQuick/Shapes",
]


def qmlRoot() -> Path | None:
    if pyside6_library_info.version is None:
        return None

    location = pyside6_library_info.location
    qmlPath = location.get("QmlImportsPath") or location.get("Qml2ImportsPath")
    if not qmlPath:
        return None

    root = Path(qmlPath).resolve()
    return root if root.exists() else None


def qmlDestination(root: Path, source: Path) -> str:
    if source.is_dir():
        relativePath = source.relative_to(root)
    else:
        relativePath = source.relative_to(root).parent
    return str(PurePath(pyside6_library_info.qt_rel_dir) / "qml" / relativePath)


root = qmlRoot()
if root is not None:
    for importPath in QML_IMPORTS:
        qmldir = root / importPath / "qmldir"
        if not qmldir.exists():
            continue

        pluginBinaries, pluginDatas = pyside6_library_info._process_qml_plugin(qmldir)
        binaries += [(str(path), qmlDestination(root, path)) for path in pluginBinaries]
        datas += [(str(path), qmlDestination(root, path)) for path in pluginDatas]
