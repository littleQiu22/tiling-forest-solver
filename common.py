import sys
from pathlib import Path

_IS_RELEASE = getattr(sys, "frozen", False)

if _IS_RELEASE:
    BASE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    BASE_ROOT = Path(__file__).parent

QML_ROOT = BASE_ROOT / "gui" / "qml"
ASSET_ROOT = QML_ROOT / "app" / "assets"


def _joinPath(root: Path, *paths: str) -> str:
    return str(root.joinpath(*paths).resolve())


def getQML(*paths: str):
    return _joinPath(QML_ROOT, *paths)


def getAsset(*paths: str):
    return _joinPath(ASSET_ROOT, *paths)
