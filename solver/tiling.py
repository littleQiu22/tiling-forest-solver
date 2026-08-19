from collections import defaultdict
import itertools as it

import cpmpy as cp

from models.puzzle import Puzzle
from models.geometry import DIRECTION
from models.tile import TILE
from solver.option import MODELING, SolverOption
from solver.flow import EDGE_CHANNEL, GRID_CHANNEL, getEdgeFlow, getGridFlow


class TilingSolver:
    def __init__(self, puzzle: Puzzle, option: SolverOption):
        self._puzzle = puzzle
        self._option = option

        self._reset()

    def _reset(self):
        self._model = cp.Model()

        self._xPerEmptyGrid = defaultdict(list)
        self._activePerPlacedGrid = {}
        self._needBloomPerGrid = {}

        self._flowPerEdge = defaultdict(defaultdict[EDGE_CHANNEL, list])
        self._flowPerGrid = defaultdict(defaultdict[GRID_CHANNEL, list])

    def _buildModel(self):
        # Reset global members
        self._reset()

        # Decisions & Expressions
        for v in self._puzzle.emptyGrids:
            xs = []
            for tile in self._puzzle.tilePool:
                x = cp.boolvar(name=f"x({v.row},{v.col},{tile.name})")
                setattr(x, "tile", tile)
                xs.append(x)

            for c in EDGE_CHANNEL:
                for d in DIRECTION:
                    flow = sum([getEdgeFlow(c, x.tile, d) for x in xs])
                    self._flowPerEdge[v.edge(d)][c].append(flow)

            for c in GRID_CHANNEL:
                for d in DIRECTION:
                    flow = sum([getGridFlow(c, x.tile, d) for x in xs])
                    self._flowPerGrid[v.neighbor(d)][c].append(flow)

            needBloom = sum([x for x in xs if x.tile in TILE.ROADS])
            self._needBloomPerGrid[v] = needBloom

        for v in self._puzzle.placedGrids:
            active = cp.boolvar(name=f"y({v.row},{v.col},{v.tile.name})")
            self._activePerPlacedGrid[v] = active

            for c in EDGE_CHANNEL:
                flow = getEdgeFlow(c, v.tile, d) * active
                self._flowPerEdge[v.edge(d)][c].append(flow)

            for c in GRID_CHANNEL:
                flow = getGridFlow(c, v.tile, d) * active
                self._flowPerGrid[v.neighbor(d)][c].append(flow)

            needBloom = v.tile in TILE.ROADS
            self._needBloomPerGrid[v] = needBloom

        # Add Constraints
        self._addExclusiveConstrs()

        for constr in self._option.constraints:
            match constr:
                case MODELING.CONSTRAINT.FIGURE_ALIGNED:
                    self._addFigureAlignedConstrs()
                case MODELING.CONSTRAINT.PAIRED_STUMPS:
                    self._addPairedStumpsConstrs()

    # Constraints
    def _addExclusiveConstrs(self):
        for xs in self._xPerEmptyGrid.values():
            self._model.add(sum(xs) <= 1)

    def _addFigureAlignedConstrs(self):
        for flowPerChannel in self._flowPerEdge.values():
            for fs in flowPerChannel.values():
                if len(fs) >= 2:
                    self._model.add(cp.AllEqual(fs))

    def _addPairedStumpsConstrs(self):
        for flowPerChannel in self._flowPerGrid.values():
            for fs in flowPerChannel.values():
                if len(fs) >= 2:
                    self._model.add(cp.AllEqual(fs))

    def _addBloomConstrs(self):
        for v in it.chain(self._puzzle.emptyGrids, self._puzzle.placedGrids):
            asBloomSource = cp.boolvar(name=f"aBloomSource({v.row},{v.col})")

            # Exmption Qualification
            hasStumpFlow = 1
            self._model.add(asBloomSource == hasStumpFlow)
        ...
