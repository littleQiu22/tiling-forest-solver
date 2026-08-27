from __future__ import annotations

import itertools as it
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from PySide6.QtCore import (
    QByteArray,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
)
from PySide6.QtQml import QmlNamedElement, QmlUncreatable

from models.geometry import BoundingBox, Grid
from models.tile import TILE, TileData, tileStatusFromJson, tileTypeFromJson


QML_IMPORT_NAME = "app.models"
QML_IMPORT_MAJOR_VERSION = 1


@dataclass(frozen=True)
class GridData:
    tile: TILE.TYPE
    status: TILE.STATUS = TILE.STATUS.NORMAL

    def toJson(self, grid: Grid) -> dict[str, Any]:
        return {
            "row": grid.row,
            "col": grid.col,
            "tile": self.tile.name,
            "status": self.status.name,
        }

    @classmethod
    def fromJson(cls, data: dict[str, Any]) -> "GridData":
        return cls(
            tile=tileTypeFromJson(data["tile"]),
            status=tileStatusFromJson(
                data.get("status", TILE.STATUS.NORMAL.name)),
        )


@dataclass
class Puzzle:
    emptyGrids: set[Grid] = field(default_factory=set)
    placedGrids: dict[Grid, GridData] = field(default_factory=dict)
    tilePool: list[TILE.TYPE] = field(default_factory=list)
    name: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)

    @property
    def grids(self):
        return it.chain(self.emptyGrids, self.placedGrids)

    @property
    def gridCount(self) -> int:
        return len(self.emptyGrids) + len(self.placedGrids)

    def contains(self, grid: Grid) -> bool:
        return grid in self.emptyGrids or grid in self.placedGrids

    def getGridData(self, grid: Grid) -> GridData | None:
        return self.placedGrids.get(grid, None)

    def toJson(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "emptyGrids": [
                {"row": grid.row, "col": grid.col}
                for grid in sorted(self.emptyGrids, key=lambda item: (item.row, item.col))
            ],
            "placedGrids": [
                gridData.toJson(grid)
                for grid, gridData in sorted(
                    self.placedGrids.items(),
                    key=lambda item: (item[0].row, item[0].col),
                )
            ],
            "tilePool": [tile.name for tile in self.tilePool],
        }

    @classmethod
    def fromJson(cls, data: dict[str, Any]) -> "Puzzle":
        emptyGrids = {
            Grid(int(grid["row"]), int(grid["col"]))
            for grid in data.get("emptyGrids", [])
        }
        placedGrids = {
            Grid(int(grid["row"]), int(grid["col"])): GridData.fromJson(grid)
            for grid in data.get("placedGrids", [])
        }
        tilePool = [tileTypeFromJson(tile)
                    for tile in data.get("tilePool", [])]
        return cls(
            emptyGrids=emptyGrids,
            placedGrids=placedGrids,
            tilePool=tilePool,
            name=str(data.get("name", "")),
            id=str(data.get("id", uuid4().hex)),
        )


@dataclass(slots=True)
class PuzzleExtraction:
    puzzle: Puzzle | None = None
    message: str = ""


def extractPuzzle(
    tileMap: dict[Grid, TileData],
    boundingBox: BoundingBox,
    seed: Grid,
) -> PuzzleExtraction:
    if seed in tileMap:
        return PuzzleExtraction()

    if boundingBox.isOutRange(seed.row, seed.col):
        return PuzzleExtraction(
            message="The selected empty area is not enclosed by placed tiles.",
        )

    def isEmpty(grid: Grid) -> bool:
        return grid not in tileMap

    def addPlacedGrid(grid: Grid) -> None:
        tile = tileMap.get(grid)
        if tile is not None:
            placedGrids[grid] = GridData(tile=tile.tile, status=tile.status)

    def unbounded() -> PuzzleExtraction:
        return PuzzleExtraction(
            message="The selected empty area is not enclosed.",
        )

    emptyGrids: set[Grid] = set()
    placedGrids: dict[Grid, GridData] = {}
    pendingSeeds = [seed]

    while pendingSeeds:
        start = pendingSeeds.pop()
        if start in emptyGrids or not isEmpty(start):
            continue

        row = start.row
        leftCol = start.col
        while True:
            nextGrid = Grid(row, leftCol - 1)
            if boundingBox.isOutRange(nextGrid.row, nextGrid.col):
                return unbounded()
            if nextGrid in emptyGrids or not isEmpty(nextGrid):
                break
            leftCol -= 1

        rightCol = start.col
        while True:
            nextGrid = Grid(row, rightCol + 1)
            if boundingBox.isOutRange(nextGrid.row, nextGrid.col):
                return unbounded()
            if nextGrid in emptyGrids or not isEmpty(nextGrid):
                break
            rightCol += 1

        addPlacedGrid(Grid(row, leftCol - 1))
        addPlacedGrid(Grid(row, rightCol + 1))

        for col in range(leftCol, rightCol + 1):
            emptyGrids.add(Grid(row, col))

        for adjacentRow in (row - 1, row + 1):
            seedAdded = False
            for col in range(leftCol, rightCol + 1):
                grid = Grid(adjacentRow, col)
                if boundingBox.isOutRange(grid.row, grid.col):
                    return unbounded()
                if grid in emptyGrids:
                    continue

                tile = tileMap.get(grid)
                if tile is not None:
                    placedGrids[grid] = GridData(
                        tile=tile.tile, status=tile.status)
                    seedAdded = False
                    continue

                if isEmpty(grid):
                    if not seedAdded:
                        pendingSeeds.append(grid)
                        seedAdded = True
                else:
                    seedAdded = False

    tilePool = [
        gridData.tile
        for _, gridData in sorted(
            placedGrids.items(),
            key=lambda item: (item[0].row, item[0].col),
        )
    ]
    return PuzzleExtraction(
        puzzle=Puzzle(
            emptyGrids=emptyGrids,
            placedGrids=placedGrids,
            tilePool=tilePool,
        ),
    )


