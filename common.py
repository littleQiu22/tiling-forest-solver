import sys
from pathlib import Path
import posixpath

_IS_RELEASE = getattr(sys, "frozen", False)

if _IS_RELEASE:
    _BASE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    _QML_ROOT = _BASE_ROOT / "gui" / "qml"
else:
    _BASE_ROOT = Path(__file__).parent
    _QML_ROOT = _BASE_ROOT / "gui" / "qml"


def _joinPath(root: Path | str, *paths: str) -> str:
    if isinstance(root, Path):
        return str(root.joinpath(*paths).resolve())
    else:
        return posixpath.join(root, *paths)


def getQML(*paths: str):
    return _joinPath(_QML_ROOT, *paths)
