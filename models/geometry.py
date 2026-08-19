from dataclasses import dataclass
from enum import IntEnum

class DIRECTION(IntEnum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

    @property
    def delta(self)->tuple[int,int]:
        match self:
            case DIRECTION.EAST:
                return (0, 1)
            case DIRECTION.WEST:
                return (0, -1)
            case DIRECTION.NORTH:
                return (-1, 0)
            case DIRECTION.SOUTH:
                return (1, 0)
            

@dataclass
class Edge:
    row1: int
    col1: int
    row2: int
    col2: int

@dataclass(slots=True, frozen=True)
class Grid:
    row: int
    col: int

    def edge(self, direction: DIRECTION)->Edge:
        dr, dc = direction.delta
        return Edge(self.row, self.col, self.row + dr, self.col + dc)

    def neighbor(self, direction: DIRECTION)->"Grid":
        dr, dc = direction.delta
        return Grid(self.row + dr, self.col + dc)