class PuzzleSolveStatus(Enum):
    UNSOLVED = "Unsolved"
    SOLVING = "Solving"
    TIME_LIMIT = "TimeLimit"
    SOLUTION_LIMIT = "SolutionLimit"
    INFEASIBLE = "Infeasible"
    SOLVED = "Solved"


@dataclass(slots=True)
class PuzzleState:
    isGeometryStaled: bool = False
    solveStatus: PuzzleSolveStatus = PuzzleSolveStatus.UNSOLVED


@QmlNamedElement("PuzzleListModel")
@QmlUncreatable("Use Workspace.puzzles")
class PuzzleListModel(QAbstractListModel):
    IndexRole = Qt.ItemDataRole.UserRole.value + 1
    IdRole = IndexRole + 1
    NameRole = IndexRole + 2
    GridCountRole = IndexRole + 3
    EmptyGridCountRole = IndexRole + 4
    PlacedGridCountRole = IndexRole + 5
    EmptyGridsRole = IndexRole + 6
    PlacedGridsRole = IndexRole + 7
    TilePoolRole = IndexRole + 8
    IsGeometryStaledRole = IndexRole + 9
    SolveStatusRole = IndexRole + 10

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._puzzles: list[Puzzle] = []
        self._stateByPuzzleId: dict[str, PuzzleState] = {}
        self._puzzleByGrid: dict[Grid, Puzzle] = {}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._puzzles)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._puzzles):
            return None

        puzzleIndex = index.row()
        puzzle = self._puzzles[puzzleIndex]
        puzzleState = self._stateByPuzzleId[puzzle.id]
        match role:
            case self.IndexRole:
                return puzzleIndex
            case self.IdRole:
                return puzzle.id
            case self.NameRole:
                return puzzle.name
            case self.GridCountRole:
                return puzzle.gridCount
            case self.EmptyGridCountRole:
                return len(puzzle.emptyGrids)
            case self.PlacedGridCountRole:
                return len(puzzle.placedGrids)
            case self.EmptyGridsRole:
                return self._emptyGridsForQml(puzzle)
            case self.PlacedGridsRole:
                return self._placedGridsForQml(puzzle)
            case self.TilePoolRole:
                return [tile.value for tile in puzzle.tilePool]
            case self.IsGeometryStaledRole:
                return puzzleState.isGeometryStaled
            case self.SolveStatusRole:
                return puzzleState.solveStatus.value
            case _:
                return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.IndexRole: QByteArray(b"index"),
            self.IdRole: QByteArray(b"id"),
            self.NameRole: QByteArray(b"name"),
            self.GridCountRole: QByteArray(b"gridCount"),
            self.EmptyGridCountRole: QByteArray(b"emptyGridCount"),
            self.PlacedGridCountRole: QByteArray(b"placedGridCount"),
            self.EmptyGridsRole: QByteArray(b"emptyGrids"),
            self.PlacedGridsRole: QByteArray(b"placedGrids"),
            self.TilePoolRole: QByteArray(b"tilePool"),
            self.IsGeometryStaledRole: QByteArray(b"isGeometryStaled"),
            self.SolveStatusRole: QByteArray(b"solveStatus"),
        }

    def puzzles(self) -> list[Puzzle]:
        return self._puzzles

    def setPuzzles(self, puzzles: list[Puzzle]) -> None:
        self.beginResetModel()
        self._puzzles = puzzles
        self._stateByPuzzleId = {}
        self._puzzleByGrid = {}
        self._ensurePuzzleNames()
        self._rebuildIndexes()
        self.endResetModel()

    def addPuzzle(self, puzzle: Puzzle) -> int:
        insertIndex = len(self._puzzles)
        if not puzzle.name:
            puzzle.name = self._defaultPuzzleName(insertIndex)

        self.beginInsertRows(QModelIndex(), insertIndex, insertIndex)
        self._puzzles.append(puzzle)
        self._registerPuzzle(puzzle)
        self.endInsertRows()
        return insertIndex

    def insertPuzzle(self, index: int, puzzle: Puzzle) -> int:
        insertIndex = max(0, min(index, len(self._puzzles)))
        if not puzzle.name:
            puzzle.name = self._defaultPuzzleName(insertIndex)

        self.beginInsertRows(QModelIndex(), insertIndex, insertIndex)
        self._puzzles.insert(insertIndex, puzzle)
        self._registerPuzzle(puzzle)
        self.endInsertRows()
        return insertIndex

    def removePuzzleAt(self, index: int) -> Puzzle | None:
        if not 0 <= index < len(self._puzzles):
            return None

        puzzle = self._puzzles[index]
        self.beginRemoveRows(QModelIndex(), index, index)
        self._unregisterPuzzle(puzzle)
        self._puzzles.pop(index)
        self.endRemoveRows()
        return puzzle

    def removePuzzleById(self, puzzleId: str) -> Puzzle | None:
        index = self.indexById(puzzleId)
        if index == -1:
            return None
        return self.removePuzzleAt(index)

    def puzzleAt(self, index: int) -> Puzzle | None:
        if not 0 <= index < len(self._puzzles):
            return None
        return self._puzzles[index]

    def puzzleById(self, puzzleId: str) -> Puzzle | None:
        index = self.indexById(puzzleId)
        if index == -1:
            return None
        return self.puzzleAt(index)

    def indexById(self, puzzleId: str) -> int:
        for index, puzzle in enumerate(self._puzzles):
            if puzzle.id == puzzleId:
                return index
        return -1

    def indexContaining(self, grid: Grid) -> int:
        puzzle = self._puzzleByGrid.get(grid)
        return -1 if puzzle is None else self.indexById(puzzle.id)

    def puzzleContaining(self, grid: Grid) -> Puzzle | None:
        return self._puzzleByGrid.get(grid)

    def puzzleStateById(self, puzzleId: str) -> PuzzleState | None:
        return self._stateByPuzzleId.get(puzzleId)

    def markGeometryStaledByGrid(self, grid: Grid) -> str:
        puzzle = self._puzzleByGrid.get(grid)
        if puzzle is None:
            return ""

        puzzleState = self._stateByPuzzleId[puzzle.id]
        if puzzleState.isGeometryStaled:
            return puzzle.id

        puzzleState.isGeometryStaled = True
        index = self.indexById(puzzle.id)
        if index != -1:
            modelIndex = self.index(index, 0)
            self.dataChanged.emit(
                modelIndex,
                modelIndex,
                [self.IsGeometryStaledRole],
            )
        return puzzle.id

    def clear(self) -> None:
        if not self._puzzles:
            return

        self.beginResetModel()
        self._puzzles = []
        self._stateByPuzzleId = {}
        self._puzzleByGrid = {}
        self.endResetModel()

    def toJson(self) -> list[dict[str, Any]]:
        return [puzzle.toJson() for puzzle in self._puzzles]

    def _ensurePuzzleNames(self) -> None:
        for index, puzzle in enumerate(self._puzzles):
            if not puzzle.name:
                puzzle.name = self._defaultPuzzleName(index)

    def _rebuildIndexes(self) -> None:
        for puzzle in self._puzzles:
            self._registerPuzzle(puzzle)

    def _registerPuzzle(self, puzzle: Puzzle) -> None:
        self._stateByPuzzleId.setdefault(puzzle.id, PuzzleState())
        for grid in puzzle.grids:
            self._puzzleByGrid[grid] = puzzle

    def _unregisterPuzzle(self, puzzle: Puzzle) -> None:
        self._stateByPuzzleId.pop(puzzle.id, None)
        for grid in puzzle.grids:
            if self._puzzleByGrid.get(grid) is puzzle:
                del self._puzzleByGrid[grid]

    def _defaultPuzzleName(self, index: int) -> str:
        return f"Puzzle {index + 1}"

    def _emptyGridsForQml(self, puzzle: Puzzle) -> list[dict[str, int]]:
        return [
            {"row": grid.row, "col": grid.col}
            for grid in sorted(puzzle.emptyGrids, key=lambda item: (item.row, item.col))
        ]

    def _placedGridsForQml(self, puzzle: Puzzle) -> list[dict[str, Any]]:
        return [
            {
                "row": grid.row,
                "col": grid.col,
                "tile": gridData.tile.value,
                "status": gridData.status.value,
            }
            for grid, gridData in sorted(
                puzzle.placedGrids.items(),
                key=lambda item: (item[0].row, item[0].col),
            )
        ]
