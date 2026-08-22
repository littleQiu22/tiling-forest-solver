from __future__ import annotations

import argparse
import html
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


BASE_SIZE = 64
CENTER = BASE_SIZE / 2
ALL_CORNERS = frozenset(("NE", "SE", "SW", "NW"))

DIR_ALIASES = {
    "E": "E",
    "EAST": "E",
    "RIGHT": "E",
    "W": "W",
    "WEST": "W",
    "LEFT": "W",
    "N": "N",
    "NORTH": "N",
    "UP": "N",
    "S": "S",
    "SOUTH": "S",
    "DOWN": "S",
}

CORNER_ALIASES = {
    "EN": "NE",
    "NE": "NE",
    "ES": "SE",
    "SE": "SE",
    "WS": "SW",
    "SW": "SW",
    "WN": "NW",
    "NW": "NW",
}


PALETTE = {
    "ink": "#263238",
    "paper": "#ffffff",
    "grass": "#6c9f70",
    "grassLight": "#82b981",
    "grassDark": "#4f7e55",
    "edgeLight": "#a8c997",
    "edgeDark": "#395b3e",
    "road": "#d9b588",
    "roadLight": "#e8cca3",
    "roadDark": "#9f7954",
    "clearing": "#d5aa7f",
    "clearingLight": "#e4c094",
    "clearingDark": "#936b4d",
    "stump": "#8a563b",
    "stumpCut": "#d7ad72",
    "stumpLight": "#f0cf92",
    "stumpDark": "#51362b",
}


@dataclass(frozen=True)
class TileAssetConfig:
    size: int = BASE_SIZE
    roadDirs: tuple[str, ...] = ()
    clearingCorners: tuple[str, ...] = ()
    stumpDir: str | None = None
    seed: int = 1


