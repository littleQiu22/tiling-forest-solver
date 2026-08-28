from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.geometry import Grid
from models.puzzle import Puzzle
from models.tile import TILE
from solver.option import MODELING, SolverOption
from solver.status import SOLVER_STATUS
from solver.tiling import TilingSolver


def emit(data: dict[str, Any]) -> None:
    print(json.dumps(data, separators=(",", ":")), flush=True)


def solutionToJson(solution: dict[Grid, TILE.TYPE]) -> list[dict[str, Any]]:
    return [
        {
            "row": grid.row,
            "col": grid.col,
            "tile": tile.name,
        }
        for grid, tile in sorted(solution.items(), key=lambda item: (item[0].row, item[0].col))
    ]


def solveRequest(request: dict[str, Any]) -> None:
    puzzle = Puzzle.fromJson(request["puzzle"])
    option = SolverOption(
        constraints=[
            MODELING.CONSTRAINT[str(constraint)]
            for constraint in request.get("constraints", [])
        ],
        goals=[
            MODELING.GOAL[str(goal)]
            for goal in request.get("objectives", [])
        ],
        timeLimit=request.get("timeLimit"),
        solutionLimit=request.get("solutionLimit"),
    )

    def callback(status: SOLVER_STATUS, solver: TilingSolver) -> None:
        if status == SOLVER_STATUS.START:
            emit({"event": "status", "status": "Solving"})
            emit({"event": "log", "message": "Solver started."})
            return

        if status == SOLVER_STATUS.FOUND_SOLUTION:
            solutions = solver.getSolutions()
            if solutions:
                emit({
                    "event": "solution",
                    "solution": solutionToJson(solutions[-1]),
                })
                emit({"event": "log", "message": f"Found solution {len(solutions)}."})
            return

        statusName = {
            SOLVER_STATUS.TIME_LIMIT: "TimeLimit",
            SOLVER_STATUS.SOLUTION_LIMIT: "SolutionLimit",
            SOLVER_STATUS.INFEASIBLE: "Infeasible",
            SOLVER_STATUS.SOLVED: "Solved",
        }.get(status, "Unsolved")
        emit({"event": "done", "status": statusName})
        emit({"event": "log", "message": f"Solver finished: {statusName}."})

    solver = TilingSolver(puzzle, option, callback)
    solver.solve()


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
        solveRequest(request)
    except Exception as error:
        emit({"event": "error", "message": str(error)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
