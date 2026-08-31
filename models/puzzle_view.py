from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QModelIndex, QObject, Property, Signal, Slot
from PySide6.QtQml import QmlElement

from models.puzzle import (
    TILE_POOL_CANDIDATES,
    Puzzle,
    PuzzleListModel,
    PuzzleSolveStatus,
    PuzzleState,
)
from solver.option import MODELING

if TYPE_CHECKING:
    from models.workspace import Workspace


QML_IMPORT_NAME = "app.models"
QML_IMPORT_MAJOR_VERSION = 1


def enumLabel(enumValue: MODELING.GOAL | MODELING.CONSTRAINT) -> str:
    return enumValue.name.replace("_", " ").capitalize()


@QmlElement
class PuzzleView(QObject):
    requestPuzzleFocus = Signal(str)
    puzzleIdChanged = Signal()
    hasPuzzleChanged = Signal()
    nameChanged = Signal()
    solveStatusChanged = Signal()
    isGeometryStaledChanged = Signal()
    tilePoolItemsChanged = Signal()
    objectiveItemsChanged = Signal()
    constraintItemsChanged = Signal()
    timeLimitChanged = Signal()
    solutionLimitChanged = Signal()
    solutionCountChanged = Signal()
    currentSolutionIndexChanged = Signal()
    solvingLogChanged = Signal()

    def __init__(self, workspace: "Workspace", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workspace = workspace
        self._puzzleId = ""

        puzzles = self._workspace._puzzles
        puzzles.modelReset.connect(self._syncPuzzleExistence)
        puzzles.rowsRemoved.connect(self._syncPuzzleExistence)
        puzzles.rowsMoved.connect(self._syncPuzzleMove)
        puzzles.dataChanged.connect(self._syncPuzzleData)

    @Property(bool, notify=hasPuzzleChanged)
    def hasPuzzle(self) -> bool:
        return self._puzzle() is not None

    @Property(str, notify=puzzleIdChanged)
    def puzzleId(self) -> str:
        return self._puzzleId

    @Property(str, notify=nameChanged)
    def name(self) -> str:
        puzzle = self._puzzle()
        return "" if puzzle is None else puzzle.name

    @Property(str, notify=solveStatusChanged)
    def solveStatus(self) -> str:
        state = self._state()
        return PuzzleSolveStatus.UNSOLVED.value if state is None else state.solveStatus.value

    @Property(bool, notify=isGeometryStaledChanged)
    def isGeometryStaled(self) -> bool:
        state = self._state()
        return False if state is None else state.isGeometryStaled

    @Property("QVariantList", notify=tilePoolItemsChanged)
    def tilePoolItems(self) -> list[dict[str, Any]]:
        puzzle = self._puzzle()
        tilePool = set() if puzzle is None else set(puzzle.tilePool)
        return [
            {
                "tile": tile.value,
                "enabled": tile in tilePool,
            }
            for tile in TILE_POOL_CANDIDATES
        ]

    @Property("QVariantList", notify=objectiveItemsChanged)
    def objectiveItems(self) -> list[dict[str, Any]]:
        state = self._state()
        if state is None:
            return []
        return [
            {
                "key": objective.name,
                "label": enumLabel(objective),
                "enabled": objective in state.enabledObjectives,
            }
            for objective in state.objectiveOrder
        ]

    @Property("QVariantList", notify=constraintItemsChanged)
    def constraintItems(self) -> list[dict[str, Any]]:
        state = self._state()
        enabledConstraints = set() if state is None else state.enabledConstraints
        return [
            {
                "key": constraint.name,
                "label": enumLabel(constraint),
                "enabled": constraint in enabledConstraints,
            }
            for constraint in MODELING.CONSTRAINT
        ]

    @Property(bool, notify=timeLimitChanged)
    def hasTimeLimit(self) -> bool:
        state = self._state()
        return state is not None and state.isTimeLimitEnabled

    @Property(int, notify=timeLimitChanged)
    def timeLimit(self) -> int:
        state = self._state()
        if state is None:
            return 0
        return state.timeLimit

    @Property(bool, notify=solutionLimitChanged)
    def hasSolutionLimit(self) -> bool:
        state = self._state()
        return state is not None and state.isSolutionLimitEnabled

    @Property(int, notify=solutionLimitChanged)
    def solutionLimit(self) -> int:
        state = self._state()
        if state is None:
            return 0
        return state.solutionLimit

    @Property(int, notify=solutionCountChanged)
    def solutionCount(self) -> int:
        state = self._state()
        return 0 if state is None else len(state.solutions)

    @Property(int, notify=currentSolutionIndexChanged)
    def currentSolutionIndex(self) -> int:
        state = self._state()
        return -1 if state is None else state.currentSolutionIndex

    @Property(str, notify=solvingLogChanged)
    def solvingLog(self) -> str:
        state = self._state()
        return "" if state is None else state.solvingLog

    @Slot(str)
    def select(self, puzzleId: str) -> None:
        if puzzleId:
            self.requestPuzzleFocus.emit(puzzleId)

        if self._puzzleId == puzzleId:
            return

        self._workspace._puzzles.setPuzzleSelected(self._puzzleId, False)
        self._puzzleId = puzzleId
        self._workspace._puzzles.setPuzzleSelected(self._puzzleId, True)
        self._emitAllChanged()

    def _puzzle(self) -> Puzzle | None:
        if not self._puzzleId:
            return None
        return self._workspace._puzzles.puzzleById(self._puzzleId)

    def _state(self) -> PuzzleState | None:
        if not self._puzzleId:
            return None
        return self._workspace._puzzles.puzzleStateById(self._puzzleId)

    def _currentIndex(self) -> int:
        if not self._puzzleId:
            return -1
        return self._workspace._puzzles.indexById(self._puzzleId)

    def _syncPuzzleExistence(self, *args: Any) -> None:
        if not self._puzzleId:
            return
        if self._puzzle() is not None:
            return
        self._puzzleId = ""
        self._emitAllChanged()

    def _syncPuzzleMove(
        self,
        parent: QModelIndex,
        sourceStart: int,
        sourceEnd: int,
        destination: QModelIndex,
        destinationRow: int,
    ) -> None:
        puzzles = self._workspace._puzzles
        movedIndex = destinationRow - 1 if sourceStart < destinationRow else destinationRow
        movedPuzzle = puzzles.puzzleAt(movedIndex)
        if movedPuzzle is not None:
            self.select(movedPuzzle.id)

    def _syncPuzzleData(
        self,
        topLeft: QModelIndex,
        bottomRight: QModelIndex,
        roles: list[int],
    ) -> None:
        currentIndex = self._currentIndex()
        if currentIndex == -1:
            self._syncPuzzleExistence()
            return
        if not topLeft.row() <= currentIndex <= bottomRight.row():
            return

        if not roles or PuzzleListModel.NameRole in roles:
            self.nameChanged.emit()
        if not roles or PuzzleListModel.TilePoolRole in roles:
            self.tilePoolItemsChanged.emit()
        if not roles or PuzzleListModel.IsGeometryStaledRole in roles:
            self.isGeometryStaledChanged.emit()
        if not roles or PuzzleListModel.SolveStatusRole in roles:
            self.solveStatusChanged.emit()
        if not roles or PuzzleListModel.ObjectiveItemsRole in roles:
            self.objectiveItemsChanged.emit()
        if not roles or PuzzleListModel.ConstraintItemsRole in roles:
            self.constraintItemsChanged.emit()
        if not roles or PuzzleListModel.TimeLimitRole in roles:
            self.timeLimitChanged.emit()
        if not roles or PuzzleListModel.SolutionLimitRole in roles:
            self.solutionLimitChanged.emit()
        if not roles or PuzzleListModel.SolutionCountRole in roles:
            self.solutionCountChanged.emit()
        if not roles or PuzzleListModel.CurrentSolutionIndexRole in roles:
            self.currentSolutionIndexChanged.emit()
        if not roles or PuzzleListModel.CurrentSolutionRole in roles:
            self.solutionCountChanged.emit()
            self.currentSolutionIndexChanged.emit()
        if not roles or PuzzleListModel.SolvingLogRole in roles:
            self.solvingLogChanged.emit()

    def _emitAllChanged(self) -> None:
        self.puzzleIdChanged.emit()
        self.hasPuzzleChanged.emit()
        self.nameChanged.emit()
        self.solveStatusChanged.emit()
        self.isGeometryStaledChanged.emit()
        self.tilePoolItemsChanged.emit()
        self.objectiveItemsChanged.emit()
        self.constraintItemsChanged.emit()
        self.timeLimitChanged.emit()
        self.solutionLimitChanged.emit()
        self.solutionCountChanged.emit()
        self.currentSolutionIndexChanged.emit()
        self.solvingLogChanged.emit()
