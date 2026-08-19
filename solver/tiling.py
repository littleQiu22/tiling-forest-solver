from collections import defaultdict

import cpmpy as cp

from models.puzzle import Puzzle
from models.geometry import DIRECTION
from models.tile import TILE
from solver.option import MODELING, SolverOption
from solver.flow import EDGE_CHANNEL, GRID_CHANNEL, EDGE_FLOW, GRID_FLOW, getEdgeFlow, getGridFlow


class TilingSolver:
    def __init__(self, puzzle: Puzzle, option: SolverOption):
        self._puzzle = puzzle
        self._option = option

        self._reset()

    def _reset(self):
        self._model = cp.Model()

        self._xsPerGrid = defaultdict(list)

        self._isRoadPerGrid = {}
        self._needBloomPerGrid = {}
        self._hasStumpFlowPerGrid = {}

        self._flowsPerEdge = defaultdict(defaultdict[EDGE_CHANNEL, list])
        self._flowsPerGrid = defaultdict(defaultdict[GRID_CHANNEL, list])

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
            self._xsPerGrid[v] = xs

        for v, vData in self._puzzle.placedGrids.items():
            x = cp.boolvar(name=f"x({v.row},{v.col},{vData.tile.name})")
            setattr(x, "tile", vData.tile)
            if vData.tile in TILE.STUMPS and MODELING.CONSTRAINT.STUMP_PAIRED in self._option.constraints:
                self._model.add(x == 1)
            self._xsPerGrid[v] = [x]

        for v in self._puzzle.grids:
            xs = self._xsPerGrid[v]

            for c in EDGE_CHANNEL:
                for d in DIRECTION:
                    flow = sum([getEdgeFlow(c, x.tile, d) * x for x in xs])
                    self._flowsPerEdge[v.edge(d)][c].append(flow)

            for c in GRID_CHANNEL:
                for d in DIRECTION:
                    flow = sum([getGridFlow(c, x.tile, d) * x for x in xs])
                    self._flowsPerGrid[v.neighbor(d)][c].append(flow)

            needBloom = sum([x for x in xs if x.tile in TILE.ROADS])
            self._needBloomPerGrid[v] = needBloom

            isRoad = sum([x for x in xs if x.tile in TILE.ROADS])
            self._isRoadPerGrid[v] = isRoad

        for v in self._puzzle.grids:
            flowsPerChannel = self._flowsPerGrid[v]
            stumpFlow = sum(flowsPerChannel[GRID_CHANNEL.STUMP_HORIZONTAL_CHANNEL]) + \
                sum(flowsPerChannel[GRID_CHANNEL.STUMP_VERTICAL_CHANNEL])

            hasStumpFlow = cp.boolvar(name=f"hasStumpFlow({v.row},{v.col})")
            self._model.add(hasStumpFlow == (stumpFlow > GRID_FLOW.NO_FLOW))
            self._hasStumpFlowPerGrid[v] = hasStumpFlow

        # Add Constraints
        self._addExclusiveConstrs()

        for constr in self._option.constraints:
            match constr:
                case MODELING.CONSTRAINT.FIGURE_ALIGNED:
                    self._addFigureAlignedConstrs()
                case MODELING.CONSTRAINT.STUMP_PAIRED:
                    self._addPairedStumpsConstrs()

    # Constraints
    def _addExclusiveConstrs(self):
        for xs in self._xsPerGrid.values():
            self._model.add(sum(xs) <= 1)

    def _addFigureAlignedConstrs(self):
        for flowsPerChannel in self._flowsPerEdge.values():
            for flows in flowsPerChannel.values():
                if len(flows) >= 2:
                    self._model.add(cp.AllEqual(flows))

    def _addPairedStumpsConstrs(self):
        for flowsPerChannel in self._flowsPerGrid.values():
            for flows in flowsPerChannel.values():
                if len(flows) >= 2:
                    self._model.add(cp.AllEqual(flows))

        for v, hasStumpFlow in self._hasStumpFlowPerGrid.items():
            isRoad = self._isRoadPerGrid[v]
            self._model.add(hasStumpFlow <= isRoad)

    def _addBloomConstrs(self):
        bloomOrderPerGrid = {}
        bloomSourceIdPerGrid = {}
        idPerGrid = {}

        for i, v in enumerate(self._puzzle.grids):
            bloomOrderPerGrid[v] = cp.boolvar(
                name=f"bloomOrder({v.row},{v.col})")
            bloomSourceIdPerGrid[v] = cp.intvar(
                0, self._puzzle.gridCount - 1, name=f"bloomSourceId({v.row},{v.col})")
            idPerGrid[v] = i

        for v in self._puzzle.grids:
            # Bloom source is a root node and thus can determine sourceId property
            asBloomSource = cp.boolvar(name=f"aBloomSource({v.row},{v.col})")
            self._model.add(asBloomSource <= (
                bloomSourceIdPerGrid[v] == idPerGrid[v]))

            # Root node qualification
            hasStumpFlow = self._hasStumpFlowPerGrid[v]
            self._model.add(asBloomSource == hasStumpFlow)

            # Become a source or select a parent
            vNeedBloom = self._needBloomPerGrid[v]
            orderV = bloomOrderPerGrid[v]
            isParents = []
            canParents = []
            for d in DIRECTION:
                u = v.neighbor(d)
                if u not in self._puzzle.grids:
                    continue

                canParent = cp.boolvar(
                    name=f"canBloomParent[({u.row},{u.col}),({v.row},{v.col})]")
                setattr(canParent, "parent", u)
                isParent = cp.boolvar(
                    name=f"isBloomParent[({u.row},{u.col}),({v.row},{v.col})]")
                canParents.append(canParent)
                isParents.append(isParents)

                # Parent qualification
                uNeedBloom = bloomOrderPerGrid[u]
                xs = self._xsPerGrid[u]
                roadFlow = sum([x * getEdgeFlow(EDGE_CHANNEL.CONNECT_CHANNEL, x.tile, d)
                               for x in xs if x in TILE.ROADS])
                self._model.add(canParent ==
                                uNeedBloom & vNeedBloom & (roadFlow > EDGE_FLOW.NO_FLOW))
                self._model.add(isParent <= canParent)

                # Parent transmit sourceId property
                self._model.add(isParent <= (
                    bloomSourceIdPerGrid[u] == bloomSourceIdPerGrid[v]))

                # Avoid cycle
                orderU = bloomOrderPerGrid[u]
                self._model.add(isParent <= (orderU + 1 <= orderV))
            self._model.add(
                vNeedBloom == asBloomSource + sum(isParents)
            )

            # All potential parents must carry the same bloom source
            for canParent in canParents:
                u = canParent.parent
                self._model.add(canParent <= (
                    bloomSourceIdPerGrid[u] == bloomSourceIdPerGrid[v]))
