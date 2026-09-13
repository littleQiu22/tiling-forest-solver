from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, QProcess, Slot

from common import BASE_ROOT, solverWorkerCommand
from models.geometry import Grid
from models.puzzle import Puzzle, PuzzleListModel, PuzzleState, Solution, PuzzleSolveStatus
from models.tile import tileTypeFromJson
from solver.status import SOLVER_STATUS


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

        puzzleState.solutions = []
        puzzleState.currentSolutionIndex = -1
        puzzleState.solvingLog = ""
        puzzleState.solveStatus = PuzzleSolveStatus.SOLVING
        self._emitStateChanged(
            puzzle.id,
            [
                PuzzleListModel.CurrentSolutionRole,
                PuzzleListModel.SolutionCountRole,
                PuzzleListModel.CurrentSolutionIndexRole,
                PuzzleListModel.SolvingLogRole,
                PuzzleListModel.SolveStatusRole,
                PuzzleListModel.ResultStatusRole,
            ],
        )
        self._workspace._markBackgroundDirty()

        program, arguments = solverWorkerCommand()
        process = QProcess(self)
        process.setProperty("puzzleId", puzzle.id)
        process.setWorkingDirectory(str(BASE_ROOT.resolve()))
        self._processes[puzzle.id] = process
        self._buffers[process] = ""

        process.readyReadStandardOutput.connect(self._readStdout)
        process.readyReadStandardError.connect(self._readStderr)
        process.finished.connect(self._finished)

        process.start(program, arguments)
        if not process.waitForStarted(3000):
            self._dropProcess(process)
            self._handleEvent(puzzle.id, {
                "status": SOLVER_STATUS.INTERNAL_ERROR.value,
                "message": "Failed to start solver process.",
            })
            return False

        process.write(json.dumps(self._solverRequest(
            puzzle, puzzleState)).encode("utf-8"))
        process.closeWriteChannel()
        return True

    @Slot(str)
    def stop(self, puzzleId: str) -> None:
        process = self._processes.get(puzzleId)
        if process is not None:
            self._handleEvent(puzzleId, {
                "status": SOLVER_STATUS.INTERRUPTED.value,
                "message": "Solver interrupted.",
            })
            process.kill()

    @Slot()
    def stopAll(self) -> None:
        for puzzleId in list(self._processes):
            self.stop(puzzleId)

    def _solverRequest(self, puzzle: Puzzle, puzzleState: PuzzleState) -> dict[str, Any]:
        return {
            "puzzle": puzzle.toJson(),
            "constraints": [
                constraint.name
                for constraint in puzzleState.enabledConstraints
            ],
            "objectives": [
                objective.name
                for objective in puzzleState.objectiveOrder
                if objective in puzzleState.enabledObjectives
            ],
            "timeLimit": puzzleState.timeLimit if puzzleState.isTimeLimitEnabled else None,
            "solutionLimit": puzzleState.solutionLimit if puzzleState.isSolutionLimitEnabled else None,
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
                "status": SOLVER_STATUS.INTERNAL_ERROR.value,
                "message": text,
            })

    def _finished(self, _exitCode: int, _exitStatus: QProcess.ExitStatus) -> None:
        process = self.sender()
        if not isinstance(process, QProcess):
            return

        self._dropProcess(process)

    def _handleEvent(self, puzzleId: str, event: dict[str, Any]) -> None:
        state = self._workspace._puzzles.puzzleStateById(puzzleId)
        if state is None:
            return

        roles: list[int] = []

        message = event.get("message", None)
        if message is not None:
            state.solvingLog += self._logLine(str(message))
            roles.append(PuzzleListModel.SolvingLogRole)

        solution = event.get("solution", None)
        if solution is not None:
            state.solutions.append(self._solutionFromJson(solution))
            if state.currentSolutionIndex == -1:
                state.currentSolutionIndex = 0
            roles.extend([
                PuzzleListModel.CurrentSolutionRole,
                PuzzleListModel.SolutionCountRole,
                PuzzleListModel.CurrentSolutionIndexRole,
                PuzzleListModel.ResultStatusRole,
            ])

        status = event.get("status", None)
        if status is not None:
            state.solveStatus = SOLVER_STATUS(str(status))
            roles.extend([
                PuzzleListModel.SolveStatusRole,
                PuzzleListModel.ResultStatusRole,
            ])

        if not roles:
            return

        self._workspace._markBackgroundDirty()
        self._emitStateChanged(puzzleId, roles)

    def _solutionFromJson(self, data: list[dict[str, Any]]) -> Solution:
        return {
            Grid(int(item["row"]), int(item["col"])): tileTypeFromJson(item["tile"])
            for item in data
        }

    def _logLine(self, message: str) -> str:
        return f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n"

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
