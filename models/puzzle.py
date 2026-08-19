from models.geometry import Grid
from tile import TILE

class TileGrid(Grid):
    tile: TILE.TYPE
    status: TILE.STATUS

class Puzzle:
    def __init__(self) -> None:
        self.emptyGrids: set[Grid] = set()
        self.placedGrids: set[TileGrid] = set()
        self.tilePool: list[TILE.TYPE] = []