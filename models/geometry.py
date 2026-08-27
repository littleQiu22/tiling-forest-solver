from dataclasses import dataclass
from enum import Enum


class DIRECTION(Enum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

    @property
    def delta(self) -> tuple[int, int]:
        match self:
            case DIRECTION.EAST:
                return (0, 1)
            case DIRECTION.WEST:
                return (0, -1)
            case DIRECTION.NORTH:
                return (-1, 0)
            case DIRECTION.SOUTH:
                return (1, 0)

    def opposite(self) -> "DIRECTION":
        match self:
            case DIRECTION.EAST:
                return DIRECTION.WEST
            case DIRECTION.WEST:
                return DIRECTION.EAST
            case DIRECTION.NORTH:
                return DIRECTION.SOUTH
            case DIRECTION.SOUTH:
                return DIRECTION.NORTH


@dataclass(slots=True, frozen=True)
class Grid:
    row: int
    col: int

    def edge(self, direction: DIRECTION) -> "Edge":
        return Edge.between(self, self.neighbor(direction))

    def neighbor(self, direction: DIRECTION) -> "Grid":
        dr, dc = direction.delta
        return Grid(self.row + dr, self.col + dc)

    def neighbors(self) -> list["Grid"]:
        return [self.neighbor(d) for d in DIRECTION]


class BoundingBox:
    def __init__(self) -> None:
        self.minRow = 0
        self.maxRow = 0
        self.minCol = 0
        self.maxCol = 0
        self.rowCount: dict[int, int] = {}
        self.colCount: dict[int, int] = {}
        self.isValid = False

    def add(self, row: int, col: int) -> None:
        if not self.isValid:
            self.minRow = self.maxRow = row
            self.minCol = self.maxCol = col
            self.isValid = True
        else:
            self.minRow = min(self.minRow, row)
            self.maxRow = max(self.maxRow, row)
            self.minCol = min(self.minCol, col)
            self.maxCol = max(self.maxCol, col)

        self.rowCount[row] = self.rowCount.get(row, 0) + 1
        self.colCount[col] = self.colCount.get(col, 0) + 1

    def remove(self, row: int, col: int) -> None:
        if not self.isValid:
            return

        self._decrementCount(self.rowCount, row)
        self._decrementCount(self.colCount, col)

        while self.minRow <= self.maxRow and self.rowCount.get(self.minRow, 0) == 0:
            self.minRow += 1
        while self.maxRow >= self.minRow and self.rowCount.get(self.maxRow, 0) == 0:
            self.maxRow -= 1
        while self.minCol <= self.maxCol and self.colCount.get(self.minCol, 0) == 0:
            self.minCol += 1
        while self.maxCol >= self.minCol and self.colCount.get(self.maxCol, 0) == 0:
            self.maxCol -= 1

        if self.minRow > self.maxRow or self.minCol > self.maxCol:
            self.reset()

    def reset(self) -> None:
        self.minRow = 0
        self.maxRow = 0
        self.minCol = 0
        self.maxCol = 0
        self.rowCount.clear()
        self.colCount.clear()
        self.isValid = False

    def isOutRange(self, row: int, col: int) -> bool:
        if not self.isValid:
            return True
        return (
            row < self.minRow
            or row > self.maxRow
            or col < self.minCol
            or col > self.maxCol
        )

    def _decrementCount(self, countMap: dict[int, int], key: int) -> None:
        nextCount = countMap.get(key, 0) - 1
        if nextCount <= 0:
            countMap.pop(key, None)
        else:
            countMap[key] = nextCount


@dataclass(slots=True, frozen=True)
class Edge:
    grid1: Grid
    grid2: Grid

    @classmethod
    def between(cls, grid1: Grid, grid2: Grid) -> "Edge":
        if (grid2.row, grid2.col) < (grid1.row, grid1.col):
            grid1, grid2 = grid2, grid1
        return cls(grid1, grid2)
