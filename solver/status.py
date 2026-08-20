from enum import IntEnum


class SOLVER_STATUS(IntEnum):
    START = 1
    FOUND_SOLUTION = 2
    TIME_LIMIT = 3
    SOLUTION_LIMIT = 4
    INFEASIBLE = 5
    SOLVED = 6
    INTERNAL_ERROR = 7
