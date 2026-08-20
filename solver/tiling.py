from collections import defaultdict
from collections.abc import Callable
import time

import cpmpy as cp
from cpmpy.expressions.core import Expression
from cpmpy.solvers.solver_interface import ExitStatus

from models.puzzle import Puzzle
from models.geometry import DIRECTION
from models.tile import TILE
from solver.option import MODELING, SolverOption
from solver.flow import EDGE_CHANNEL, GRID_CHANNEL, EDGE_FLOW, GRID_FLOW, getEdgeFlow, getGridFlow
from solver.status import SOLVER_STATUS


class TilingSolver:
    def __init__(self, puzzle: Puzzle, option: SolverOption, callback: Callable[[SOLVER_STATUS, "TilingSolver"], None] | None):
        self._puzzle = puzzle
        self._option = option
        self._callback = callback

        self._buildModel()

    def _resetModel(self):
        self._deriveGeometry()

        self._model = cp.Model()

        self._xsPerGrid = defaultdict(list)

        self._isRoadPerGrid = {}
        self._isClearingPerGrid = {}

        self._hasStumpFlowPerGrid = {}

        self._needConnectPerGrid = {}
        self._needBloomPerGrid = {}

        self._asConnectSourcePerGrid = {}
        self._isConnectParentsPerGrid = defaultdict(defaultdict)
        self._isSourceExitPerGrid = {}

        self._flowsPerEdge = defaultdict(defaultdict[EDGE_CHANNEL, list])
        self._flowsPerGrid = defaultdict(defaultdict[GRID_CHANNEL, list])

        self._connectivityMetrics = None

        self._solutions = []

    def getSolutions(self):
        return self._solutions

    def _deriveGeometry(self):
        # Exits
        self._exits = set()
        for v, vData in self._puzzle.placedGrids.items():
            if vData.status == TILE.STATUS.UNEXPLORED:
                continue
            for d in DIRECTION:
                u = v.neighbor(d)
                flow = getEdgeFlow(EDGE_CHANNEL.CONNECT_CHANNEL, vData.tile, d)
                if u not in self._puzzle.grids and flow > EDGE_FLOW.NO_FLOW:
                    self._exits.add(v)
        # Fallback: If the system is perfectly closed, then every grid without unexplored flag is an exit
        if not self._exits:
            for v in self._puzzle.grids:
                vData = self._puzzle.getGridData(v)
                if vData is not None and vData.status == TILE.STATUS.UNEXPLORED:
                    continue
                self._exits.add(v)

        # Ids
        self._idPerGrid = {}
        for i, v in enumerate(self._puzzle.grids):
            self._idPerGrid[v] = i + 1

    def _buildModel(self):
        # Reset global members
        self._resetModel()

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

            isClearing = sum([x for x in xs if x.tile in TILE.CLEARINGS])
            self._isClearingPerGrid[v] = isClearing

            needConnect = sum(
                [x for x in xs if x.tile in (TILE.ROADS | TILE.CLEARINGS)])
            self._needConnectPerGrid[v] = needConnect

        for v in self._puzzle.grids:
            flowsPerChannel = self._flowsPerGrid[v]
            stumpFlow = sum(flowsPerChannel[GRID_CHANNEL.STUMP_HORIZONTAL_CHANNEL]) + \
                sum(flowsPerChannel[GRID_CHANNEL.STUMP_VERTICAL_CHANNEL])

            hasStumpFlow = cp.boolvar(name=f"hasStumpFlow({v.row},{v.col})")
            self._model.add(hasStumpFlow == (stumpFlow > GRID_FLOW.NO_FLOW))
            self._hasStumpFlowPerGrid[v] = hasStumpFlow

        # Add Constraints
        self._addExclusiveConstrs()
        self._addConnectivityConstrs()

        for constr in self._option.constraints:
            match constr:
                case MODELING.CONSTRAINT.FIGURE_ALIGNED:
                    self._addFigureAlignedConstrs()
                case MODELING.CONSTRAINT.STUMP_PAIRED:
                    self._addPairedStumpsConstrs()
                case MODELING.CONSTRAINT.ROAD_BLOOM:
                    self._addBloomConstrs()
                case MODELING.CONSTRAINT.ROAD_MUST_EXIT:
                    self._addRoadMustExitConstrs()

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

        for i, v in enumerate(self._puzzle.grids):
            bloomOrderPerGrid[v] = cp.boolvar(
                name=f"bloomOrder({v.row},{v.col})")
            bloomSourceIdPerGrid[v] = cp.intvar(
                1, self._puzzle.gridCount, name=f"bloomSourceId({v.row},{v.col})")

        for v in self._puzzle.grids:
            # Root node qualification
            vData = self._puzzle.getGridData(v)
            isBlooming = vData is not None and vData.status == TILE.STATUS.BLOOMING
            isExit = v in self._exits

            if isBlooming and isExit:
                # If a tile is blooming and is an exit, then it must have an external blooming source
                selfAsBloomingSource = 1
            else:
                selfAsBloomingSource = cp.boolvar(
                    name=f"selfAsBloomingSource({v.row},{v.col})")
                self._model.add(selfAsBloomingSource <= isBlooming)

            stumpAsBloomingSource = self._hasStumpFlowPerGrid[v]

            # Root node determines sourceId property
            self._model.add((selfAsBloomingSource | stumpAsBloomingSource) <= (
                bloomSourceIdPerGrid[v] == self._idPerGrid[v]))

            # Become a source or select a parent
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
                xs = self._xsPerGrid[u]
                roadFlow = sum([x * getEdgeFlow(EDGE_CHANNEL.CONNECT_CHANNEL, x.tile, d.opposite())
                               for x in xs if x in TILE.ROADS])
                self._model.add(canParent ==
                                self._needBloomPerGrid[u] & self._needBloomPerGrid[v] & (roadFlow > EDGE_FLOW.NO_FLOW))
                self._model.add(isParent <= canParent)

                # Parent transmit sourceId property
                self._model.add(isParent <= (
                    bloomSourceIdPerGrid[u] == bloomSourceIdPerGrid[v]))

                # Parent determines order
                self._model.add(isParent <= (
                    bloomOrderPerGrid[u] + 1 <= bloomOrderPerGrid[v]))
            self._model.add(
                self._needBloomPerGrid[v] == selfAsBloomingSource +
                stumpAsBloomingSource + sum(isParents)
            )

            # All potential parents must carry the same bloom source
            for canParent in canParents:
                u = canParent.parent
                self._model.add(canParent <= (
                    bloomSourceIdPerGrid[u] == bloomSourceIdPerGrid[v]))

    def _addConnectivityConstrs(self):
        connectOrderPerGrid = {}

        for v in self._puzzle.grids:
            isSourceExit = cp.boolvar(name=f"isSourceExit({v.row},{v.col})")
            self._isSourceExitPerGrid[v] = isSourceExit
            connectOrder = cp.intvar(
                1, self._puzzle.gridCount, name=f"connectOrder({v.row},{v.col})")
            connectOrderPerGrid[v] = connectOrder

        for v in self._puzzle.grids:
            # Root node qualification: All grid can be source of connect tree
            asConnectSource = cp.boolvar(
                name=f"isConnectSource({v.row},{v.col})")
            self._asConnectSourcePerGrid[v] = asConnectSource

            # Root node determines isSourceExit property
            isExit = v in self._exits
            self._model.add(self._asConnectSourcePerGrid[v] <= (
                self._isSourceExitPerGrid[v] == isExit))

            # Become a root node or select a parent
            isParents = []
            for d in DIRECTION:
                u = v.neighbor(d)
                if u not in self._puzzle.grids:
                    continue

                # Parent qualification
                isParent = cp.boolvar(
                    name=f"isConnectParent[({u.row},{u.col}),({v.row},{v.col})]")
                isParents.append(isParent)
                xs = self._xsPerGrid[u]
                connectFlow = sum([x * e
                                   for x in xs
                                   if (e := getEdgeFlow(EDGE_CHANNEL.CONNECT_CHANNEL, x.tile, d.opposite())) > EDGE_FLOW.NO_FLOW
                                   ])
                self._model.add(isParent <= self._needConnectPerGrid[v])
                self._model.add(isParent <= self._needConnectPerGrid[u])
                self._model.add(isParent <= connectFlow)

                self._isConnectParentsPerGrid[v][u] = isParent

                # Parent transmit isSourceExit property
                for u, isParent in self._isConnectParentsPerGrid[v].items():
                    self._model.add(isParent <= (
                        self._isSourceExitPerGrid[u] == self._isSourceExitPerGrid[v]))

                # Parent determines order
                self._model.add(
                    isParent <= (
                        connectOrderPerGrid[u] + 1 <= connectOrderPerGrid[v])
                )
            self._model.add(
                self._needConnectPerGrid[v] == asConnectSource + sum(isParents)
            )

        # Connectivity metrics
        self._connectivityMetrics = sum(
            [isConnectSource for isConnectSource in self._asConnectSourcePerGrid.values()])

    def _addRoadMustExitConstrs(self):
        for v in self._puzzle.grids:
            # A road must use exit as its source in connect tree
            self._model.add(
                self._isRoadPerGrid[v] <= self._isSourceExitPerGrid[v]
            )

    def _simpleSolve(self, timeLimit: int | None):
        self._model.solve(time_limit=timeLimit)

        status = SOLVER_STATUS.SOLVED
        objValue = None
        solution = {}

        match self._model.status():
            case ExitStatus.FEASIBLE:
                if self._model.has_objective():
                    status = SOLVER_STATUS.TIME_LIMIT
                else:
                    status = SOLVER_STATUS.SOLVED
            case ExitStatus.OPTIMAL:
                status = SOLVER_STATUS.SOLVED
            case ExitStatus.UNSATISFIABLE:
                status = SOLVER_STATUS.INFEASIBLE
            case _:
                status = SOLVER_STATUS.INTERNAL_ERROR

        if status == SOLVER_STATUS.SOLVED:
            objValue = self._model.objective_value()

            for v in self._puzzle.emptyGrids:
                for x in self._xsPerGrid[v]:
                    if abs(1 - x.value()) < 1e-2:
                        solution[v] = x.tile

        return status, objValue, solution

    def _addGoalBound(self, goal: MODELING.GOAL, bound):
        match goal:
            case MODELING.GOAL.MAX_CONNECTIVITY:
                if self._connectivityMetrics is not None and type(self._connectivityMetrics) != int:
                    self._model.add(self._connectivityMetrics == bound)
            case MODELING.GOAL.MAX_DENSITY:
                density = sum([sum(xs) for xs in self._xsPerGrid.values()])
                self._model.add(density == bound)
            case MODELING.GOAL.MAX_EXITED_UNEXPLORE:
                exitedUnexplore = sum(
                    [isSourceExit for v, isSourceExit in self._isSourceExitPerGrid.items()
                     if (vData := self._puzzle.getGridData(v)) is not None and vData.status == TILE.STATUS.UNEXPLORED])
                self._model.add(exitedUnexplore == bound)

    def _addPlacementNoGoods(self):
        placementVars = [x for xs in self._xsPerGrid.values() for x in xs]
        samePlacement = [var if abs(1 - var.value())
                         < 1e-2 else ~var for var in placementVars]
        self._model.add(sum(samePlacement) <= len(samePlacement) - 1)

    def solve(self):
        if self._callback is not None:
            self._callback(SOLVER_STATUS.START, self)

        startedAt = time.monotonic()

        lastSolution = None
        # Optimize goals in order
        for goal in self._option.goals:
            remainingTime = self._remainingTime(startedAt)
            if remainingTime is not None and remainingTime <= 0:
                self._guardedCallback(SOLVER_STATUS.TIME_LIMIT)
            self._setGoal(goal)
            status, objValue, solution = self._simpleSolve(remainingTime)

            if status != SOLVER_STATUS.SOLVED:
                self._guardedCallback(status)
                return

            self._addGoalBound(goal, objValue)
            lastSolution = solution

        # Enumeration more solutions
        self._model.objective_ = None

        if lastSolution is not None:
            self._solutions.append(lastSolution)
        solutionLimit = self._option.solutionLimit
        while solutionLimit is not None and len(self._solutions) < solutionLimit:
            remainingTime = self._remainingTime(startedAt)
            if remainingTime is not None and remainingTime <= 0:
                self._guardedCallback(SOLVER_STATUS.TIME_LIMIT)

            if lastSolution is not None:
                self._addPlacementNoGoods()

            status, _, solution = self._simpleSolve(
                timeLimit=remainingTime)

            if status != SOLVER_STATUS.SOLVED:
                match status:
                    case SOLVER_STATUS.INFEASIBLE:
                        if len(self._solutions) > 0:
                            self._guardedCallback(SOLVER_STATUS.SOLVED)
                        else:
                            self._guardedCallback(SOLVER_STATUS.INFEASIBLE)
                    case _:
                        self._guardedCallback(status)
                return

            self._solutions.append(solution)
            self._guardedCallback(SOLVER_STATUS.FOUND_SOLUTION)
            lastSolution = solution

        if solutionLimit is not None:
            self._guardedCallback(SOLVER_STATUS.SOLUTION_LIMIT)

    def _remainingTime(self, startedAt):
        if self._option.timeLimit is None:
            return None
        return self._option.timeLimit - (time.monotonic() - startedAt)

    def _guardedCallback(self, status: SOLVER_STATUS):
        if self._callback is not None:
            self._callback(status, self)

    def _setGoal(self, goal: MODELING.GOAL):
        match goal:
            case MODELING.GOAL.MAX_CONNECTIVITY:
                if self._connectivityMetrics is not None and type(self._connectivityMetrics) != int:
                    self._guaredSetObjective(self._connectivityMetrics, True)
            case MODELING.GOAL.MAX_DENSITY:
                density = sum([sum(xs) for xs in self._xsPerGrid.values()])
                self._guaredSetObjective(density, False)
            case MODELING.GOAL.MAX_EXITED_UNEXPLORE:
                exitedUnexplore = sum(
                    [isSourceExit for v, isSourceExit in self._isSourceExitPerGrid.items()
                     if (vData := self._puzzle.getGridData(v)) is not None and vData.status == TILE.STATUS.UNEXPLORED])
                self._guaredSetObjective(exitedUnexplore, False)

    def _guaredSetObjective(self, objExpr, isMinimize):
        if isinstance(objExpr, (int, float)):
            objExpr = objExpr + cp.intvar(0, 0, name="dummy")
        if not isinstance(objExpr, Expression):
            objExpr = cp.intvar(0, 0, name="dummy")
        if isMinimize:
            self._model.minimize(objExpr)
        else:
            self._model.maximize(objExpr)
