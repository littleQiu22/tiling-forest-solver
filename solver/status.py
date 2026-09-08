from enum import Enum
from typing import Any

from solver.option import MODELING


class SOLVER_STATUS(Enum):
    UNSOLVED = "Unsolved"
    SOLVING = "Solving"
    FOUND_SOLUTION = "FoundSolution"
    TIME_LIMIT = "TimeLimit"
    SOLUTION_LIMIT = "SolutionLimit"
    INFEASIBLE = "Infeasible"
    SOLVED = "Solved"
    INTERNAL_ERROR = "InternalError"
    INTERRUPTED = "Interrupted"


class SOLVER_PHASE(Enum):
    BUILD_MODEL = "BuildModel"
    START = "Start"
    OPTIMIZE_GOAL = "OptimizeGoal"
    ENUMERATION = "Enumeration"


def phaseMessage(
    phase: SOLVER_PHASE,
    goal: MODELING.GOAL | None = None,
    objectiveValue: Any = None,
) -> str:
    match phase:
        case SOLVER_PHASE.BUILD_MODEL:
            return "Building solver model..."
        case SOLVER_PHASE.OPTIMIZE_GOAL:
            if goal is None:
                return "Optimizing goal..."
            if objectiveValue is None:
                return f"Optimizing goal: {goal.name}"
            match goal:
                case MODELING.GOAL.MIN_UNEXPLORED:
                    return f"Number of connected unexplored tiles: {objectiveValue}."
                case MODELING.GOAL.MAX_DENSITY:
                    return f"Number of placed tiles: {objectiveValue}."
                case MODELING.GOAL.MAX_CONNECTIVITY:
                    return f"Number of connected components of exits: {objectiveValue}."
                case _:
                    return f"Optimizing goal: {goal.name}"
        case SOLVER_PHASE.ENUMERATION:
            return "Enumerating solutions..."
        case SOLVER_PHASE.START:
            return "Solver started."
