import itertools as it
from dataclasses import dataclass

from models.geometry import Grid
from models.tile import TILE


@dataclass(frozen=True)
class GridData():
    tile: TILE.TYPE
    status: TILE.STATUS


@dataclass
class Puzzle:
    def __init__(self) -> None:
        self.emptyGrids: set[Grid] = set()
        self.placedGrids: dict[Grid, GridData] = {}
        self.tilePool: list[TILE.TYPE] = []

    @property
    def grids(self):
        return it.chain(self.emptyGrids, self.placedGrids)

    @property
    def gridCount(self):
        return len(self.emptyGrids) + len(self.placedGrids)

    def getGridData(self, grid: Grid) -> GridData | None:
        return self.placedGrids.get(grid, None)
