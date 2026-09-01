from __future__ import annotations

import json
import sys
from typing import Any

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
            for constraint in request["constraints"]
        ],
        goals=[
            MODELING.GOAL[str(goal)]
            for goal in request["objectives"]
        ],
        timeLimit=request["timeLimit"],
        solutionLimit=request["solutionLimit"],
    )

    def callback(status: SOLVER_STATUS, solver: TilingSolver) -> None:
        if status == SOLVER_STATUS.SOLVING:
            emit({
                "status": SOLVER_STATUS.SOLVING.value,
                "message": solver.phaseMessage(),
            })
            return

        if status == SOLVER_STATUS.FOUND_SOLUTION:
            solutions = solver.getSolutions()
            if solutions:
                lastSolution = solutions[-1]
                emit({
                    "solution": solutionToJson(lastSolution),
                    "message": f"Found solution {len(solutions)} with {len(lastSolution)} tiles.",
                })
            return

        emit({
            "status": status.value,
            "message": f"Solver finished: {status.value}.",
        })

    solver = TilingSolver(puzzle, option, callback)
    solver.solve()


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
        solveRequest(request)
    except Exception as error:
        emit({
            "status": SOLVER_STATUS.INTERNAL_ERROR.value,
            "message": "Solver error: " + str(error),
        })
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