def fmt(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def attrs(**values: object) -> str:
    result = []
    for key, value in values.items():
        if value is None:
            continue
        result.append(
            f'{key.replace("_", "-")}="{html.escape(str(value), quote=True)}"')
    return " ".join(result)


def tag(name: str, **values: object) -> str:
    return f"<{name} {attrs(**values)} />"


def pathFromPoints(points: Sequence[tuple[float, float]]) -> str:
    first, *rest = points
    chunks = [f"M {fmt(first[0])} {fmt(first[1])}"]
    chunks.extend(f"L {fmt(x)} {fmt(y)}" for x, y in rest)
    chunks.append("Z")
    return " ".join(chunks)


def jaggedLine(
    start: tuple[float, float],
    end: tuple[float, float],
    rng: random.Random,
    jitter: float,
    steps: int = 7,
) -> list[tuple[float, float]]:
    sx, sy = start
    ex, ey = end
    horizontal = abs(ex - sx) >= abs(ey - sy)
    points = []
    for index in range(steps + 1):
        t = index / steps
        x = sx + (ex - sx) * t
        y = sy + (ey - sy) * t
        if index not in (0, steps):
            offset = rng.uniform(-jitter, jitter)
            if horizontal:
                y += offset
            else:
                x += offset
        points.append((x, y))
    return points


def logoSvg(size: int = BASE_SIZE) -> str:
    lines = []
    for i in range(5):
        p = 6 + i * 13
        lines.append(tag("line", x1=p, y1=6, x2=p, y2=58,
                     stroke=PALETTE["ink"], stroke_width=2))
        lines.append(tag("line", x1=6, y1=p, x2=58, y2=p,
                     stroke=PALETTE["ink"], stroke_width=2))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="10" fill="{PALETTE['paper']}"/>
  <rect x="6" y="6" width="52" height="52" rx="3" fill="none" stroke="{PALETTE['ink']}" stroke-width="3"/>
  {" ".join(lines)}
</svg>
"""


def tileHeader(size: int) -> list[str]:
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64" shape-rendering="crispEdges">',
        tag("rect", x=0, y=0, width=BASE_SIZE,
            height=BASE_SIZE, fill=PALETTE["grass"]),
    ]


def addTileBevel(lines: list[str]) -> None:
    lines.append(tag("rect", x=0, y=0, width=BASE_SIZE, height=1,
                 fill=PALETTE["edgeLight"], opacity="0.35"))
    lines.append(tag("rect", x=0, y=0, width=1, height=BASE_SIZE,
                 fill=PALETTE["edgeLight"], opacity="0.22"))
    lines.append(tag("rect", x=0, y=BASE_SIZE - 3, width=BASE_SIZE,
                 height=3, fill=PALETTE["edgeDark"], opacity="0.36"))
    lines.append(tag("rect", x=BASE_SIZE - 2, y=0, width=2,
                 height=BASE_SIZE, fill=PALETTE["edgeDark"], opacity="0.22"))


def addGrassTexture(lines: list[str], seed: int, count: int = 160) -> None:
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randrange(1, BASE_SIZE - 2)
        y = rng.randrange(2, BASE_SIZE - 4)
        w = rng.choice((1, 1, 2, 2, 3))
        h = rng.choice((1, 1, 2))
        color = PALETTE["grassLight"] if rng.random(
        ) < 0.58 else PALETTE["grassDark"]
        opacity = rng.uniform(0.18, 0.50)
        lines.append(tag("rect", x=x, y=y, width=w, height=h,
                     fill=color, opacity=fmt(opacity)))


def addRegion(lines: list[str], points: Sequence[tuple[float, float]], *, kind: str) -> None:
    if kind == "road":
        fill = PALETTE["road"]
        light = PALETTE["roadLight"]
        dark = PALETTE["roadDark"]
    else:
        fill = PALETTE["clearing"]
        light = PALETTE["clearingLight"]
        dark = PALETTE["clearingDark"]

    d = pathFromPoints(points)
    lines.append(tag("path", d=d, fill=dark, opacity="0.30",
                 transform="translate(1 1)"))
    lines.append(tag("path", d=d, fill=fill))
    lines.append(tag("path", d=d, fill=light, opacity="0.16",
                 transform="translate(-0.6 -0.6)"))
    lines.append(tag("path", d=d, fill="none", stroke=dark,
                 stroke_width="1.1", opacity="0.28"))


def addClearingRegions(lines: list[str], corners: Iterable[str], seed: int) -> None:
    corners = frozenset(corners)
    if not corners:
        return

    rng = random.Random(seed)
    jitter = 1.05
    rightHalf = frozenset(("NE", "SE"))
    leftHalf = frozenset(("NW", "SW"))
    topHalf = frozenset(("NW", "NE"))
    bottomHalf = frozenset(("SW", "SE"))

    if corners == ALL_CORNERS:
        addRegion(lines, [(0, 0), (BASE_SIZE, 0), (BASE_SIZE,
                  BASE_SIZE), (0, BASE_SIZE)], kind="clearing")
        return
    if corners == rightHalf:
        inner = jaggedLine((CENTER, BASE_SIZE), (CENTER, 0), rng, jitter)
        addRegion(lines, [(BASE_SIZE, 0), (BASE_SIZE,
                  BASE_SIZE)] + inner, kind="clearing")
        return
    if corners == leftHalf:
        inner = jaggedLine((CENTER, 0), (CENTER, BASE_SIZE), rng, jitter)
        addRegion(lines, [(0, 0)] + inner + [(0, BASE_SIZE)], kind="clearing")
        return
    if corners == topHalf:
        inner = jaggedLine((BASE_SIZE, CENTER), (0, CENTER), rng, jitter)
        addRegion(lines, [(0, 0), (BASE_SIZE, 0)] + inner, kind="clearing")
        return
    if corners == bottomHalf:
        inner = jaggedLine((0, CENTER), (BASE_SIZE, CENTER), rng, jitter)
        addRegion(lines, inner + [(BASE_SIZE, BASE_SIZE),
                  (0, BASE_SIZE)], kind="clearing")
        return

    for corner in sorted(corners):
        if corner == "NE":
            left = jaggedLine((CENTER, CENTER), (CENTER, 0), rng, jitter)
            bottom = jaggedLine((BASE_SIZE, CENTER),
                                (CENTER, CENTER), rng, jitter)
            addRegion(lines, [(BASE_SIZE, 0), (BASE_SIZE, CENTER)
                              ] + bottom[1:] + left[1:], kind="clearing")
        elif corner == "SE":
            top = jaggedLine((CENTER, CENTER),
                             (BASE_SIZE, CENTER), rng, jitter)
            left = jaggedLine((CENTER, BASE_SIZE),
                              (CENTER, CENTER), rng, jitter)
            addRegion(lines, top + [(BASE_SIZE, BASE_SIZE),
                      (CENTER, BASE_SIZE)] + left[1:], kind="clearing")
        elif corner == "SW":
            right = jaggedLine(
                (CENTER, CENTER), (CENTER, BASE_SIZE), rng, jitter)
            top = jaggedLine((0, CENTER), (CENTER, CENTER), rng, jitter)
            addRegion(lines, [(0, BASE_SIZE), (0, CENTER)] +
                      top[1:] + right[1:], kind="clearing")
        elif corner == "NW":
            bottom = jaggedLine((CENTER, CENTER), (0, CENTER), rng, jitter)
            right = jaggedLine((CENTER, 0), (CENTER, CENTER), rng, jitter)
            addRegion(lines, [(0, 0), (CENTER, 0)] +
                      right[1:] + bottom[1:], kind="clearing")


def roadPath(direction: str, width: float, seed: int) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    half = width / 2
    overlap = half + 3
    jitter = 0.85
    if direction == "W":
        top = jaggedLine((0, CENTER - half), (CENTER +
                         overlap, CENTER - half), rng, jitter)
        bottom = jaggedLine((CENTER + overlap, CENTER + half),
                            (0, CENTER + half), rng, jitter)
        return top + bottom
    if direction == "E":
        top = jaggedLine((CENTER - overlap, CENTER - half),
                         (BASE_SIZE, CENTER - half), rng, jitter)
        bottom = jaggedLine((BASE_SIZE, CENTER + half),
                            (CENTER - overlap, CENTER + half), rng, jitter)
        return top + bottom
    if direction == "N":
        left = jaggedLine((CENTER - half, CENTER + overlap),
                          (CENTER - half, 0), rng, jitter)
        right = jaggedLine((CENTER + half, 0), (CENTER +
                           half, CENTER + overlap), rng, jitter)
        return left + right
    if direction == "S":
        left = jaggedLine((CENTER - half, CENTER - overlap),
                          (CENTER - half, BASE_SIZE), rng, jitter)
        right = jaggedLine((CENTER + half, BASE_SIZE),
                           (CENTER + half, CENTER - overlap), rng, jitter)
        return left + right
    raise ValueError(direction)


def addRoads(lines: list[str], directions: Iterable[str], seed: int) -> None:
    directions = frozenset(directions)
    if not directions:
        return

    width = 12.0
    for index, direction in enumerate(("W", "E", "N", "S")):
        if direction in directions:
            addRegion(lines, roadPath(direction, width,
                      seed + index * 29), kind="road")

    radius = width / 2 + 3
    lines.append(tag("circle", cx=CENTER, cy=CENTER, r=fmt(
        radius), fill=PALETTE["roadDark"], opacity="0.28", transform="translate(0.7 0.7)"))
    lines.append(tag("circle", cx=CENTER, cy=CENTER,
                 r=fmt(radius), fill=PALETTE["road"]))
    lines.append(tag("circle", cx=CENTER - 0.6, cy=CENTER - 0.6,
                 r=fmt(radius * 0.70), fill=PALETTE["roadLight"], opacity="0.14"))


def isInsideDirection(x: float, y: float, directions: Iterable[str], width: float) -> bool:
    half = width / 2
    for direction in directions:
        if direction == "W" and x <= CENTER + half and abs(y - CENTER) <= half:
            return True
        if direction == "E" and x >= CENTER - half and abs(y - CENTER) <= half:
            return True
        if direction == "N" and y <= CENTER + half and abs(x - CENTER) <= half:
            return True
        if direction == "S" and y >= CENTER - half and abs(x - CENTER) <= half:
            return True
    return False


def isInsideCorner(x: float, y: float, corners: Iterable[str]) -> bool:
    for corner in corners:
        if corner == "NE" and x >= CENTER and y <= CENTER:
            return True
        if corner == "SE" and x >= CENTER and y >= CENTER:
            return True
        if corner == "SW" and x <= CENTER and y >= CENTER:
            return True
        if corner == "NW" and x <= CENTER and y <= CENTER:
            return True
    return False


def addGroundTexture(lines: list[str], *, directions: Iterable[str], corners: Iterable[str], seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(34):
        x = rng.uniform(2, BASE_SIZE - 4)
        y = rng.uniform(3, BASE_SIZE - 6)
        if not (isInsideDirection(x, y, directions, 14) or isInsideCorner(x, y, corners)):
            continue
        color = PALETTE["roadLight"] if rng.random(
        ) < 0.42 else PALETTE["roadDark"]
        opacity = rng.uniform(0.20, 0.42)
        lines.append(tag("rect", x=fmt(x), y=fmt(y), width=fmt(
            rng.uniform(1, 3)), height=1, fill=color, opacity=fmt(opacity)))


def arrowPoints(direction: str) -> list[tuple[float, float]]:
    if direction == "E":
        return [(20, 29), (39, 29), (39, 24), (51, 32), (39, 40), (39, 35), (20, 35)]
    if direction == "W":
        return [(44, 29), (25, 29), (25, 24), (13, 32), (25, 40), (25, 35), (44, 35)]
    if direction == "N":
        return [(29, 44), (29, 25), (24, 25), (32, 13), (40, 25), (35, 25), (35, 44)]
    if direction == "S":
        return [(29, 20), (29, 39), (24, 39), (32, 51), (40, 39), (35, 39), (35, 20)]
    raise ValueError(direction)


def addStump(lines: list[str], direction: str, seed: int) -> None:
    rng = random.Random(seed)
    lines.append(tag("ellipse", cx=34, cy=36, rx=23, ry=20,
                 fill=PALETTE["edgeDark"], opacity="0.22"))
    lines.append(tag("circle", cx=32, cy=32, r=24, fill=PALETTE["stumpDark"]))
    lines.append(tag("circle", cx=31, cy=30, r=23, fill=PALETTE["stump"]))

    for index in range(22):
        angle = math.radians(index * 360 / 22 + rng.uniform(-5, 5))
        outer = rng.uniform(20, 23)
        inner = outer - rng.uniform(3, 6)
        x1 = 31 + outer * math.cos(angle)
        y1 = 30 + outer * math.sin(angle)
        x2 = 31 + inner * math.cos(angle)
        y2 = 30 + inner * math.sin(angle)
        lines.append(tag("path", d=f"M {fmt(x1)} {fmt(y1)} L {fmt(x2)} {fmt(y2)}",
                     stroke=PALETTE["stumpLight"], stroke_width="1", opacity=fmt(rng.uniform(0.14, 0.30))))

    lines.append(tag("circle", cx=32, cy=32, r=19,
                 fill=PALETTE["clearingDark"]))
    lines.append(tag("circle", cx=31, cy=30, r=19, fill=PALETTE["stumpCut"]))
    lines.append(tag("ellipse", cx=25, cy=23, rx=10, ry=5,
                 fill=PALETTE["stumpLight"], opacity="0.28"))
    for radius, opacity, width in ((14, 0.46, 1.35), (10, 0.40, 1.15), (6, 0.36, 1.0), (3, 0.38, 0.9)):
        lines.append(tag("ellipse", cx=31 + rng.uniform(-0.5, 0.5), cy=30 + rng.uniform(-0.5, 0.5), rx=radius, ry=fmt(radius *
                     rng.uniform(0.78, 0.92)), fill="none", stroke=PALETTE["stumpDark"], stroke_width=fmt(width), opacity=fmt(opacity)))

    points = [(32 + (x - 32) * 0.82, 32 + (y - 32) * 0.82)
              for x, y in arrowPoints(direction)]
    lines.append(tag("path", d=pathFromPoints(points),
                 fill=PALETTE["stumpDark"], opacity="0.92"))
    lines.append(tag("path", d=pathFromPoints(points), fill="none",
                 stroke=PALETTE["stumpLight"], stroke_width="0.9", opacity="0.34"))


def tileSvg(config: TileAssetConfig) -> str:
    lines = tileHeader(config.size)
    addGrassTexture(lines, config.seed)
    addTileBevel(lines)
    if config.stumpDir is not None:
        addStump(lines, config.stumpDir, config.seed + 300)
    else:
        addClearingRegions(lines, config.clearingCorners, config.seed + 100)
        addRoads(lines, config.roadDirs, config.seed + 200)
        addGroundTexture(lines, directions=config.roadDirs,
                         corners=config.clearingCorners, seed=config.seed + 400)
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def renderPng(svgText: str, pngPath: Path, size: int) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication([])
    _ = app

    renderer = QSvgRenderer(QByteArray(svgText.encode("utf-8")))
    if not renderer.isValid():
        raise RuntimeError("Generated SVG is invalid")

    image = QImage(QSize(size, size),
                   QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(Qt.GlobalColor.transparent))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    pngPath.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(pngPath), "PNG"):
        raise RuntimeError(f"Could not write PNG: {pngPath}")


def normalizeDirs(rawDirs: Iterable[str]) -> tuple[str, ...]:
    result = []
    for rawDir in rawDirs:
        key = rawDir.upper()
        if key not in DIR_ALIASES:
            raise ValueError(f"Unknown direction: {rawDir}")
        result.append(DIR_ALIASES[key])
    return tuple(dict.fromkeys(result))


def normalizeCorners(rawCorners: Iterable[str], fullClearing: bool) -> tuple[str, ...]:
    if fullClearing:
        return tuple(sorted(ALL_CORNERS))
    result = []
    for rawCorner in rawCorners:
        key = rawCorner.upper()
        if key not in CORNER_ALIASES:
            raise ValueError(f"Unknown clearing corner: {rawCorner}")
        result.append(CORNER_ALIASES[key])
    return tuple(dict.fromkeys(result))


def writeText(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate one configurable tile asset.")
    parser.add_argument("--output-svg")
    parser.add_argument("--output-png")
    parser.add_argument("--size", type=int, default=BASE_SIZE)
    parser.add_argument("--road-dir", action="append", default=[])
    parser.add_argument("--clearing-corner", action="append", default=[])
    parser.add_argument("--full-clearing", action="store_true")
    parser.add_argument("--stump-dir")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    if not args.output_svg and not args.output_png:
        parser.error(
            "at least one of --output-svg or --output-png is required")

    stumpDir = normalizeDirs([args.stump_dir])[0] if args.stump_dir else None
    config = TileAssetConfig(
        size=args.size,
        roadDirs=normalizeDirs(args.road_dir),
        clearingCorners=normalizeCorners(
            args.clearing_corner, args.full_clearing),
        stumpDir=stumpDir,
        seed=args.seed,
    )
    svgText = tileSvg(config)
    if args.output_svg:
        writeText(Path(args.output_svg), svgText)
    if args.output_png:
        renderPng(svgText, Path(args.output_png), args.size)
    return 0


if __name__ == "__main__":
    main()
