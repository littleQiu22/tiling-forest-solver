from __future__ import annotations

import itertools as it
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from PySide6.QtCore import (
    QCoreApplication,
    QByteArray,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    Slot,
)
from PySide6.QtQml import QmlNamedElement, QmlUncreatable

from models.geometry import DIRECTION, BoundingBox, Grid
from models.tile import TILE, TILE_SIZE, TileData, tileStatusFromJson, tileTypeFromJson
from solver.option import MODELING
from solver.status import SOLVER_STATUS


QML_IMPORT_NAME = "app.models"
QML_IMPORT_MAJOR_VERSION = 1
PUZZLE_SVG_PADDING = 16


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
            status=tileStatusFromJson(data["status"]),
        )


@dataclass
class Puzzle:
    emptyGrids: set[Grid] = field(default_factory=set)
    placedGrids: dict[Grid, GridData] = field(default_factory=dict)
    tilePool: list[TILE.TYPE] = field(default_factory=list)
    name: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)
    svgPaths: list[str] = field(default_factory=list)
    svgX: int = 0
    svgY: int = 0
    svgWidth: int = 0
    svgHeight: int = 0

    def __post_init__(self) -> None:
        self.rebuildSvgPaths()

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

    def rebuildSvgPaths(self) -> None:
        svgGeometry = buildPuzzleSvgGeometry(self.emptyGrids, self.placedGrids)
        self.svgPaths = svgGeometry.paths
        self.svgX = svgGeometry.x
        self.svgY = svgGeometry.y
        self.svgWidth = svgGeometry.width
        self.svgHeight = svgGeometry.height

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
            for grid in data["emptyGrids"]
        }
        placedGrids = {
            Grid(int(grid["row"]), int(grid["col"])): GridData.fromJson(grid)
            for grid in data["placedGrids"]
        }
        tilePool = [tileTypeFromJson(tile) for tile in data["tilePool"]]
        return cls(
            emptyGrids=emptyGrids,
            placedGrids=placedGrids,
            tilePool=tilePool,
            name=str(data["name"]),
            id=str(data["id"]),
        )


Point = tuple[int, int]
Segment = tuple[Point, Point]


@dataclass(slots=True)
class PuzzleSvgGeometry:
    paths: list[str] = field(default_factory=list)
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


def buildPuzzleSvgGeometry(
    emptyGrids: set[Grid],
    placedGrids: dict[Grid, GridData],
) -> PuzzleSvgGeometry:
    segments: list[Segment] = []

    for emptyGrid in emptyGrids:
        row = emptyGrid.row
        col = emptyGrid.col
        left = col * TILE_SIZE
        right = (col + 1) * TILE_SIZE
        top = row * TILE_SIZE
        bottom = (row + 1) * TILE_SIZE

        if Grid(row - 1, col) in placedGrids:
            segments.append(((left, top), (right, top)))
        if Grid(row, col + 1) in placedGrids:
            segments.append(((right, top), (right, bottom)))
        if Grid(row + 1, col) in placedGrids:
            segments.append(((right, bottom), (left, bottom)))
        if Grid(row, col - 1) in placedGrids:
            segments.append(((left, bottom), (left, top)))

    if not segments:
        return PuzzleSvgGeometry()

    points = [point for segment in segments for point in segment]
    minX = min(point[0] for point in points) - PUZZLE_SVG_PADDING
    maxX = max(point[0] for point in points) + PUZZLE_SVG_PADDING
    minY = min(point[1] for point in points) - PUZZLE_SVG_PADDING
    maxY = max(point[1] for point in points) + PUZZLE_SVG_PADDING

    shiftedPaths = []
    for loopPoints in _buildSegmentLoops(segments):
        shiftedPoints = [(x - minX, y - minY)
                         for x, y in _compactPoints(loopPoints)]
        if shiftedPoints:
            shiftedPaths.append(_pointsToSvgPath(shiftedPoints))

    return PuzzleSvgGeometry(
        paths=shiftedPaths,
        x=minX,
        y=minY,
        width=maxX - minX,
        height=maxY - minY,
    )


def _buildSegmentLoops(segments: list[Segment]) -> list[list[Point]]:
    segmentsByStart: dict[Point, list[Point]] = {}
    for start, end in segments:
        segmentsByStart.setdefault(start, []).append(end)

    loops: list[list[Point]] = []
    while segmentsByStart:
        start = next(iter(segmentsByStart))
        points = [start]

        while start in segmentsByStart:
            end = segmentsByStart[start].pop()
            if not segmentsByStart[start]:
                del segmentsByStart[start]

            points.append(end)
            start = end

        loops.append(points)

    return loops


