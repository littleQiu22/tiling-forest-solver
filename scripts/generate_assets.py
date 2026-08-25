from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_ROOT = Path(__file__).resolve().parents[1]
if str(BASE_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_ROOT))

from common import ASSET_ROOT
from models.tile import TILE
from scripts.generate_tile_asset import TileAssetConfig, logoSvg, renderPng, tileSvg


TileSpec = tuple[tuple[str, ...], tuple[str, ...], str | None]


TILE_SPECS: dict[str, TileSpec] = {
    "GRASSLAND": ((), (), None),
    "ROAD_WS": (("W", "S"), (), None),
    "ROAD_WE": (("W", "E"), (), None),
    "ROAD_WN": (("W", "N"), (), None),
    "ROAD_ES": (("E", "S"), (), None),
    "ROAD_EN": (("E", "N"), (), None),
    "ROAD_NS": (("N", "S"), (), None),
    "ROAD_E": (("E",), (), None),
    "ROAD_W": (("W",), (), None),
    "ROAD_N": (("N",), (), None),
    "ROAD_S": (("S",), (), None),
    "CLEARING": ((), ("NE", "SE", "SW", "NW"), None),
    "CLEARING_EN": ((), ("NE",), None),
    "CLEARING_ES": ((), ("SE",), None),
    "CLEARING_WS": ((), ("SW",), None),
    "CLEARING_WN": ((), ("NW",), None),
    "CLEARING_E": ((), ("NE", "SE"), None),
    "CLEARING_W": ((), ("NW", "SW"), None),
    "CLEARING_S": ((), ("SW", "SE"), None),
    "CLEARING_N": ((), ("NW", "NE"), None),
    "CLEARING_E_ROAD_W": (("W",), ("NE", "SE"), None),
    "CLEARING_W_ROAD_E": (("E",), ("NW", "SW"), None),
    "CLEARING_S_ROAD_N": (("N",), ("SW", "SE"), None),
    "CLEARING_N_ROAD_S": (("S",), ("NW", "NE"), None),
    "STUMP_W": ((), (), "W"),
    "STUMP_E": ((), (), "E"),
    "STUMP_N": ((), (), "N"),
    "STUMP_S": ((), (), "S"),
}


def writeText(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def tileAssetStem(typeName: str) -> str:
    if typeName == "GRASSLAND":
        return "grassland"
    if typeName == "CLEARING":
        return "clearing"
    prefix, _, suffix = typeName.partition("_")
    return f"{prefix.lower()}_{suffix}"


def validateTileSpecs() -> None:
    expected = set(TILE.TYPE.__members__)
    actual = set(TILE_SPECS)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise RuntimeError(
            f"Tile asset specs are out of sync. Missing={missing}, extra={extra}")


def tileSvgForType(typeName: str, size: int) -> str:
    roadDirs, clearingCorners, stumpDir = TILE_SPECS[typeName]
    return tileSvg(
        TileAssetConfig(
            size=size,
            roadDirs=roadDirs,
            clearingCorners=clearingCorners,
            stumpDir=stumpDir,
            seed=TILE.TYPE[typeName].value * 17,
        )
    )


def writeOptionalSvg(path: Path, text: str, shouldWrite: bool) -> None:
    if shouldWrite:
        writeText(path, text)


def assetsQml(mapping: dict[str, str]) -> str:
    lines = [
        "pragma Singleton",
        "import QtQuick",
        "",
        "import app.models",
        "",
        "QtObject {",
        "    id: root",
        "",
        '    readonly property url logo: Qt.resolvedUrl("assets/logo.png")',
        "    readonly property int tileSize: TileSpec.size",
        "",
        "    function tileImage(tile) {",
        "        switch (tile) {",
    ]
    for typeName, path in mapping.items():
        lines.extend([
            f"        case Tile.{typeName}:",
            f'            return Qt.resolvedUrl("assets/{path}");',
        ])
    lines.extend([
        "        default:",
        '            return "";',
        "        }",
        "    }",
        "}",
        "",
    ])
    return "\n".join(lines)


def generateAssets(size: int, *, shouldWriteSvg: bool = False) -> None:
    validateTileSpecs()

    logoText = logoSvg(size)
    writeOptionalSvg(ASSET_ROOT / "logo.svg", logoText, shouldWriteSvg)
    renderPng(logoText, ASSET_ROOT / "logo.png", size)

    mapping: dict[str, str] = {}
    for typeName in TILE.TYPE.__members__:
        stem = tileAssetStem(typeName)
        svgText = tileSvgForType(typeName, size)
        writeOptionalSvg(ASSET_ROOT / "tiles" / f"{stem}.svg", svgText, shouldWriteSvg)
        renderPng(svgText, ASSET_ROOT / "tiles" / f"{stem}.png", size)
        mapping[typeName] = f"tiles/{stem}.png"

    writeText(ASSET_ROOT / "tiles" / "tile_assets.json",
              json.dumps(mapping, indent=2) + "\n")
    writeText(BASE_ROOT / "gui" / "qml" / "app" / "Assets.qml", assetsQml(mapping))


def main():
    parser = argparse.ArgumentParser(
        description="Generate project image assets.")
    parser.add_argument("--size", type=int, default=TILE.SIZE)
    parser.add_argument("--write-svg", action="store_true")
    args = parser.parse_args()

    generateAssets(args.size, shouldWriteSvg=args.write_svg)


if __name__ == "__main__":
    main()
