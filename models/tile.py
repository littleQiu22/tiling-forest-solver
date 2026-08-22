from enum import Enum

from PySide6.QtCore import QObject, QEnum
from PySide6.QtQml import QmlNamedElement, QmlUncreatable


QML_IMPORT_NAME = "app.models"
QML_IMPORT_MAJOR_VERSION = 1


@QmlNamedElement("Tile")
@QmlUncreatable("Tile enums only")
class TILE(QObject):
    class STATUS(Enum):
        NORMAL = 1
        UNEXPLORED = 2
        BLOOMING = 3
    QEnum(STATUS)

    class TYPE(Enum):
        GRASSLAND = 1

        ROAD_WS = 11
        ROAD_WE = 12
        ROAD_WN = 13
        ROAD_ES = 14
        ROAD_EN = 15
        ROAD_NS = 16
        ROAD_E = 17
        ROAD_W = 18
        ROAD_N = 19
        ROAD_S = 20

        CLEARING_EN = 21
        CLEARING_ES = 22
        CLEARING_WS = 23
        CLEARING_WN = 24
        CLEARING_E = 25
        CLEARING_W = 26
        CLEARING_S = 27
        CLEARING_N = 28
        CLEARING = 29

        CLEARING_E_ROAD_W = 31
        CLEARING_W_ROAD_E = 32
        CLEARING_S_ROAD_N = 33
        CLEARING_N_ROAD_S = 34

        STUMP_W = 41
        STUMP_E = 42
        STUMP_N = 43
        STUMP_S = 44
    QEnum(TYPE)

    STUMPS = {TYPE.STUMP_W, TYPE.STUMP_E, TYPE.STUMP_N, TYPE.STUMP_S}
    MIXED_CLEARING_ROADS = {TYPE.CLEARING_E_ROAD_W, TYPE.CLEARING_W_ROAD_E,
                            TYPE.CLEARING_N_ROAD_S, TYPE.CLEARING_S_ROAD_N}
    SIMPLE_ROADS = {TYPE.ROAD_WS, TYPE.ROAD_WN, TYPE.ROAD_EN, TYPE.ROAD_ES,
                    TYPE.ROAD_WE, TYPE.ROAD_NS, TYPE.ROAD_E, TYPE.ROAD_W, TYPE.ROAD_N, TYPE.ROAD_S}
    ROADS = SIMPLE_ROADS | MIXED_CLEARING_ROADS
    SIMPLE_CLEARINGS = {TYPE.CLEARING_EN, TYPE.CLEARING_ES, TYPE.CLEARING_WN,
                        TYPE.CLEARING_WS, TYPE.CLEARING_E, TYPE.CLEARING_S, TYPE.CLEARING_W, TYPE.CLEARING_N,
                        TYPE.CLEARING}
    CLEARINGS = SIMPLE_CLEARINGS | MIXED_CLEARING_ROADS
