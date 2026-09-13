from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STUB_ROOT = PROJECT_ROOT / "packaging_stubs"
DEFAULT_APP_NAME = "TilingForestSolver"


def addDataArg(source: Path, destination: str) -> str:
    return f"{source}{os.pathsep}{destination}"


def packageRoot(packageName: str) -> Path | None:
    spec = importlib.util.find_spec(packageName)
    if spec is None or spec.origin is None:
        return None
    return Path(spec.origin).parent


def sharedLibraryFiles(root: Path) -> list[Path]:
    suffixes = {".dll", ".dylib", ".so"}
    return [
        path
        for path in root.iterdir()
        if path.is_file() and (path.suffix.lower() in suffixes or ".so." in path.name)
    ]


def addPackageBinaryArgs(packageName: str, binaryNames: list[str], destination: str) -> list[str]:
    root = packageRoot(packageName)
    if root is None:
        return []

    args: list[str] = []
    for binaryName in binaryNames:
        binary = root / binaryName
        if binary.exists():
            args.extend(["--add-binary", addDataArg(binary, destination)])
    return args


def ortoolsBinaryArgs() -> list[str]:
    root = packageRoot("ortools")
    if root is None:
        return []

    libsRoot = root / ".libs"
    if not libsRoot.exists():
        return []

    args: list[str] = []
    for binary in sharedLibraryFiles(libsRoot):
        args.extend(["--add-binary", addDataArg(binary, "ortools/.libs")])
    return args


def pysideRuntimeBinaryArgs() -> list[str]:
    return addPackageBinaryArgs("PySide6", [
        "concrt140.dll",
        "msvcp140_codecvt_ids.dll",
        "vcamp140.dll",
        "vccorlib140.dll",
        "vcomp140.dll",
    ], "PySide6")


def buildEnvironment() -> dict[str, str]:
    env = os.environ.copy()
    if os.name != "nt":
        return env

    systemRoot = Path(env.get("SystemRoot", "C:/Windows"))
    pathEntries = [
        Path(sys.executable).parent,
        systemRoot / "System32",
        systemRoot,
    ]
    env["PATH"] = os.pathsep.join(str(path) for path in pathEntries)
    return env


def run(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, env=buildEnvironment())


def platformName() -> str:
    return {
        "Darwin": "macOS",
        "Windows": "Windows",
    }.get(platform.system(), platform.system() or "Unknown")


def createArchive(appName: str, outputDir: Path) -> Path:
    archiveBase = outputDir / f"{appName}-{platformName()}"
    archivePath = archiveBase.with_suffix(".zip")
    archivePath.unlink(missing_ok=True)
    shutil.make_archive(str(archiveBase), "zip", outputDir, appName)
    return archivePath


