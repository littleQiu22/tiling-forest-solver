from dataclasses import dataclass
from enum import IntEnum


class MODELING:
    class CONSTRAINT(IntEnum):
        FIGURE_ALIGNED = 1
        ROAD_MUST_EXIT = 2
        STUMP_PAIRED = 3
        ROAD_BLOOM = 4

    class GOAL(IntEnum):
        MIN_UNEXPLORED = 1
        MAX_DENSITY = 2
        MAX_CONNECTIVITY = 3


@dataclass
class SolverOption:
    constraints: list[MODELING.CONSTRAINT]
    goals: list[MODELING.GOAL]
    timeLimit: int | None
    solutionLimit: int | None
