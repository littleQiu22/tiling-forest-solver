from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtQml import QmlElement

from manager.solving_manager import SolvingManager
from models.geometry import Grid
from models.puzzle import (
    Puzzle,
    PuzzleListModel,
    PuzzleSolveStatus,
    PuzzleState,
    extractPuzzle,
)
from models.puzzle_view import PuzzleView
from models.tile import (
    TILE,
    TileData,
    TileListModel,
    tileStatusFromQml,
    tileTypeFromQml,
)


QML_IMPORT_NAME = "app.models"
QML_IMPORT_MAJOR_VERSION = 1

WORKSPACE_VERSION = 1
DEFAULT_OPERATION_CAPACITY = 512


class Operation(ABC):
    @abstractmethod
    def execute(self, workspace: "Workspace") -> None:
        ...

    @abstractmethod
    def undo(self, workspace: "Workspace") -> None:
        ...

    def executeHeavyReason(self, workspace: "Workspace") -> str:
        return ""

    def undoHeavyReason(self, workspace: "Workspace") -> str:
        return ""


class OperationStack:
    def __init__(
        self,
        workspace: "Workspace",
        capacity: int | None = DEFAULT_OPERATION_CAPACITY,
    ) -> None:
        self._workspace = workspace
        self._capacity = capacity
        self._operations: list[Operation] = []
        self._cursor = 0
        self._cleanCursor = 0

    @property
    def canUndo(self) -> bool:
        return self._cursor > 0

    @property
    def canRedo(self) -> bool:
        return self._cursor < len(self._operations)

    @property
    def isDirty(self) -> bool:
        return self._cursor != self._cleanCursor

    def apply(self, operation: Operation) -> None:
        if self._cursor < len(self._operations):
            if self._cleanCursor > self._cursor:
                self._cleanCursor = -1
            del self._operations[self._cursor:]

        operation.execute(self._workspace)
        self._operations.append(operation)
        self._cursor += 1
        self._trimToCapacity()

    def undo(self) -> None:
        if not self.canUndo:
            return

        self._cursor -= 1
        self._operations[self._cursor].undo(self._workspace)

    def redo(self) -> None:
        if not self.canRedo:
            return

        self._operations[self._cursor].execute(self._workspace)
        self._cursor += 1

    def reset(self) -> None:
        self._operations = []
        self._cursor = 0
        self._cleanCursor = 0

    def markClean(self) -> None:
        self._cleanCursor = self._cursor

    def undoHeavyReason(self) -> str:
        if not self.canUndo:
            return ""
        return self._operations[self._cursor - 1].undoHeavyReason(self._workspace)

    def _trimToCapacity(self) -> None:
        if self._capacity is None or len(self._operations) <= self._capacity:
            return

        removeCount = len(self._operations) - self._capacity
        del self._operations[:removeCount]
        self._cursor = max(0, self._cursor - removeCount)

        if self._cleanCursor == -1:
            return
        if self._cleanCursor < removeCount:
            self._cleanCursor = -1
        else:
            self._cleanCursor -= removeCount


class EditTileOperation(Operation):
    def __init__(
        self,
        grid: Grid,
        oldTile: TileData | None,
        newTile: TileData | None,
    ) -> None:
        self.grid = grid
        self.oldTile = oldTile
        self.newTile = newTile

    def execute(self, workspace: "Workspace") -> None:
        workspace._setTileData(self.grid, self.newTile)

    def undo(self, workspace: "Workspace") -> None:
        workspace._setTileData(self.grid, self.oldTile)


