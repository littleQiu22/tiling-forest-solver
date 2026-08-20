from dataclasses import dataclass
from enum import IntEnum


class DIRECTION(IntEnum):
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


@dataclass(slots=True, frozen=True)
class Edge:
    grid1: Grid
    grid2: Grid

    @classmethod
    def between(cls, grid1: Grid, grid2: Grid) -> "Edge":
        if (grid2.row, grid2.col) < (grid1.row, grid1.col):
            grid1, grid2 = grid2, grid1
        return cls(grid1, grid2)