def _compactPoints(points: list[Point]) -> list[Point]:
    if len(points) <= 2:
        return points

    compactPoints: list[Point] = []
    pointCount = len(points)
    isClosed = points[0] == points[-1]
    actualLength = pointCount - 1 if isClosed else pointCount

    for index in range(actualLength):
        previousPoint = points[index - 1 if index > 0 else actualLength - 1]
        currentPoint = points[index]
        nextPoint = points[(index + 1) % actualLength]

        isHorizontal = previousPoint[1] == currentPoint[1] == nextPoint[1]
        isVertical = previousPoint[0] == currentPoint[0] == nextPoint[0]
        if not (isHorizontal or isVertical):
            compactPoints.append(currentPoint)

    return compactPoints


def _pointsToSvgPath(points: list[Point]) -> str:
    if not points:
        return ""

    commands = [f"M {points[0][0]} {points[0][1]}"]
    commands.extend(f"L {point[0]} {point[1]}" for point in points[1:])
    commands.append("Z")
    return " ".join(commands)


@dataclass(slots=True)
class PuzzleExtraction:
    puzzle: Puzzle | None = None
    message: str = ""


def extractPuzzle(
    tileMap: dict[Grid, TileData],
    boundingBox: BoundingBox,
    seed: Grid,
    tilePool: list[TILE.TYPE] | None = None
) -> PuzzleExtraction:
    if seed in tileMap:
        return PuzzleExtraction()

    if boundingBox.isOutRange(seed.row, seed.col):
        return PuzzleExtraction(
            message=QCoreApplication.translate(
                "PuzzleExtraction", "Puzzle creation failed: The selected empty area is not enclosed by tiles."),
        )

    def isEmpty(grid: Grid) -> bool:
        return grid not in tileMap

    def addPlacedGrid(grid: Grid) -> None:
        tile = tileMap.get(grid)
        if tile is not None:
            placedGrids[grid] = GridData(tile=tile.tile, status=tile.status)

    def unbounded() -> PuzzleExtraction:
        return PuzzleExtraction(
            message=QCoreApplication.translate(
                "PuzzleExtraction", "The selected empty area is not enclosed."),
        )

    def addPairedStumps() -> None:
        stumpByDirection = {
            DIRECTION.NORTH: TILE.TYPE.STUMP_S,
            DIRECTION.EAST: TILE.TYPE.STUMP_W,
            DIRECTION.SOUTH: TILE.TYPE.STUMP_N,
            DIRECTION.WEST: TILE.TYPE.STUMP_E,
        }

        for placedGrid, placedData in list(placedGrids.items()):
            if placedData.tile not in TILE.ROADS:
                continue

            for direction, stumpType in stumpByDirection.items():
                stumpGrid = placedGrid.neighbor(direction)
                if stumpGrid in emptyGrids or stumpGrid in placedGrids:
                    continue

                stumpTile = tileMap.get(stumpGrid)
                if stumpTile is not None and stumpTile.tile == stumpType:
                    placedGrids[stumpGrid] = GridData(
                        tile=stumpTile.tile,
                        status=stumpTile.status,
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

    addPairedStumps()

    return PuzzleExtraction(
        puzzle=Puzzle(
            emptyGrids=emptyGrids,
            placedGrids=placedGrids,
            tilePool=tilePool if tilePool is not None else [],
        ),
    )


PuzzleSolveStatus = SOLVER_STATUS


TILE_POOL_CANDIDATES = [
    TILE.TYPE.ROAD_WE,
    TILE.TYPE.ROAD_NS,
    TILE.TYPE.ROAD_ES,
    TILE.TYPE.ROAD_WS,
    TILE.TYPE.ROAD_WN,
    TILE.TYPE.ROAD_EN,
    TILE.TYPE.CLEARING_ES,
    TILE.TYPE.CLEARING_WS,
    TILE.TYPE.CLEARING_WN,
    TILE.TYPE.CLEARING_EN,
    TILE.TYPE.CLEARING_E,
    TILE.TYPE.CLEARING_S,
    TILE.TYPE.CLEARING_W,
    TILE.TYPE.CLEARING_N,
    TILE.TYPE.CLEARING_W_ROAD_E,
    TILE.TYPE.CLEARING_N_ROAD_S,
    TILE.TYPE.CLEARING_E_ROAD_W,
    TILE.TYPE.CLEARING_S_ROAD_N,
    TILE.TYPE.STUMP_E,
    TILE.TYPE.STUMP_S,
    TILE.TYPE.STUMP_W,
    TILE.TYPE.STUMP_N,
]


Solution = dict[Grid, TILE.TYPE]
DEFAULT_TIME_LIMIT = 30
DEFAULT_SOLUTION_LIMIT = 20


@dataclass(slots=True)
class PuzzleState:
    isSelected: bool = False
    isGeometryStaled: bool = False
    solveStatus: PuzzleSolveStatus = PuzzleSolveStatus.UNSOLVED
    objectiveOrder: list[MODELING.GOAL] = field(
        default_factory=lambda: list(MODELING.GOAL))
    enabledObjectives: set[MODELING.GOAL] = field(default_factory=lambda: {
        MODELING.GOAL.MIN_UNEXPLORED,
        MODELING.GOAL.MAX_CONNECTIVITY,
        MODELING.GOAL.MAX_DENSITY
    })
    enabledConstraints: set[MODELING.CONSTRAINT] = field(
        default_factory=lambda: {
            MODELING.CONSTRAINT.FIGURE_ALIGNED,
            MODELING.CONSTRAINT.ROAD_MUST_EXIT,
        })
    isTimeLimitEnabled: bool = False
    timeLimit: int = DEFAULT_TIME_LIMIT
    isSolutionLimitEnabled: bool = False
    solutionLimit: int = DEFAULT_SOLUTION_LIMIT
    solutions: list[Solution] = field(default_factory=list)
    currentSolutionIndex: int = -1
    solvingLog: str = ""

    def toJson(self) -> dict[str, Any]:
        return {
            "isGeometryStaled": self.isGeometryStaled,
            "solveStatus": PuzzleSolveStatus.UNSOLVED.value
            if self.solveStatus == PuzzleSolveStatus.SOLVING
            else self.solveStatus.value,
            "objectiveOrder": [objective.name for objective in self.objectiveOrder],
            "enabledObjectives": sorted(objective.name for objective in self.enabledObjectives),
            "enabledConstraints": sorted(constraint.name for constraint in self.enabledConstraints),
            "isTimeLimitEnabled": self.isTimeLimitEnabled,
            "timeLimit": self.timeLimit,
            "isSolutionLimitEnabled": self.isSolutionLimitEnabled,
            "solutionLimit": self.solutionLimit,
            "solutions": [
                [
                    {
                        "row": grid.row,
                        "col": grid.col,
                        "tile": tile.name,
                    }
                    for grid, tile in sorted(solution.items(), key=lambda item: (item[0].row, item[0].col))
                ]
                for solution in self.solutions
            ],
            "currentSolutionIndex": self.currentSolutionIndex,
            "solvingLog": self.solvingLog,
        }

    @classmethod
    def fromJson(cls, data: dict[str, Any]) -> "PuzzleState":
        solveStatus = PuzzleSolveStatus(data["solveStatus"])
        if solveStatus == PuzzleSolveStatus.SOLVING:
            solveStatus = PuzzleSolveStatus.UNSOLVED
        return cls(
            isGeometryStaled=bool(data["isGeometryStaled"]),
            solveStatus=solveStatus,
            objectiveOrder=[
                MODELING.GOAL[str(item)]
                for item in data["objectiveOrder"]
            ],
            enabledObjectives={
                MODELING.GOAL[str(item)]
                for item in data["enabledObjectives"]
            },
            enabledConstraints={
                MODELING.CONSTRAINT[str(item)]
                for item in data["enabledConstraints"]
            },
            isTimeLimitEnabled=bool(data["isTimeLimitEnabled"]),
            timeLimit=int(data["timeLimit"]),
            isSolutionLimitEnabled=bool(data["isSolutionLimitEnabled"]),
            solutionLimit=int(data["solutionLimit"]),
            solutions=[
                {
                    Grid(int(item["row"]), int(item["col"])): tileTypeFromJson(item["tile"])
                    for item in solution
                }
                for solution in data["solutions"]
            ],
            currentSolutionIndex=int(data["currentSolutionIndex"]),
            solvingLog=str(data["solvingLog"]),
        )


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
    IsSelectedRole = IndexRole + 10
    SolveStatusRole = IndexRole + 11
    SvgPathsRole = IndexRole + 12
    SvgXRole = IndexRole + 13
    SvgYRole = IndexRole + 14
    SvgWidthRole = IndexRole + 15
    SvgHeightRole = IndexRole + 16
    CurrentSolutionRole = IndexRole + 17
    ObjectiveItemsRole = IndexRole + 18
    ConstraintItemsRole = IndexRole + 19
    TimeLimitRole = IndexRole + 20
    SolutionLimitRole = IndexRole + 21
    SolutionCountRole = IndexRole + 22
    CurrentSolutionIndexRole = IndexRole + 23
    SolvingLogRole = IndexRole + 24

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._puzzles: list[Puzzle] = []
        self._stateByPuzzleId: dict[str, PuzzleState] = {}
        self._puzzlesByGrid: dict[Grid, list[Puzzle]] = {}

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
            case self.IsSelectedRole:
                return puzzleState.isSelected
            case self.SolveStatusRole:
                return puzzleState.solveStatus.value
            case self.SvgPathsRole:
                return puzzle.svgPaths
            case self.SvgXRole:
                return puzzle.svgX
            case self.SvgYRole:
                return puzzle.svgY
            case self.SvgWidthRole:
                return puzzle.svgWidth
            case self.SvgHeightRole:
                return puzzle.svgHeight
            case self.CurrentSolutionRole:
                return self._currentSolutionForQml(puzzleState)
            case self.ObjectiveItemsRole:
                return [objective.name for objective in puzzleState.objectiveOrder]
            case self.ConstraintItemsRole:
                return sorted(constraint.name for constraint in puzzleState.enabledConstraints)
            case self.TimeLimitRole:
                return puzzleState.timeLimit
            case self.SolutionLimitRole:
                return puzzleState.solutionLimit
            case self.SolutionCountRole:
                return len(puzzleState.solutions)
            case self.CurrentSolutionIndexRole:
                return puzzleState.currentSolutionIndex
            case self.SolvingLogRole:
                return puzzleState.solvingLog
            case _:
                return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.IndexRole: QByteArray(b"index"),
            self.IdRole: QByteArray(b"puzzleId"),
            self.NameRole: QByteArray(b"name"),
            self.GridCountRole: QByteArray(b"gridCount"),
            self.EmptyGridCountRole: QByteArray(b"emptyGridCount"),
            self.PlacedGridCountRole: QByteArray(b"placedGridCount"),
            self.EmptyGridsRole: QByteArray(b"emptyGrids"),
            self.PlacedGridsRole: QByteArray(b"placedGrids"),
            self.TilePoolRole: QByteArray(b"tilePool"),
            self.IsGeometryStaledRole: QByteArray(b"isGeometryStaled"),
            self.IsSelectedRole: QByteArray(b"isSelected"),
            self.SolveStatusRole: QByteArray(b"solveStatus"),
            self.SvgPathsRole: QByteArray(b"svgPaths"),
            self.SvgXRole: QByteArray(b"svgX"),
            self.SvgYRole: QByteArray(b"svgY"),
            self.SvgWidthRole: QByteArray(b"svgWidth"),
            self.SvgHeightRole: QByteArray(b"svgHeight"),
            self.CurrentSolutionRole: QByteArray(b"currentSolution"),
            self.ObjectiveItemsRole: QByteArray(b"objectiveItems"),
            self.ConstraintItemsRole: QByteArray(b"constraintItems"),
            self.TimeLimitRole: QByteArray(b"timeLimit"),
            self.SolutionLimitRole: QByteArray(b"solutionLimit"),
            self.SolutionCountRole: QByteArray(b"solutionCount"),
            self.CurrentSolutionIndexRole: QByteArray(b"currentSolutionIndex"),
            self.SolvingLogRole: QByteArray(b"solvingLog"),
        }

    def puzzles(self) -> list[Puzzle]:
        return self._puzzles

    def setPuzzles(self, puzzles: list[Puzzle]) -> None:
        self.beginResetModel()
        self._puzzles = puzzles
        self._stateByPuzzleId = {}
        self._puzzlesByGrid = {}
        self._ensurePuzzleNames()
        self._rebuildIndexes()
        self.endResetModel()

    def insertPuzzle(self, index: int, puzzle: Puzzle, state: PuzzleState | None = None) -> int:
        insertIndex = max(0, min(index, len(self._puzzles)))
        if not puzzle.name:
            puzzle.name = self._defaultPuzzleName(insertIndex)

        self.beginInsertRows(QModelIndex(), insertIndex, insertIndex)
        self._puzzles.insert(insertIndex, puzzle)
        self._registerPuzzle(puzzle, state)
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

    def movePuzzleToIndex(self, puzzleId: str, targetIndex: int) -> bool:
        sourceIndex = self.indexById(puzzleId)
        if sourceIndex == -1:
            return False

        targetIndex = max(0, min(targetIndex, len(self._puzzles) - 1))
        if sourceIndex == targetIndex:
            return False

        destinationChild = targetIndex + 1 if sourceIndex < targetIndex else targetIndex
        if not self.beginMoveRows(
            QModelIndex(),
            sourceIndex,
            sourceIndex,
            QModelIndex(),
            destinationChild,
        ):
            return False

        puzzle = self._puzzles.pop(sourceIndex)
        self._puzzles.insert(targetIndex, puzzle)
        self.endMoveRows()
        return True

    def puzzleAt(self, index: int) -> Puzzle | None:
        if not 0 <= index < len(self._puzzles):
            return None
        return self._puzzles[index]

    def puzzleById(self, puzzleId: str) -> Puzzle | None:
        index = self.indexById(puzzleId)
        if index == -1:
            return None
        return self.puzzleAt(index)

    @Slot(str, result=int)
    def indexById(self, puzzleId: str) -> int:
        for index, puzzle in enumerate(self._puzzles):
            if puzzle.id == puzzleId:
                return index
        return -1

    def puzzleContaining(self, grid: Grid) -> Puzzle | None:
        puzzles = self._puzzlesByGrid.get(grid)
        if not puzzles:
            return None
        return puzzles[-1]

    def puzzleStateById(self, puzzleId: str) -> PuzzleState | None:
        return self._stateByPuzzleId.get(puzzleId)

    @Slot(str, result="QVariantMap")
    def geometryById(self, puzzleId: str) -> dict[str, Any]:
        puzzle = self.puzzleById(puzzleId)
        if puzzle is None:
            return {
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 0,
            }

        return {
            "x": puzzle.svgX,
            "y": puzzle.svgY,
            "width": puzzle.svgWidth,
            "height": puzzle.svgHeight,
        }

    def setPuzzleName(self, puzzleId: str, name: str) -> bool:
        index = self.indexById(puzzleId)
        puzzle = self.puzzleAt(index)
        if puzzle is None:
            return False

        nextName = name.strip() or self._defaultPuzzleName(index)
        if puzzle.name == nextName:
            return False

        puzzle.name = nextName
        self._emitRoles(index, [self.NameRole])
        return True

    def setPuzzleTilePool(self, puzzleId: str, tilePool: list[TILE.TYPE]) -> bool:
        index = self.indexById(puzzleId)
        puzzle = self.puzzleAt(index)
        if puzzle is None or puzzle.tilePool == tilePool:
            return False

        puzzle.tilePool = tilePool
        self._emitRoles(index, [self.TilePoolRole])
        return True

    def setPuzzleSelected(self, puzzleId: str, isSelected: bool) -> None:
        index = self.indexById(puzzleId)
        puzzleState = self._stateByPuzzleId.get(puzzleId)
        if index == -1 or puzzleState is None or puzzleState.isSelected == isSelected:
            return

        puzzleState.isSelected = isSelected
        self._emitRoles(index, [self.IsSelectedRole])

    def replacePuzzleGeometry(self, puzzleId: str, puzzle: Puzzle) -> bool:
        index = self.indexById(puzzleId)
        oldPuzzle = self.puzzleAt(index)
        if oldPuzzle is None:
            return False

        puzzle.id = oldPuzzle.id
        puzzle.name = oldPuzzle.name
        puzzle.tilePool = oldPuzzle.tilePool

        self._unregisterPuzzleGrids(oldPuzzle)

        self._puzzles[index] = puzzle
        self._registerPuzzleGrids(puzzle)

        self._emitRoles(
            index,
            [
                self.GridCountRole,
                self.EmptyGridCountRole,
                self.PlacedGridCountRole,
                self.EmptyGridsRole,
                self.PlacedGridsRole,
                self.SvgPathsRole,
                self.SvgXRole,
                self.SvgYRole,
                self.SvgWidthRole,
                self.SvgHeightRole,
            ],
        )
        return True

    def emitPuzzleChanged(self, puzzleId: str, roles: list[int]) -> None:
        index = self.indexById(puzzleId)
        if index != -1:
            self._emitRoles(index, roles)

    def emitAllChanged(self, roles: list[int]) -> None:
        if not self._puzzles:
            return

        topLeft = self.index(0, 0)
        bottomRight = self.index(len(self._puzzles) - 1, 0)
        self.dataChanged.emit(topLeft, bottomRight, roles)

    def markGeometryStaledByGrid(self, grid: Grid) -> str:
        puzzles = self._puzzlesByGrid.get(grid)
        if not puzzles:
            return ""

        markedPuzzleId = ""
        for puzzle in puzzles:
            puzzleState = self._stateByPuzzleId[puzzle.id]
            markedPuzzleId = markedPuzzleId or puzzle.id
            if puzzleState.isGeometryStaled:
                continue

            puzzleState.isGeometryStaled = True
            index = self.indexById(puzzle.id)
            if index != -1:
                modelIndex = self.index(index, 0)
                self.dataChanged.emit(
                    modelIndex,
                    modelIndex,
                    [self.IsGeometryStaledRole],
                )
        return markedPuzzleId

    def clear(self) -> None:
        if not self._puzzles:
            return

        self.beginResetModel()
        self._puzzles = []
        self._stateByPuzzleId = {}
        self._puzzlesByGrid = {}
        self.endResetModel()

    def toJson(self) -> list[dict[str, Any]]:
        return [puzzle.toJson() for puzzle in self._puzzles]

    def statesToJson(self) -> dict[str, dict[str, Any]]:
        return {
            puzzleId: state.toJson()
            for puzzleId, state in self._stateByPuzzleId.items()
        }

    def states(self) -> dict[str, PuzzleState]:
        return self._stateByPuzzleId

    def setStates(self, states: dict[str, PuzzleState]) -> None:
        self._stateByPuzzleId = states
        if self._puzzles:
            topLeft = self.index(0, 0)
            bottomRight = self.index(len(self._puzzles) - 1, 0)
            self.dataChanged.emit(topLeft, bottomRight, [])

    def loadStatesJson(self, data: dict[str, Any]) -> None:
        for puzzleId, stateData in data.items():
            if puzzleId in self._stateByPuzzleId:
                self._stateByPuzzleId[puzzleId] = PuzzleState.fromJson(
                    stateData)
        if self._puzzles:
            topLeft = self.index(0, 0)
            bottomRight = self.index(len(self._puzzles) - 1, 0)
            self.dataChanged.emit(
                topLeft,
                bottomRight,
                [
                    self.IsGeometryStaledRole,
                    self.SolveStatusRole,
                    self.CurrentSolutionRole,
                ],
            )

    def _ensurePuzzleNames(self) -> None:
        for index, puzzle in enumerate(self._puzzles):
            if not puzzle.name:
                puzzle.name = self._defaultPuzzleName(index)

    def _rebuildIndexes(self) -> None:
        for puzzle in self._puzzles:
            self._registerPuzzle(puzzle)

    def _registerPuzzle(self, puzzle: Puzzle, state: PuzzleState | None = None) -> None:
        self._stateByPuzzleId.setdefault(puzzle.id, state or PuzzleState())
        self._registerPuzzleGrids(puzzle)

    def _registerPuzzleGrids(self, puzzle: Puzzle) -> None:
        for grid in puzzle.grids:
            puzzles = self._puzzlesByGrid.setdefault(grid, [])
            if puzzle not in puzzles:
                puzzles.append(puzzle)

    def _unregisterPuzzle(self, puzzle: Puzzle) -> None:
        self._stateByPuzzleId.pop(puzzle.id, None)
        self._unregisterPuzzleGrids(puzzle)

    def _unregisterPuzzleGrids(self, puzzle: Puzzle) -> None:
        for grid in puzzle.grids:
            puzzles = self._puzzlesByGrid.get(grid)
            if not puzzles:
                continue
            if puzzle in puzzles:
                puzzles.remove(puzzle)
            if not puzzles:
                del self._puzzlesByGrid[grid]

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

    def _currentSolutionForQml(self, puzzleState: PuzzleState) -> list[dict[str, int]]:
        if not 0 <= puzzleState.currentSolutionIndex < len(puzzleState.solutions):
            return []

        solution = puzzleState.solutions[puzzleState.currentSolutionIndex]
        return [
            {
                "row": grid.row,
                "col": grid.col,
                "tile": tile.value,
            }
            for grid, tile in sorted(solution.items(), key=lambda item: (item[0].row, item[0].col))
        ]

    def _emitRoles(self, index: int, roles: list[int]) -> None:
        modelIndex = self.index(index, 0)
        self.dataChanged.emit(modelIndex, modelIndex, roles)
