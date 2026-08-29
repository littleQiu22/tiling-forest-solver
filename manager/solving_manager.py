from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QProcess, Slot

from common import solverWorkerCommand
from models.geometry import Grid
from models.puzzle import Puzzle, PuzzleListModel, PuzzleSolveStatus, PuzzleState, Solution
from models.tile import tileTypeFromJson

if TYPE_CHECKING:
    from models.workspace import Workspace


class SolvingManager(QObject):
    def __init__(
        self,
        workspace: "Workspace",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace = workspace
        self._processes: dict[str, QProcess] = {}
        self._buffers: dict[QProcess, str] = {}

    def isSolving(self, puzzleId: str) -> bool:
        return puzzleId in self._processes

    def start(self, puzzle: Puzzle, puzzleState: PuzzleState) -> bool:
        if puzzle.id in self._processes:
            return False

        puzzleState.solveStatus = PuzzleSolveStatus.SOLVING
        puzzleState.solutions = []
        puzzleState.currentSolutionIndex = -1
        puzzleState.solvingLog = "Solver starting...\n"
        puzzleState.isGeometryStaled = False
        self._emitStateChanged(
            puzzle.id,
            [
                PuzzleListModel.SolveStatusRole,
                PuzzleListModel.IsGeometryStaledRole,
                PuzzleListModel.CurrentSolutionRole,
                PuzzleListModel.SolutionCountRole,
                PuzzleListModel.CurrentSolutionIndexRole,
                PuzzleListModel.SolvingLogRole,
            ],
        )

        program, arguments = solverWorkerCommand()
        process = QProcess(self)
        process.setProperty("puzzleId", puzzle.id)
        self._processes[puzzle.id] = process
        self._buffers[process] = ""

        process.readyReadStandardOutput.connect(self._readStdout)
        process.readyReadStandardError.connect(self._readStderr)
        process.finished.connect(self._finished)

        process.start(program, arguments)
        if not process.waitForStarted(3000):
            self._dropProcess(process)
            self._handleEvent(puzzle.id, {
                "event": "error",
                "message": "Failed to start solver process.",
            })
            return False

        process.write(json.dumps(self._solverRequest(puzzle, puzzleState)).encode("utf-8"))
        process.closeWriteChannel()
        return True

    @Slot(str)
    def stop(self, puzzleId: str) -> None:
        process = self._processes.get(puzzleId)
        if process is not None:
            process.kill()

    @Slot()
    def stopAll(self) -> None:
        for puzzleId in list(self._processes):
            self.stop(puzzleId)

    def _solverRequest(self, puzzle: Puzzle, puzzleState: PuzzleState) -> dict[str, Any]:
        return {
            "puzzle": puzzle.toJson(),
            "constraints": sorted(puzzleState.enabledConstraints),
            "objectives": [
                objective
                for objective in puzzleState.objectiveOrder
                if objective in puzzleState.enabledObjectives
            ],
            "timeLimit": None if puzzleState.timeLimit <= 0 else puzzleState.timeLimit,
            "solutionLimit": None if puzzleState.solutionLimit <= 0 else puzzleState.solutionLimit,
        }

    def _readStdout(self) -> None:
        process = self.sender()
        if not isinstance(process, QProcess):
            return

        puzzleId = process.property("puzzleId")
        if not isinstance(puzzleId, str):
            return

        text = self._buffers.get(process, "") + bytes(
            process.readAllStandardOutput(),
        ).decode("utf-8")
        self._buffers[process] = ""

        for line in text.splitlines(keepends=True):
            if not line.endswith("\n"):
                self._buffers[process] = line
                continue

            line = line.strip()
            if line:
                self._handleEvent(puzzleId, json.loads(line))

    def _readStderr(self) -> None:
        process = self.sender()
        if not isinstance(process, QProcess):
            return

        puzzleId = process.property("puzzleId")
        if not isinstance(puzzleId, str):
            return

        text = bytes(process.readAllStandardError()).decode("utf-8")
        if text:
            self._handleEvent(puzzleId, {
                "event": "stderr",
                "message": text,
            })

    def _finished(self, exitCode: int, exitStatus: QProcess.ExitStatus) -> None:
        process = self.sender()
        if not isinstance(process, QProcess):
            return

        puzzleId = process.property("puzzleId")
        self._dropProcess(process)
        if isinstance(puzzleId, str):
            self._handleEvent(puzzleId, {
                "event": "processFinished",
                "exitCode": exitCode,
            })

    def _handleEvent(self, puzzleId: str, event: dict[str, Any]) -> None:
        state = self._workspace._puzzles.puzzleStateById(puzzleId)
        if state is None:
            return

        match event.get("event"):
            case "status":
                state.solveStatus = PuzzleSolveStatus(event.get("status", "Unsolved"))
                self._emitStateChanged(
                    puzzleId,
                    [PuzzleListModel.SolveStatusRole],
                )
            case "solution":
                state.solutions.append(self._solutionFromJson(event.get("solution", [])))
                if state.currentSolutionIndex == -1:
                    state.currentSolutionIndex = 0
                self._workspace._markBackgroundDirty()
                self._emitStateChanged(
                    puzzleId,
                    [
                        PuzzleListModel.CurrentSolutionRole,
                        PuzzleListModel.SolutionCountRole,
                        PuzzleListModel.CurrentSolutionIndexRole,
                    ],
                )
            case "done":
                state.solveStatus = PuzzleSolveStatus(event.get("status", "Unsolved"))
                self._workspace._markBackgroundDirty()
                self._emitStateChanged(
                    puzzleId,
                    [PuzzleListModel.SolveStatusRole],
                )
            case "log":
                state.solvingLog += str(event.get("message", "")) + "\n"
                self._emitStateChanged(puzzleId, [PuzzleListModel.SolvingLogRole])
            case "stderr":
                state.solvingLog += str(event.get("message", ""))
                self._emitStateChanged(puzzleId, [PuzzleListModel.SolvingLogRole])
            case "error":
                state.solveStatus = PuzzleSolveStatus.UNSOLVED
                state.solvingLog += "Solver error: " + str(event.get("message", "")) + "\n"
                self._emitStateChanged(
                    puzzleId,
                    [PuzzleListModel.SolveStatusRole, PuzzleListModel.SolvingLogRole],
                )
            case "processFinished":
                if state.solveStatus == PuzzleSolveStatus.SOLVING:
                    state.solveStatus = PuzzleSolveStatus.UNSOLVED
                    state.solvingLog += f"Solver stopped with exit code {event.get('exitCode', -1)}.\n"
                    self._emitStateChanged(
                        puzzleId,
                        [PuzzleListModel.SolveStatusRole, PuzzleListModel.SolvingLogRole],
                    )

    def _solutionFromJson(self, data: list[dict[str, Any]]) -> Solution:
        return {
            Grid(int(item["row"]), int(item["col"])): tileTypeFromJson(item["tile"])
            for item in data
        }

    def _emitStateChanged(
        self,
        puzzleId: str,
        roles: list[int],
    ) -> None:
        self._workspace._puzzles.emitPuzzleChanged(puzzleId, roles)

    def _dropProcess(self, process: QProcess) -> None:
        puzzleId = process.property("puzzleId")
        if isinstance(puzzleId, str):
            self._processes.pop(puzzleId, None)
        self._buffers.pop(process, None)
        process.deleteLater()
