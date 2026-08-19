from dataclasses import dataclass
from enum import IntEnum


class MODELING:
    class CONSTRAINT(IntEnum):
        FIGURE_ALIGNED = 1
        STUMP_PAIRED = 2
        ROAD_BLOOM = 3

    class GOAL(IntEnum):
        MAX_CONNECTIVITY = 1
        MAX_DENSITY = 2
        MIN_UNEXPLORED_ROAD = 3


@dataclass
class SolverOption:
    constraints: list[MODELING.CONSTRAINT]
    goals: list[MODELING.GOAL]
    timeLimit: int
    solutionLimit: int
