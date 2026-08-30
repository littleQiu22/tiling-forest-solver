from enum import Enum


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
