pragma Singleton
import QtQuick

import app.models

QtObject {
    id: root

    readonly property url logo: Qt.resolvedUrl("assets/logo.png")
    readonly property int tileSize: TileSpec.size

    function tileImage(tile) {
        switch (tile) {
        case Tile.GRASSLAND:
            return Qt.resolvedUrl("assets/tiles/grassland.png");
        case Tile.ROAD_WS:
            return Qt.resolvedUrl("assets/tiles/road_WS.png");
        case Tile.ROAD_WE:
            return Qt.resolvedUrl("assets/tiles/road_WE.png");
        case Tile.ROAD_WN:
            return Qt.resolvedUrl("assets/tiles/road_WN.png");
        case Tile.ROAD_ES:
            return Qt.resolvedUrl("assets/tiles/road_ES.png");
        case Tile.ROAD_EN:
            return Qt.resolvedUrl("assets/tiles/road_EN.png");
        case Tile.ROAD_NS:
            return Qt.resolvedUrl("assets/tiles/road_NS.png");
        case Tile.ROAD_E:
            return Qt.resolvedUrl("assets/tiles/road_E.png");
        case Tile.ROAD_W:
            return Qt.resolvedUrl("assets/tiles/road_W.png");
        case Tile.ROAD_N:
            return Qt.resolvedUrl("assets/tiles/road_N.png");
        case Tile.ROAD_S:
            return Qt.resolvedUrl("assets/tiles/road_S.png");
        case Tile.CLEARING_EN:
            return Qt.resolvedUrl("assets/tiles/clearing_EN.png");
        case Tile.CLEARING_ES:
            return Qt.resolvedUrl("assets/tiles/clearing_ES.png");
        case Tile.CLEARING_WS:
            return Qt.resolvedUrl("assets/tiles/clearing_WS.png");
        case Tile.CLEARING_WN:
            return Qt.resolvedUrl("assets/tiles/clearing_WN.png");
        case Tile.CLEARING_E:
            return Qt.resolvedUrl("assets/tiles/clearing_E.png");
        case Tile.CLEARING_W:
            return Qt.resolvedUrl("assets/tiles/clearing_W.png");
        case Tile.CLEARING_S:
            return Qt.resolvedUrl("assets/tiles/clearing_S.png");
        case Tile.CLEARING_N:
            return Qt.resolvedUrl("assets/tiles/clearing_N.png");
        case Tile.CLEARING:
            return Qt.resolvedUrl("assets/tiles/clearing.png");
        case Tile.CLEARING_E_ROAD_W:
            return Qt.resolvedUrl("assets/tiles/clearing_E_ROAD_W.png");
        case Tile.CLEARING_W_ROAD_E:
            return Qt.resolvedUrl("assets/tiles/clearing_W_ROAD_E.png");
        case Tile.CLEARING_S_ROAD_N:
            return Qt.resolvedUrl("assets/tiles/clearing_S_ROAD_N.png");
        case Tile.CLEARING_N_ROAD_S:
            return Qt.resolvedUrl("assets/tiles/clearing_N_ROAD_S.png");
        case Tile.STUMP_W:
            return Qt.resolvedUrl("assets/tiles/stump_W.png");
        case Tile.STUMP_E:
            return Qt.resolvedUrl("assets/tiles/stump_E.png");
        case Tile.STUMP_N:
            return Qt.resolvedUrl("assets/tiles/stump_N.png");
        case Tile.STUMP_S:
            return Qt.resolvedUrl("assets/tiles/stump_S.png");
        default:
            return "";
        }
    }
}
