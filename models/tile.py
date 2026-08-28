from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from PySide6.QtCore import (
    QByteArray,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Property,
    QEnum,
    Qt,
)
from PySide6.QtQml import QmlNamedElement, QmlSingleton, QmlUncreatable

from models.geometry import BoundingBox, Grid


QML_IMPORT_NAME = "app.models"
QML_IMPORT_MAJOR_VERSION = 1
TILE_SIZE = 64


@QmlNamedElement("Tile")
@QmlUncreatable("Tile enums only")
class TILE(QObject):
    SIZE = TILE_SIZE

    class STATUS(Enum):
        NORMAL = 1
        UNEXPLORED = 2
        BLOOMING = 3
    QEnum(STATUS)

    class TYPE(Enum):
        GRASSLAND = 1

        ROAD_WS = 11
        ROAD_WE = 12
        ROAD_WN = 13
        ROAD_ES = 14
        ROAD_EN = 15
        ROAD_NS = 16
        ROAD_E = 17
        ROAD_W = 18
        ROAD_N = 19
        ROAD_S = 20

        CLEARING_EN = 21
        CLEARING_ES = 22
        CLEARING_WS = 23
        CLEARING_WN = 24
        CLEARING_E = 25
        CLEARING_W = 26
        CLEARING_S = 27
        CLEARING_N = 28
        CLEARING = 29

        CLEARING_E_ROAD_W = 31
        CLEARING_W_ROAD_E = 32
        CLEARING_S_ROAD_N = 33
        CLEARING_N_ROAD_S = 34

        STUMP_W = 41
        STUMP_E = 42
        STUMP_N = 43
        STUMP_S = 44
    QEnum(TYPE)

    STUMPS = {TYPE.STUMP_W, TYPE.STUMP_E, TYPE.STUMP_N, TYPE.STUMP_S}
    MIXED_CLEARING_ROADS = {
        TYPE.CLEARING_E_ROAD_W,
        TYPE.CLEARING_W_ROAD_E,
        TYPE.CLEARING_N_ROAD_S,
        TYPE.CLEARING_S_ROAD_N,
    }
    SIMPLE_ROADS = {
        TYPE.ROAD_WS,
        TYPE.ROAD_WN,
        TYPE.ROAD_EN,
        TYPE.ROAD_ES,
        TYPE.ROAD_WE,
        TYPE.ROAD_NS,
        TYPE.ROAD_E,
        TYPE.ROAD_W,
        TYPE.ROAD_N,
        TYPE.ROAD_S,
    }
    ROADS = SIMPLE_ROADS | MIXED_CLEARING_ROADS
    SIMPLE_CLEARINGS = {
        TYPE.CLEARING_EN,
        TYPE.CLEARING_ES,
        TYPE.CLEARING_WN,
        TYPE.CLEARING_WS,
        TYPE.CLEARING_E,
        TYPE.CLEARING_S,
        TYPE.CLEARING_W,
        TYPE.CLEARING_N,
        TYPE.CLEARING,
    }
    CLEARINGS = SIMPLE_CLEARINGS | MIXED_CLEARING_ROADS


@QmlNamedElement("TileSpec")
@QmlSingleton
class TileSpec(QObject):
    @Property(int, constant=True)
    def size(self) -> int:
        return TILE.SIZE


@dataclass(slots=True)
class TileData:
    row: int
    col: int
    tile: TILE.TYPE
    status: TILE.STATUS = TILE.STATUS.NORMAL
    index: int = field(default=-1, compare=False)

    @property
    def grid(self) -> Grid:
        return Grid(self.row, self.col)

    def toJson(self) -> dict[str, Any]:
        return {
            "row": self.row,
            "col": self.col,
            "tile": self.tile.name,
            "status": self.status.name,
        }

    @classmethod
    def fromJson(cls, data: dict[str, Any]) -> "TileData":
        return cls(
            row=int(data["row"]),
            col=int(data["col"]),
            tile=tileTypeFromJson(data["tile"]),
            status=tileStatusFromJson(
                data.get("status", TILE.STATUS.NORMAL.name)),
        )


def tileTypeFromQml(value: int) -> TILE.TYPE:
    return TILE.TYPE(int(value))


def tileStatusFromQml(value: int) -> TILE.STATUS:
    return TILE.STATUS(int(value))


