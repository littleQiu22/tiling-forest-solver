from collections import defaultdict
from collections.abc import Callable
import time

import cpmpy as cp
from cpmpy.expressions.core import Expression
from cpmpy.solvers.solver_interface import ExitStatus

from models.puzzle import Puzzle
from models.geometry import DIRECTION, Grid, Edge
from models.tile import TILE
from solver.option import MODELING, SolverOption
from solver.flow import CHANNEL_FLOW_DIRECTIONS, EDGE_CHANNEL, GRID_CHANNEL, EDGE_FLOW, GRID_FLOW, getEdgeFlow, getGridFlow
from solver.status import SOLVER_PHASE, SOLVER_STATUS, phaseMessage


class TilingSolver:
    def __init__(self, puzzle: Puzzle, option: SolverOption, callback: Callable[[SOLVER_STATUS, "TilingSolver"], None] | None):
        self._puzzle = puzzle
        self._option = option
        self._callback = callback
        self._phase = SOLVER_PHASE.START
        self._phaseGoal = None
        self._phaseObjectiveValue = None

        self._setPhase(SOLVER_PHASE.BUILD_MODEL)
        self._guardedCallback(SOLVER_STATUS.SOLVING)
        self._buildModel()

    @property
    def phase(self) -> SOLVER_PHASE:
        return self._phase

    @property
    def phaseGoal(self) -> MODELING.GOAL | None:
        return self._phaseGoal

    @property
    def phaseObjectiveValue(self):
        return self._phaseObjectiveValue

    def phaseMessage(self) -> str:
        return phaseMessage(
            self._phase,
            self._phaseGoal,
            self._phaseObjectiveValue,
        )

    def _setPhase(
        self,
        phase: SOLVER_PHASE,
        goal: MODELING.GOAL | None = None,
        objectiveValue=None,
    ) -> None:
        self._phase = phase
        self._phaseGoal = goal
        self._phaseObjectiveValue = objectiveValue

    def _resetModel(self):
        self._deriveGeometry()

        self._model = cp.Model()

        self._xsPerGrid = defaultdict(list)

        self._isSourceExitPerGrid = {}
        self._asConnectSourcePerGrid = {}
        self._needConnectPerGrid = {}

        self._isStumpPairedPerGrid = {}

        self._flowsPerEdge: defaultdict[Edge, defaultdict[EDGE_CHANNEL, list]] = defaultdict(
            lambda: defaultdict(list))
        self._flowsPerGrid: defaultdict[Grid, defaultdict[GRID_CHANNEL, list]] = defaultdict(
            lambda: defaultdict(list))

        self._solutions = []

    def getSolutions(self):
        return self._solutions

    def _deriveGeometry(self):

        def canReachEmptyFrom(start: Grid) -> bool:
            visited = set()
            pendingGrids = [start]
            while pendingGrids:
                grid = pendingGrids.pop()
                if grid not in self._puzzle.grids or grid in visited:
                    continue
                if grid in self._puzzle.emptyGrids:
                    return True

                visited.add(grid)
                gridData = self._puzzle.placedGrids[grid]
                for direction in DIRECTION:
                    neighbor = grid.neighbor(direction)
                    flow = getEdgeFlow(
                        EDGE_CHANNEL.CONNECT_CHANNEL, gridData.tile, direction)
                    if flow > EDGE_FLOW.NO_FLOW:
                        pendingGrids.append(neighbor)
            return False

        # Exits: with outbound flow and can connect to empty grids
        self._exits = set()
        for v, vData in self._puzzle.placedGrids.items():
            withOutsideFlow = False
            if vData.status == TILE.STATUS.UNEXPLORED:
                continue
            for d in DIRECTION:
                u = v.neighbor(d)
                flow = getEdgeFlow(EDGE_CHANNEL.CONNECT_CHANNEL, vData.tile, d)
                # Check whether with outbound flow
                if u not in self._puzzle.grids and flow > EDGE_FLOW.NO_FLOW:
                    withOutsideFlow = True
                    break
            if withOutsideFlow and canReachEmptyFrom(v):
                self._exits.add(v)
        # Fallback 1: if there is no external exit, placed grids that can connect to empty grids can act as exits.
        if not self._exits:
            for v, vData in self._puzzle.placedGrids.items():
                if vData.status == TILE.STATUS.UNEXPLORED:
                    continue
                if canReachEmptyFrom(v):
                    self._exits.add(v)

        # Fallback 2: if even placed grids cannot provide an exit, every empty
        # grid can act as an exit.
        if not self._exits:
            self._exits.update(self._puzzle.emptyGrids)

        unexploredConnectedGrids = set()
        pendingGrids = [
            grid
            for grid, gridData in self._puzzle.placedGrids.items()
            if gridData.status == TILE.STATUS.UNEXPLORED
        ]
        while pendingGrids:
            grid = pendingGrids.pop()
            if grid in unexploredConnectedGrids:
                continue
            unexploredConnectedGrids.add(grid)

            gridData = self._puzzle.placedGrids[grid]
            for direction in DIRECTION:
                neighbor = grid.neighbor(direction)
                neighborData = self._puzzle.placedGrids.get(neighbor)
                if neighborData is None or neighbor in unexploredConnectedGrids:
                    continue

                gridFlow = getEdgeFlow(
                    EDGE_CHANNEL.CONNECT_CHANNEL, gridData.tile, direction)
                if gridFlow > EDGE_FLOW.NO_FLOW:
                    pendingGrids.append(neighbor)

        self._exits.difference_update(unexploredConnectedGrids)

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
            for d in DIRECTION:
                u = v.neighbor(d)
                if u not in self._puzzle.emptyGrids:
                    continue
                flow = getEdgeFlow(EDGE_CHANNEL.CONNECT_CHANNEL, vData.tile, d)
                if flow > EDGE_FLOW.NO_FLOW:
                    self._model.add(sum(self._xsPerGrid[u]) <= x)
            self._xsPerGrid[v] = [x]

        for v in self._puzzle.grids:
            xs = self._xsPerGrid[v]

            for c in EDGE_CHANNEL:
                for d in CHANNEL_FLOW_DIRECTIONS[c]:
                    flow = sum([getEdgeFlow(c, x.tile, d) * x for x in xs])
                    self._flowsPerEdge[v.edge(d)][c].append(flow)

            for c in GRID_CHANNEL:
                for d in CHANNEL_FLOW_DIRECTIONS[c]:
                    flow = sum([getGridFlow(c, x.tile, d) * x for x in xs])
                    self._flowsPerGrid[v.neighbor(d)][c].append(flow)

        # Add Constraints
        self._addNotFullyEmptyConstrs()
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

    def _addNotFullyEmptyConstrs(self):
        placementVars = [
            x
            for grid in self._puzzle.emptyGrids
            for x in self._xsPerGrid[grid]
        ]
        self._model.add(sum(placementVars) >= 1)

    def _addFigureAlignedConstrs(self):
        for edge, flowsPerChannel in self._flowsPerEdge.items():
            flows = flowsPerChannel[EDGE_CHANNEL.CONNECT_CHANNEL]
            if len(flows) >= 2:
                self._model.add(cp.AllEqual(flows))
            else:
                if edge.grid1 in self._puzzle.grids and edge.grid2 in self._puzzle.grids:
                    self._model.add(sum(flows) == 0)

    def _addPairedStumpsConstrs(self):
        for grid, flowsPerChannel in self._flowsPerGrid.items():
            for channel in (
                GRID_CHANNEL.STUMP_HORIZONTAL_CHANNEL,
                GRID_CHANNEL.STUMP_VERTICAL_CHANNEL,
            ):
                flows = flowsPerChannel[channel]
                if len(flows) >= 2:
                    self._model.add(cp.AllEqual(flows))
                else:
                    if grid in self._puzzle.grids:
                        self._model.add(sum(flows) == 0)
        if not self._isStumpPairedPerGrid:
            self._buildIsStumpPairedPerGrid()

    def _addBloomConstrs(self):
        def isBloomingRoad(grid: Grid) -> bool:
            gridData = self._puzzle.placedGrids.get(grid)
            return (
                gridData is not None
                and gridData.status == TILE.STATUS.BLOOMING
                and gridData.tile in TILE.ROADS
            )

        def hasRoadFlow(grid: Grid, direction: DIRECTION) -> bool:
            gridData = self._puzzle.placedGrids.get(grid)
            return (
                gridData is not None
                and gridData.tile in TILE.ROADS
                and getEdgeFlow(
                    EDGE_CHANNEL.CONNECT_CHANNEL,
                    gridData.tile,
                    direction,
                ) == EDGE_FLOW.ROAD_FLOW
            )

        def isConnectedRoadPair(grid: Grid, direction: DIRECTION) -> bool:
            neighbor = grid.neighbor(direction)
            return (
                neighbor in self._puzzle.placedGrids
                and hasRoadFlow(grid, direction)
                and hasRoadFlow(neighbor, direction.opposite())
            )

        def placedRoadGroups() -> list[list[Grid]]:
            groups = []
            visited = set()
            roadGrids = {
                grid
                for grid, gridData in self._puzzle.placedGrids.items()
                if gridData.tile in TILE.ROADS
            }

            for grid in roadGrids:
                if grid in visited:
                    continue

                group = []
                pending = [grid]
                visited.add(grid)
                while pending:
                    current = pending.pop()
                    group.append(current)
                    for direction in DIRECTION:
                        neighbor = current.neighbor(direction)
                        if neighbor not in roadGrids or neighbor in visited:
                            continue
                        if not isConnectedRoadPair(current, direction):
                            continue
                        visited.add(neighbor)
                        pending.append(neighbor)

                groups.append(group)
            return groups

        needBloomPerGrid = {}
        for v in self._puzzle.grids:
            xs = self._xsPerGrid[v]
            needBloomPerGrid[v] = sum([x for x in xs if x.tile in TILE.ROADS])
        if not self._isStumpPairedPerGrid:
            self._buildIsStumpPairedPerGrid()

        bloomOrderPerGrid = {}
        bloomSourceIdPerGrid = {}
        grantAsBloomingSourcePerGrid = {}
        stumpAsBloomingSourcePerGrid = {}

        for v in self._puzzle.grids:
            bloomOrderPerGrid[v] = cp.intvar(
                1, self._puzzle.gridCount,
                name=f"bloomOrder({v.row},{v.col})")
            bloomSourceIdPerGrid[v] = cp.intvar(
                1, self._puzzle.gridCount, name=f"bloomSourceId({v.row},{v.col})")

        for v in self._puzzle.grids:
            # Root node qualification
            isBlooming = isBloomingRoad(v)

            grantAsBloomingSource = cp.boolvar(
                name=f"grantAsBloomingSource({v.row},{v.col})")
            self._model.add(grantAsBloomingSource <= isBlooming)

            stumpAsBloomingSource = self._isStumpPairedPerGrid[v]
            grantAsBloomingSourcePerGrid[v] = grantAsBloomingSource
            stumpAsBloomingSourcePerGrid[v] = stumpAsBloomingSource

            # Root node determines sourceId property
            sourceOwnsId = bloomSourceIdPerGrid[v] == self._idPerGrid[v]
            self._model.add(grantAsBloomingSource <= sourceOwnsId)
            self._model.add(stumpAsBloomingSource <= sourceOwnsId)

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
                isParents.append(isParent)

                # Parent qualification
                xs = self._xsPerGrid[u]
                connectFlow = sum([x * getEdgeFlow(EDGE_CHANNEL.CONNECT_CHANNEL, x.tile, d.opposite())
                                   for x in xs if x.tile])
                self._model.add(
                    canParent
                    == (
                        (needBloomPerGrid[u] > 0)
                        & (needBloomPerGrid[v] > 0)
                        & (connectFlow == EDGE_FLOW.ROAD_FLOW)
                    )
                )
                self._model.add(isParent <= canParent)

                # Parent transmit sourceId property
                self._model.add(isParent <= (
                    bloomSourceIdPerGrid[u] == bloomSourceIdPerGrid[v]))

                # Parent determines order
                self._model.add(isParent <= (
                    bloomOrderPerGrid[u] + 1 <= bloomOrderPerGrid[v]))
            self._model.add(
                needBloomPerGrid[v] <= grantAsBloomingSource +
                stumpAsBloomingSource + sum(isParents)
            )

            # All potential parents must carry the same bloom source
            for canParent in canParents:
                u = canParent.parent
                self._model.add(canParent <= (
                    bloomSourceIdPerGrid[u] == bloomSourceIdPerGrid[v]))

        for group in placedRoadGroups():
            if not any(isBloomingRoad(grid) for grid in group):
                continue
            self._model.add(
                sum(
                    grantAsBloomingSourcePerGrid[grid]
                    + stumpAsBloomingSourcePerGrid[grid]
                    for grid in group
                ) == 1
            )

    def _addConnectivityConstrs(self):
        for v in self._puzzle.grids:
            xs = self._xsPerGrid[v]
            needConnect = sum(
                [x for x in xs if x.tile in (TILE.ROADS | TILE.CLEARINGS)])
            self._needConnectPerGrid[v] = needConnect

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
            self._model.add(asConnectSource <= (
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

                # Parent transmit isSourceExit property
                self._model.add(isParent <= (
                    self._isSourceExitPerGrid[u] == self._isSourceExitPerGrid[v]))

                # Parent determines order
                self._model.add(
                    isParent <= (
                        connectOrderPerGrid[u] + 1 <= connectOrderPerGrid[v])
                )
            self._model.add(
                self._needConnectPerGrid[v] <= asConnectSource + sum(isParents)
            )
            self._model.add(
                self._isSourceExitPerGrid[v] <= self._needConnectPerGrid[v])
            if v in self._exits:
                # Connectivity canonicalization: an active exit uses an exit-rooted tree.
                self._model.add(self._needConnectPerGrid[v] <=
                                self._isSourceExitPerGrid[v])

    def _addRoadMustExitConstrs(self):
        for v in self._puzzle.grids:
            # A road must use exit as its source in connect tree
            xs = self._xsPerGrid[v]
            isRoad = sum([x for x in xs if x.tile in TILE.ROADS])
            self._model.add(
                isRoad <= self._isSourceExitPerGrid[v]
            )

    def _buildIsStumpPairedPerGrid(self):
        for grid in self._puzzle.grids:
            flowsPerChannel = self._flowsPerGrid[grid]
            stumpPairOptions = []
            for channel in (
                GRID_CHANNEL.STUMP_HORIZONTAL_CHANNEL,
                GRID_CHANNEL.STUMP_VERTICAL_CHANNEL,
            ):
                flows = flowsPerChannel[channel]
                if len(flows) == 2:
                    stumpPairOptions.append(cp.all(
                        [flow == GRID_FLOW.STUMP_FLOW for flow in flows]))

            isStumpPaired = cp.boolvar(
                name=f"isStumpPaired({grid.row},{grid.col})")
            if stumpPairOptions:
                self._model.add(isStumpPaired == cp.any(stumpPairOptions))
            else:
                self._model.add(isStumpPaired == 0)
            simpleRoads = [
                x for x in self._xsPerGrid[grid]
                if x.tile in TILE.SIMPLE_ROADS
            ]
            self._model.add(isStumpPaired <= sum(simpleRoads))
            self._isStumpPairedPerGrid[grid] = isStumpPaired

    def _simpleSolve(self, timeLimit: int | None):
        self._model.solve(time_limit=timeLimit)

        status = SOLVER_STATUS.SOLVED
        objValue = None
        solution = {}

        match self._model.status().exitstatus:
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
                self._model.add(self._getConnectivity() == bound)
            case MODELING.GOAL.MAX_DENSITY:
                self._model.add(self._getDensity() == bound)
            case MODELING.GOAL.MIN_UNEXPLORED:
                self._model.add(self._getExitedUnexplored() == bound)

    def _addPlacementNoGoods(self):
        placementVars = [
            x
            for grid in self._puzzle.emptyGrids
            for x in self._xsPerGrid[grid]
        ]
        samePlacement = [var if abs(1 - var.value())
                         < 1e-2 else ~var for var in placementVars]
        self._model.add(sum(samePlacement) <= len(samePlacement) - 1)

    def solve(self):
        self._setPhase(SOLVER_PHASE.START)
        self._guardedCallback(SOLVER_STATUS.SOLVING)

        startedAt = time.monotonic()

        lastSolution = None
        # Optimize goals in order
        for goal in self._option.goals:
            remainingTime = self._remainingTime(startedAt)
            if remainingTime is not None and remainingTime <= 0:
                self._guardedCallback(SOLVER_STATUS.TIME_LIMIT)
                return
            if not self._setGoal(goal):
                continue
            self._setPhase(SOLVER_PHASE.OPTIMIZE_GOAL, goal)
            self._guardedCallback(SOLVER_STATUS.SOLVING)
            status, objValue, solution = self._simpleSolve(remainingTime)

            if status != SOLVER_STATUS.SOLVED:
                self._guardedCallback(status)
                return

            if objValue is not None:
                objValue = int(objValue)
            self._setPhase(SOLVER_PHASE.OPTIMIZE_GOAL, goal, objValue)
            self._guardedCallback(SOLVER_STATUS.SOLVING)
            self._addGoalBound(goal, objValue)
            lastSolution = solution

        # Enumeration more solutions
        self._setPhase(SOLVER_PHASE.ENUMERATION)
        self._model.objective_ = None

        if lastSolution is not None:
            self._solutions.append(lastSolution)
            self._guardedCallback(SOLVER_STATUS.FOUND_SOLUTION)
        solutionLimit = self._option.solutionLimit
        while True:
            if solutionLimit is not None and len(self._solutions) >= solutionLimit:
                self._guardedCallback(SOLVER_STATUS.SOLUTION_LIMIT)
                return

            remainingTime = self._remainingTime(startedAt)
            if remainingTime is not None and remainingTime <= 0:
                self._guardedCallback(SOLVER_STATUS.TIME_LIMIT)
                return

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

    def _remainingTime(self, startedAt):
        if self._option.timeLimit is None:
            return None
        return self._option.timeLimit - (time.monotonic() - startedAt)

    def _guardedCallback(self, status: SOLVER_STATUS):
        if self._callback is not None:
            self._callback(status, self)

    def _setGoal(self, goal: MODELING.GOAL) -> bool:
        match goal:
            case MODELING.GOAL.MAX_CONNECTIVITY:
                self._guaredSetObjective(self._getConnectivity(), True)
            case MODELING.GOAL.MAX_DENSITY:
                self._guaredSetObjective(self._getDensity(), False)
            case MODELING.GOAL.MIN_UNEXPLORED:
                self._guaredSetObjective(self._getExitedUnexplored(), False)
        return True

    def _getDensity(self):
        return sum([sum(xs) for grid, xs in self._xsPerGrid.items(
        ) if grid in self._puzzle.emptyGrids])

    def _getExitedUnexplored(self):
        return sum([isSourceExit for v, isSourceExit in self._isSourceExitPerGrid.items()
                    if (vData := self._puzzle.getGridData(v)) is not None and vData.status == TILE.STATUS.UNEXPLORED])

    def _getConnectivity(self):
        return sum([
            (1 - self._needConnectPerGrid[grid]) +
            self._asConnectSourcePerGrid[grid]
            for grid in self._exits
        ])

    def _guaredSetObjective(self, objExpr, isMinimize):
        if isinstance(objExpr, (int, float)):
            objExpr = objExpr + cp.intvar(0, 0, name="dummy")
        if not isinstance(objExpr, Expression):
            objExpr = cp.intvar(0, 0, name="dummy")
        if isMinimize:
            self._model.minimize(objExpr)
        else:
            self._model.maximize(objExpr)