class AddPuzzleOperation(Operation):
    def __init__(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle
        self.puzzleState: PuzzleState | None = None

    def execute(self, workspace: "Workspace") -> None:
        workspace._addPuzzle(self.puzzle, self.puzzleState)

    def undo(self, workspace: "Workspace") -> None:
        self.puzzleState = workspace._puzzles.puzzleStateById(self.puzzle.id)
        workspace._removePuzzleById(self.puzzle.id)

    def undoHeavyReason(self, workspace: "Workspace") -> str:
        puzzleState = workspace._puzzles.puzzleStateById(self.puzzle.id)
        if puzzleState is None:
            return ""
        if puzzleState.solveStatus == PuzzleSolveStatus.SOLVING:
            return "Undoing this puzzle creation will stop its running solver process."
        return ""


class RemovePuzzleOperation(Operation):
    def __init__(self, index: int, puzzle: Puzzle, puzzleState: PuzzleState | None) -> None:
        self.index = index
        self.puzzle = puzzle
        self.puzzleState = puzzleState

    def execute(self, workspace: "Workspace") -> None:
        workspace._removePuzzleById(self.puzzle.id)

    def undo(self, workspace: "Workspace") -> None:
        workspace._insertPuzzle(self.index, self.puzzle, self.puzzleState)

    def executeHeavyReason(self, workspace: "Workspace") -> str:
        puzzleState = workspace._puzzles.puzzleStateById(self.puzzle.id)
        if puzzleState is None:
            return ""
        if puzzleState.solveStatus == PuzzleSolveStatus.SOLVING:
            return "Deleting this puzzle will stop its running solver process."
        return ""


class ClearWorkspaceOperation(Operation):
    def __init__(
        self,
        tiles: list[TileData],
        puzzles: list[Puzzle],
        puzzleStates: dict[str, PuzzleState],
    ) -> None:
        self.tiles = tiles
        self.puzzles = puzzles
        self.puzzleStates = puzzleStates

    def execute(self, workspace: "Workspace") -> None:
        workspace._setTiles([])
        workspace._setPuzzles([])

    def undo(self, workspace: "Workspace") -> None:
        workspace._setTiles(self.tiles)
        workspace._setPuzzles(self.puzzles)
        workspace._puzzles.setStates(self.puzzleStates)

    def executeHeavyReason(self, workspace: "Workspace") -> str:
        for puzzle in self.puzzles:
            puzzleState = workspace._puzzles.puzzleStateById(puzzle.id)
            if puzzleState is not None and puzzleState.solveStatus == PuzzleSolveStatus.SOLVING:
                return "Clearing the workspace will stop running solver processes."
        return ""


class RenamePuzzleOperation(Operation):
    def __init__(self, puzzleId: str, oldName: str, newName: str) -> None:
        self.puzzleId = puzzleId
        self.oldName = oldName
        self.newName = newName

    def execute(self, workspace: "Workspace") -> None:
        workspace._puzzles.setPuzzleName(self.puzzleId, self.newName)

    def undo(self, workspace: "Workspace") -> None:
        workspace._puzzles.setPuzzleName(self.puzzleId, self.oldName)


@QmlElement
class Workspace(QObject):
    isDirtyChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tiles = TileListModel(self)
        self._puzzles = PuzzleListModel(self)
        self._solvingManager = SolvingManager(self, self)
        self._puzzleView = PuzzleView(self, self)
        self._operationStack = OperationStack(self)
        self._isBackgroundDirty = False

    @Property(QObject, constant=True)
    def tiles(self) -> TileListModel:
        return self._tiles

    @Property(QObject, constant=True)
    def puzzles(self) -> PuzzleListModel:
        return self._puzzles

    @Property(QObject, constant=True)
    def puzzleView(self) -> PuzzleView:
        return self._puzzleView

    @Property(bool, notify=isDirtyChanged)
    def isDirty(self) -> bool:
        return self._isBackgroundDirty or self._operationStack.isDirty

    @Slot(int, int, int, result=str)
    @Slot(int, int, int, bool, result=str)
    def paintTile(
        self,
        row: int,
        col: int,
        tile: int,
        isQueryHeavyReason: bool = False,
    ) -> str:
        grid = Grid(row, col)
        newTile = TileData(
            row=grid.row,
            col=grid.col,
            tile=tileTypeFromQml(tile),
            status=TILE.STATUS.NORMAL,
        )
        oldTile = self._tiles.tileAt(grid)
        if oldTile == newTile:
            return ""

        return self._queryOrApplyOperation(
            EditTileOperation(grid, oldTile, newTile),
            isQueryHeavyReason,
        )

    @Slot(int, int, result=str)
    @Slot(int, int, bool, result=str)
    def eraseTile(
        self,
        row: int,
        col: int,
        isQueryHeavyReason: bool = False,
    ) -> str:
        grid = Grid(row, col)
        oldTile = self._tiles.tileAt(grid)
        if oldTile is None:
            return ""

        return self._queryOrApplyOperation(
            EditTileOperation(grid, oldTile, None),
            isQueryHeavyReason,
        )

    @Slot(int, int, int, result=str)
    @Slot(int, int, int, bool, result=str)
    def setTileStatus(
        self,
        row: int,
        col: int,
        status: int,
        isQueryHeavyReason: bool = False,
    ) -> str:
        grid = Grid(row, col)
        oldTile = self._tiles.tileAt(grid)
        if oldTile is None:
            return ""

        newTile = TileData(
            row=oldTile.row,
            col=oldTile.col,
            tile=oldTile.tile,
            status=tileStatusFromQml(status),
        )
        if oldTile == newTile:
            return ""

        return self._queryOrApplyOperation(
            EditTileOperation(grid, oldTile, newTile),
            isQueryHeavyReason,
        )

    @Slot(int, int, result=str)
    @Slot(int, int, bool, result=str)
    def resetTileStatus(
        self,
        row: int,
        col: int,
        isQueryHeavyReason: bool = False,
    ) -> str:
        return self.setTileStatus(
            row,
            col,
            TILE.STATUS.NORMAL.value,
            isQueryHeavyReason,
        )

    @Slot(int, int, result=str)
    @Slot(int, int, bool, result=str)
    def selectOrCreatePuzzle(
        self,
        row: int,
        col: int,
        isQueryHeavyReason: bool = False,
    ) -> str:
        grid = Grid(int(row), int(col))
        existingPuzzle = self._puzzles.puzzleContaining(grid)
        if existingPuzzle is not None:
            if not isQueryHeavyReason:
                self._puzzleView.select(existingPuzzle.id)
            return ""

        extraction = extractPuzzle(
            self._tiles.tileMap(),
            self._tiles.boundingBox(),
            grid,
        )
        if extraction.message:
            return extraction.message
        if extraction.puzzle is None:
            return ""

        message = self._queryOrApplyOperation(
            AddPuzzleOperation(extraction.puzzle),
            isQueryHeavyReason,
        )
        if not isQueryHeavyReason:
            self._puzzleView.select(extraction.puzzle.id)
        return message

    @Slot(str, result=str)
    @Slot(str, bool, result=str)
    def deletePuzzle(
        self,
        puzzleId: str,
        isQueryHeavyReason: bool = False,
    ) -> str:
        index = self._puzzles.indexById(puzzleId)
        if index == -1:
            return ""

        puzzle = self._puzzles.puzzleAt(index)
        if puzzle is None:
            return ""

        return self._queryOrApplyOperation(
            RemovePuzzleOperation(
                index, puzzle, self._puzzles.puzzleStateById(puzzle.id)),
            isQueryHeavyReason,
        )

    @Slot(int, int, result=str)
    @Slot(int, int, bool, result=str)
    def deletePuzzleAt(
        self,
        row: int,
        col: int,
        isQueryHeavyReason: bool = False,
    ) -> str:
        grid = Grid(row, col)
        index = self._puzzles.indexContaining(grid)
        if index == -1:
            return ""

        puzzle = self._puzzles.puzzleAt(index)
        if puzzle is None:
            return ""

        return self._queryOrApplyOperation(
            RemovePuzzleOperation(
                index, puzzle, self._puzzles.puzzleStateById(puzzle.id)),
            isQueryHeavyReason,
        )

    @Slot(result=str)
    @Slot(bool, result=str)
    def clear(self, isQueryHeavyReason: bool = False) -> str:
        if not self._tiles.tiles() and not self._puzzles.puzzles():
            return ""

        return self._queryOrApplyOperation(
            ClearWorkspaceOperation(
                self._tiles.tiles(), self._puzzles.puzzles(), self._puzzles.states()),
            isQueryHeavyReason,
        )

    @Slot()
    def undo(self) -> None:
        self._operationStack.undo()
        self._emitOperationStateChanged()

    @Slot()
    def redo(self) -> None:
        self._operationStack.redo()
        self._emitOperationStateChanged()

    @Slot(result=str)
    def getUndoHeavyReason(self) -> str:
        return self._operationStack.undoHeavyReason()

    @Slot(str)
    def selectPuzzle(self, puzzleId: str) -> None:
        self._puzzleView.select(puzzleId)

    @Slot(str, str)
    def renamePuzzle(self, puzzleId: str, name: str) -> None:
        index = self._puzzles.indexById(puzzleId)
        puzzle = self._puzzles.puzzleAt(index)
        if puzzle is None:
            return

        nextName = name.strip() or f"Puzzle {index + 1}"
        if puzzle.name == nextName:
            return

        self._applyOperation(RenamePuzzleOperation(puzzleId, puzzle.name, nextName))

    @Slot(str, int, bool)
    def setPuzzleTileEnabled(self, puzzleId: str, tile: int, enabled: bool) -> None:
        puzzle = self._puzzles.puzzleById(puzzleId)
        if puzzle is None:
            return

        tileType = tileTypeFromQml(tile)
        tilePool = list(puzzle.tilePool)
        if enabled and tileType not in tilePool:
            tilePool.append(tileType)
        elif not enabled and tileType in tilePool:
            tilePool.remove(tileType)
        else:
            return

        self._puzzles.setPuzzleTilePool(puzzleId, tilePool)
        self._markBackgroundDirty()

    @Slot(str, str, bool)
    def setPuzzleObjectiveEnabled(self, puzzleId: str, objective: str, enabled: bool) -> None:
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzleState is None:
            return
        if enabled:
            puzzleState.enabledObjectives.add(objective)
        else:
            puzzleState.enabledObjectives.discard(objective)
        self._puzzles.emitPuzzleChanged(puzzleId, [PuzzleListModel.ObjectiveItemsRole])
        self._markBackgroundDirty()

    @Slot(str, str, int)
    def movePuzzleObjective(self, puzzleId: str, objective: str, delta: int) -> None:
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzleState is None or objective not in puzzleState.objectiveOrder:
            return

        oldIndex = puzzleState.objectiveOrder.index(objective)
        newIndex = max(0, min(len(puzzleState.objectiveOrder) - 1, oldIndex + delta))
        if oldIndex == newIndex:
            return

        puzzleState.objectiveOrder.pop(oldIndex)
        puzzleState.objectiveOrder.insert(newIndex, objective)
        self._puzzles.emitPuzzleChanged(puzzleId, [PuzzleListModel.ObjectiveItemsRole])
        self._markBackgroundDirty()

    @Slot(str, str, bool)
    def setPuzzleConstraintEnabled(self, puzzleId: str, constraint: str, enabled: bool) -> None:
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzleState is None:
            return
        if enabled:
            puzzleState.enabledConstraints.add(constraint)
        else:
            puzzleState.enabledConstraints.discard(constraint)
        self._puzzles.emitPuzzleChanged(puzzleId, [PuzzleListModel.ConstraintItemsRole])
        self._markBackgroundDirty()

    @Slot(str, int)
    def setPuzzleTimeLimit(self, puzzleId: str, timeLimit: int) -> None:
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzleState is None:
            return
        puzzleState.timeLimit = max(0, int(timeLimit))
        self._puzzles.emitPuzzleChanged(puzzleId, [PuzzleListModel.TimeLimitRole])
        self._markBackgroundDirty()

    @Slot(str, int)
    def setPuzzleSolutionLimit(self, puzzleId: str, solutionLimit: int) -> None:
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzleState is None:
            return
        puzzleState.solutionLimit = max(0, int(solutionLimit))
        self._puzzles.emitPuzzleChanged(puzzleId, [PuzzleListModel.SolutionLimitRole])
        self._markBackgroundDirty()

    @Slot(str)
    def previousPuzzleSolution(self, puzzleId: str) -> None:
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzleState is not None:
            self.setPuzzleCurrentSolutionIndex(puzzleId, puzzleState.currentSolutionIndex - 1)

    @Slot(str)
    def nextPuzzleSolution(self, puzzleId: str) -> None:
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzleState is not None:
            self.setPuzzleCurrentSolutionIndex(puzzleId, puzzleState.currentSolutionIndex + 1)

    @Slot(str, int)
    def setPuzzleCurrentSolutionIndex(self, puzzleId: str, solutionIndex: int) -> None:
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzleState is None or not puzzleState.solutions:
            return

        puzzleState.currentSolutionIndex = max(0, min(int(solutionIndex), len(puzzleState.solutions) - 1))
        self._puzzles.emitPuzzleChanged(
            puzzleId,
            [
                PuzzleListModel.CurrentSolutionRole,
                PuzzleListModel.CurrentSolutionIndexRole,
            ],
        )

    @Slot(str)
    def solvePuzzle(self, puzzleId: str) -> None:
        puzzle = self._puzzles.puzzleById(puzzleId)
        puzzleState = self._puzzles.puzzleStateById(puzzleId)
        if puzzle is not None and puzzleState is not None:
            if not self._rebuildPuzzleIfStaled(puzzle, puzzleState):
                return
            puzzle = self._puzzles.puzzleById(puzzleId)
            if puzzle is None:
                return
            self._solvingManager.start(puzzle, puzzleState)

    @Slot(str)
    def stopSolver(self, puzzleId: str) -> None:
        self.stopSolvingPuzzle(puzzleId)

    @Slot()
    def stopAllSolvers(self) -> None:
        self._solvingManager.stopAll()

    def stopSolvingPuzzle(self, puzzleId: str) -> None:
        self._solvingManager.stop(puzzleId)

    def newDocument(self) -> None:
        self.stopAllSolvers()
        self.loadJson(self.emptyJson())

    def markClean(self) -> None:
        self._operationStack.markClean()
        self._isBackgroundDirty = False
        self.isDirtyChanged.emit()

    def toJson(self) -> dict[str, Any]:
        return {
            "version": WORKSPACE_VERSION,
            "tiles": self._tiles.toJson(),
            "puzzles": self._puzzles.toJson(),
            "puzzleStates": self._puzzles.statesToJson(),
        }

    def loadJson(
        self,
        data: dict[str, Any],
    ) -> None:
        self.stopAllSolvers()
        tiles = [TileData.fromJson(tile) for tile in data.get("tiles", [])]
        puzzles = [Puzzle.fromJson(puzzle)
                   for puzzle in data.get("puzzles", [])]

        self._setTiles(tiles)
        self._setPuzzles(puzzles)
        self._puzzles.loadStatesJson(data.get("puzzleStates", {}))
        self._puzzleView.select("")

        self._operationStack.reset()
        self.markClean()

    @classmethod
    def emptyJson(cls) -> dict[str, Any]:
        return {"version": WORKSPACE_VERSION, "tiles": [], "puzzles": []}

    def _applyOperation(self, operation: Operation) -> None:
        self._operationStack.apply(operation)
        self._emitOperationStateChanged()

    def _queryOrApplyOperation(
        self,
        operation: Operation,
        isQueryHeavyReason: bool,
    ) -> str:
        if isQueryHeavyReason:
            return operation.executeHeavyReason(self)

        self._applyOperation(operation)
        return ""

    def _setTileData(self, grid: Grid, tile: TileData | None) -> None:
        if tile is None:
            self._tiles.removeTile(grid)
        else:
            self._tiles.upsertTile(tile)
        staledPuzzleId = self._puzzles.markGeometryStaledByGrid(grid)

    def _rebuildPuzzleIfStaled(
        self,
        puzzle: Puzzle,
        puzzleState: PuzzleState,
    ) -> bool:
        if not puzzleState.isGeometryStaled:
            return True

        seed = next(
            (
                grid
                for grid in sorted(puzzle.emptyGrids, key=lambda item: (item.row, item.col))
                if self._tiles.tileAt(grid) is None
            ),
            None,
        )
        if seed is None:
            self._setPuzzleSolveMessage(
                puzzle.id,
                puzzleState,
                "Cannot rebuild stale puzzle: no empty seed grid remains.",
            )
            return False

        extraction = extractPuzzle(
            self._tiles.tileMap(),
            self._tiles.boundingBox(),
            seed,
        )
        if extraction.message:
            self._setPuzzleSolveMessage(puzzle.id, puzzleState, extraction.message)
            return False
        if extraction.puzzle is None:
            self._setPuzzleSolveMessage(
                puzzle.id,
                puzzleState,
                "Cannot rebuild stale puzzle from the selected empty seed.",
            )
            return False

        if self._puzzles.replacePuzzleGeometry(puzzle.id, extraction.puzzle):
            puzzleState.isGeometryStaled = False
            self._puzzles.emitPuzzleChanged(
                puzzle.id,
                [PuzzleListModel.IsGeometryStaledRole],
            )
            self._markBackgroundDirty()
        return True

    def _setPuzzleSolveMessage(
        self,
        puzzleId: str,
        puzzleState: PuzzleState,
        message: str,
    ) -> None:
        puzzleState.solveStatus = PuzzleSolveStatus.UNSOLVED
        puzzleState.solvingLog = message + "\n"
        self._puzzles.emitPuzzleChanged(
            puzzleId,
            [
                PuzzleListModel.SolveStatusRole,
                PuzzleListModel.SolvingLogRole,
            ],
        )

    def _setTiles(self, tiles: list[TileData]) -> None:
        self._tiles.setTiles(tiles)

    def _removeTile(self, grid: Grid) -> None:
        self._tiles.removeTile(grid)

    def _setPuzzles(self, puzzles: list[Puzzle]) -> None:
        if not puzzles:
            self.stopAllSolvers()
        self._puzzles.setPuzzles(puzzles)

    def _addPuzzle(self, puzzle: Puzzle, puzzleState: PuzzleState | None = None) -> int:
        if puzzleState is None:
            return self._puzzles.addPuzzle(puzzle)
        return self._puzzles.insertPuzzle(len(self._puzzles.puzzles()), puzzle, puzzleState)

    def _insertPuzzle(self, index: int, puzzle: Puzzle, puzzleState: PuzzleState | None = None) -> int:
        return self._puzzles.insertPuzzle(index, puzzle, puzzleState)

    def _removePuzzleById(self, puzzleId: str) -> Puzzle | None:
        self.stopSolvingPuzzle(puzzleId)
        removedPuzzle = self._puzzles.removePuzzleById(puzzleId)
        if self._puzzleView.puzzleId == puzzleId:
            self._puzzleView.select("")
        return removedPuzzle

    def _markBackgroundDirty(self) -> None:
        if self._isBackgroundDirty:
            return
        self._isBackgroundDirty = True
        self.isDirtyChanged.emit()

    def _emitOperationStateChanged(self) -> None:
        self.isDirtyChanged.emit()
