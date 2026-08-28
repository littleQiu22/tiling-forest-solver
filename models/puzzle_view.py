from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtQml import QmlElement

from models.puzzle import (
    DEFAULT_CONSTRAINTS,
    TILE_POOL_CANDIDATES,
    Puzzle,
    PuzzleSolveStatus,
    PuzzleState,
    constraintLabel,
    objectiveLabel,
)

if TYPE_CHECKING:
    from models.workspace import Workspace


QML_IMPORT_NAME = "app.models"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class PuzzleView(QObject):
    puzzleChanged = Signal()

    def __init__(self, workspace: "Workspace", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workspace = workspace
        self._puzzleId = ""

        puzzles = self._workspace._puzzles
        puzzles.modelReset.connect(self._sync)
        puzzles.rowsInserted.connect(self._sync)
        puzzles.rowsRemoved.connect(self._sync)
        puzzles.dataChanged.connect(self._sync)
        puzzles.puzzleStateChanged.connect(self._syncPuzzleState)

    @Property(bool, notify=puzzleChanged)
    def hasPuzzle(self) -> bool:
        return self._puzzle() is not None

    @Property(str, notify=puzzleChanged)
    def puzzleId(self) -> str:
        return self._puzzleId

    @Property(str, notify=puzzleChanged)
    def name(self) -> str:
        puzzle = self._puzzle()
        return "" if puzzle is None else puzzle.name

    @Property(str, notify=puzzleChanged)
    def solveStatus(self) -> str:
        state = self._state()
        return PuzzleSolveStatus.UNSOLVED.value if state is None else state.solveStatus.value

    @Property(bool, notify=puzzleChanged)
    def isGeometryStaled(self) -> bool:
        state = self._state()
        return False if state is None else state.isGeometryStaled

    @Property("QVariantList", constant=True)
    def tilePoolCandidates(self) -> list[dict[str, Any]]:
        return [{"tile": tile.value} for tile in TILE_POOL_CANDIDATES]

    @Property("QVariantList", notify=puzzleChanged)
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

    @Property("QVariantList", notify=puzzleChanged)
    def objectiveItems(self) -> list[dict[str, Any]]:
        state = self._state()
        if state is None:
            return []
        return [
            {
                "key": objective,
                "label": objectiveLabel(objective),
                "enabled": objective in state.enabledObjectives,
            }
            for objective in state.objectiveOrder
        ]

    @Property("QVariantList", notify=puzzleChanged)
    def constraintItems(self) -> list[dict[str, Any]]:
        state = self._state()
        enabledConstraints = set(DEFAULT_CONSTRAINTS) if state is None else state.enabledConstraints
        return [
            {
                "key": constraint,
                "label": constraintLabel(constraint),
                "enabled": constraint in enabledConstraints,
            }
            for constraint in DEFAULT_CONSTRAINTS
        ]

    @Property(int, notify=puzzleChanged)
    def timeLimit(self) -> int:
        state = self._state()
        return 0 if state is None else state.timeLimit

    @Property(int, notify=puzzleChanged)
    def solutionLimit(self) -> int:
        state = self._state()
        return 0 if state is None else state.solutionLimit

    @Property(int, notify=puzzleChanged)
    def solutionCount(self) -> int:
        state = self._state()
        return 0 if state is None else len(state.solutions)

    @Property(int, notify=puzzleChanged)
    def currentSolutionIndex(self) -> int:
        state = self._state()
        return -1 if state is None else state.currentSolutionIndex

    @Property(str, notify=puzzleChanged)
    def solvingLog(self) -> str:
        state = self._state()
        return "" if state is None else state.solvingLog

    @Slot(str)
    def select(self, puzzleId: str) -> None:
        if self._puzzleId == puzzleId:
            return
        self._puzzleId = puzzleId
        self._sync()

    def _puzzle(self) -> Puzzle | None:
        if not self._puzzleId:
            return None
        return self._workspace._puzzles.puzzleById(self._puzzleId)

    def _state(self) -> PuzzleState | None:
        if not self._puzzleId:
            return None
        return self._workspace._puzzles.puzzleStateById(self._puzzleId)

    def _sync(self, *args: Any) -> None:
        if self._puzzleId and self._puzzle() is None:
            self._puzzleId = ""
        self.puzzleChanged.emit()

    @Slot(str)
    def _syncPuzzleState(self, puzzleId: str) -> None:
        if puzzleId == self._puzzleId:
            self._sync()