def tileTypeFromJson(name: str) -> TILE.TYPE:
    return TILE.TYPE[str(name)]


def tileStatusFromJson(name: str) -> TILE.STATUS:
    return TILE.STATUS[str(name)]


@QmlNamedElement("TileListModel")
@QmlUncreatable("Use Workspace.tiles")
class TileListModel(QAbstractListModel):
    RowRole = Qt.ItemDataRole.UserRole.value + 1
    ColRole = RowRole + 1
    TileRole = RowRole + 2
    StatusRole = RowRole + 3

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tiles: list[TileData] = []
        self._tileByGrid: dict[Grid, TileData] = {}
        self._boundingBox = BoundingBox()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._tiles)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._tiles):
            return None

        tile = self._tiles[index.row()]
        match role:
            case self.RowRole:
                return tile.row
            case self.ColRole:
                return tile.col
            case self.TileRole:
                return tile.tile.value
            case self.StatusRole:
                return tile.status.value
            case _:
                return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.RowRole: QByteArray(b"row"),
            self.ColRole: QByteArray(b"col"),
            self.TileRole: QByteArray(b"tile"),
            self.StatusRole: QByteArray(b"status"),
        }

    def tiles(self) -> list[TileData]:
        return self._tiles

    def tileMap(self) -> dict[Grid, TileData]:
        return self._tileByGrid

    def tileAt(self, grid: Grid) -> TileData | None:
        return self._tileByGrid.get(grid)

    def boundingBox(self) -> BoundingBox:
        return self._boundingBox

    def setTiles(self, tiles: list[TileData]) -> None:
        self.beginResetModel()
        self._tiles = []
        self._tileByGrid = {}
        self._boundingBox.reset()
        for tile in tiles:
            self._appendTile(tile)
        self.endResetModel()

    def upsertTile(self, tile: TileData) -> TileData | None:
        oldTile = self.tileAt(tile.grid)
        if oldTile == tile:
            return oldTile

        currentTile = self._tileByGrid.get(tile.grid)
        if currentTile is not None:
            tile.index = currentTile.index
            self._tiles[tile.index] = tile
            self._tileByGrid[tile.grid] = tile
            modelIndex = self.index(tile.index, 0)
            self.dataChanged.emit(
                modelIndex,
                modelIndex,
                [self.RowRole, self.ColRole, self.TileRole, self.StatusRole],
            )
            return oldTile

        insertIndex = len(self._tiles)
        self.beginInsertRows(QModelIndex(), insertIndex, insertIndex)
        self._appendTile(tile)
        self.endInsertRows()
        return None

    def removeTile(self, grid: Grid) -> TileData | None:
        tile = self._tileByGrid.get(grid)
        if tile is None:
            return None

        removeIndex = tile.index
        lastIndex = len(self._tiles) - 1
        oldTile = tile
        del self._tileByGrid[grid]
        self._boundingBox.remove(tile.row, tile.col)

        if removeIndex == lastIndex:
            self.beginRemoveRows(QModelIndex(), removeIndex, removeIndex)
            self._tiles.pop()
            self.endRemoveRows()
            return oldTile

        movedTile = self._tiles[lastIndex]
        movedTile.index = removeIndex
        self._tiles[removeIndex] = movedTile
        changedIndex = self.index(removeIndex, 0)
        self.dataChanged.emit(
            changedIndex,
            changedIndex,
            [self.RowRole, self.ColRole, self.TileRole, self.StatusRole],
        )

        self.beginRemoveRows(QModelIndex(), lastIndex, lastIndex)
        self._tiles.pop()
        self.endRemoveRows()
        return oldTile

    def clear(self) -> None:
        if not self._tiles:
            return

        self.beginResetModel()
        self._tiles = []
        self._tileByGrid = {}
        self._boundingBox.reset()
        self.endResetModel()

    def toJson(self) -> list[dict[str, Any]]:
        return [
            tile.toJson()
            for tile in sorted(self._tiles, key=lambda item: (item.row, item.col))
        ]

    def _appendTile(self, tile: TileData) -> None:
        tile.index = len(self._tiles)
        self._tiles.append(tile)
        self._tileByGrid[tile.grid] = tile
        self._boundingBox.add(tile.row, tile.col)