def removePath(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def prunePackagedApp(appName: str, outputDir: Path) -> None:
    appRoot = outputDir / appName
    internalRoot = appRoot / "_internal"
    if not internalRoot.exists():
        internalRoot = appRoot

    pysideRoot = internalRoot / "PySide6"
    removePath(pysideRoot / "translations")
    removePath(pysideRoot / "plugins" / "imageformats")
    removePath(pysideRoot / "plugins" / "tls")
    removePath(pysideRoot / "opengl32sw.dll")
    removePath(pysideRoot / "QtOpenGL.pyd")
    removePath(pysideRoot / "Qt6Pdf.dll")
    removePath(pysideRoot / "Qt6Svg.dll")
    removePath(pysideRoot / "Qt6VirtualKeyboard.dll")
    removePath(pysideRoot / "Qt6Quick3DUtils.dll")

    removePath(internalRoot / "libcrypto-3-x64.dll")
    removePath(internalRoot / "libssl-3-x64.dll")
    removePath(internalRoot / "pandas.libs")

    qmlRoot = pysideRoot / "qml"
    if qmlRoot.exists():
        for typeInfo in qmlRoot.rglob("plugins.qmltypes"):
            removePath(typeInfo)
        for designerDir in qmlRoot.rglob("designer"):
            removePath(designerDir)


def buildPackage(appName: str, outputDir: Path, clean: bool, archive: bool, console: bool) -> None:
    workDir = PROJECT_ROOT / "build" / appName
    specDir = PROJECT_ROOT / "build" / "spec"

    if clean:
        shutil.rmtree(outputDir / appName, ignore_errors=True)
        shutil.rmtree(workDir, ignore_errors=True)
        shutil.rmtree(specDir, ignore_errors=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--console" if console else "--windowed",
        "--name",
        appName,
        "--distpath",
        str(outputDir),
        "--workpath",
        str(workDir),
        "--specpath",
        str(specDir),
        "--paths",
        str(STUB_ROOT),
        "--paths",
        str(PROJECT_ROOT),
        "--additional-hooks-dir",
        str(PROJECT_ROOT / "hooks"),
        "--hidden-import",
        "PySide6.QtQuick",
        "--hidden-import",
        "PySide6.QtQuickControls2",
        "--collect-submodules",
        "manager",
        "--collect-submodules",
        "models",
        "--collect-submodules",
        "solver",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "scipy",
        "--exclude-module",
        "IPython",
        "--exclude-module",
        "pyarrow",
        "--exclude-module",
        "numba",
        "--exclude-module",
        "PySide6.Qt3DAnimation",
        "--exclude-module",
        "PySide6.Qt3DCore",
        "--exclude-module",
        "PySide6.Qt3DExtras",
        "--exclude-module",
        "PySide6.Qt3DInput",
        "--exclude-module",
        "PySide6.Qt3DLogic",
        "--exclude-module",
        "PySide6.Qt3DRender",
        "--exclude-module",
        "PySide6.QtCharts",
        "--exclude-module",
        "PySide6.QtDataVisualization",
        "--exclude-module",
        "PySide6.QtGraphs",
        "--exclude-module",
        "PySide6.QtLocation",
        "--exclude-module",
        "PySide6.QtMultimedia",
        "--exclude-module",
        "PySide6.QtPdf",
        "--exclude-module",
        "PySide6.QtPositioning",
        "--exclude-module",
        "PySide6.QtRemoteObjects",
        "--exclude-module",
        "PySide6.QtScxml",
        "--exclude-module",
        "PySide6.QtSensors",
        "--exclude-module",
        "PySide6.QtSpatialAudio",
        "--exclude-module",
        "PySide6.QtTextToSpeech",
        "--exclude-module",
        "PySide6.QtWebChannel",
        "--exclude-module",
        "PySide6.QtWebEngineCore",
        "--exclude-module",
        "PySide6.QtWebEngineQuick",
        "--exclude-module",
        "PySide6.QtWebEngineWidgets",
        "--exclude-module",
        "PySide6.QtWebSockets",
        "--exclude-module",
        "PySide6.QtWebView",
        "--add-data",
        addDataArg(PROJECT_ROOT / "gui" / "qml", "gui/qml"),
        "--add-data",
        addDataArg(PROJECT_ROOT / "templates", "templates"),
        "--add-data",
        addDataArg(PROJECT_ROOT / "translations", "translations"),
        "--add-data",
        addDataArg(PROJECT_ROOT / "LICENSE", "."),
        *pysideRuntimeBinaryArgs(),
        *ortoolsBinaryArgs(),
        str(PROJECT_ROOT / "main.py"),
    ]

    run(command)
    prunePackagedApp(appName, outputDir)
    if archive:
        archivePath = createArchive(appName, outputDir)
        print(f"Archive written to {archivePath}", flush=True)


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local PyInstaller package for Tiling Forest Solver.",
    )
    parser.add_argument(
        "--name",
        default=DEFAULT_APP_NAME,
        help=f"Application/package name. Defaults to {DEFAULT_APP_NAME}.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "dist",
        help="Directory that receives the packaged application.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous build output for this application before packaging.",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Skip creating a zip archive after packaging.",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Build with a console window for packaging diagnostics.",
    )
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    buildPackage(
        appName=args.name,
        outputDir=args.output_dir.resolve(),
        clean=args.clean,
        archive=not args.no_archive,
        console=args.console,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
