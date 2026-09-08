from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import PySide6


BASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_ROOT))

from common import TRANSLATION_DIR


PYSIDE_ROOT = Path(PySide6.__file__).resolve().parent
SOURCE_DIRS = [
    "gui/qml/app",
    "manager",
    "models",
]
SOURCE_SUFFIXES = {".qml", ".py"}


def pysideTool(name: str) -> str:
    return str(PYSIDE_ROOT / f"{name}.exe")


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=BASE_ROOT, check=True)


def sourceFiles() -> list[str]:
    files: list[str] = []
    for sourceDir in SOURCE_DIRS:
        for path in (BASE_ROOT / sourceDir).rglob("*"):
            if path.suffix in SOURCE_SUFFIXES:
                files.append(str(path.relative_to(BASE_ROOT)))
    return sorted(files)


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update Qt translation source files and compile them to .qm files.",
    )
    parser.add_argument(
        "translationFiles",
        nargs="*",
        help="Translation .ts files. Bare file names are resolved under translations/.",
    )
    return parser.parse_args()


def resolveTranslationFile(translationFileName: str) -> Path:
    translationFile = Path(translationFileName)
    if translationFile.is_absolute():
        return translationFile
    if len(translationFile.parts) == 1:
        return TRANSLATION_DIR / translationFile
    return BASE_ROOT / translationFile


def selectedTranslationFiles(translationFileNames: list[str]) -> list[Path]:
    if translationFileNames:
        return [resolveTranslationFile(name) for name in translationFileNames]

    translationFiles = sorted(TRANSLATION_DIR.glob("*.ts"))
    return translationFiles or [TRANSLATION_DIR / "app_zh_CN.ts"]


def main() -> int:
    args = parseArgs()

    for translationFile in selectedTranslationFiles(args.translationFiles):
        translationFile.parent.mkdir(exist_ok=True)
        run([
            pysideTool("lupdate"),
            *sourceFiles(),
            "-ts",
            str(translationFile),
        ])
        run([
            pysideTool("lrelease"),
            str(translationFile),
        ])
    return 0


if __name__ == "__main__":
    sys.exit(main())
