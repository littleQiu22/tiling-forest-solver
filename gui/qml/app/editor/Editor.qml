import QtQuick

import app.global
import app.models

Rectangle {
    id: root
    implicitWidth: 300
    implicitHeight: 300
    color: "transparent"
    border.color: AppTheme.border

    required property Workspace workspace
    property string toolMode: "view"
    property string currentTileGroup: "road"
    property int currentTile: Tile.ROAD_WS

    signal paintTileRequested(int row, int col, int tile)
    signal eraseTileRequested(int row, int col)
    signal selectOrCreatePuzzleRequested(int row, int col)
    signal deletePuzzleRequested(int row, int col)

    function callWorkspace(method, args) {
        if (!root.workspace)
            return false;

        let fn = root.workspace[method];
        if (typeof fn !== "function")
            return false;

        fn.apply(root.workspace, args);
        return true;
    }

    function paintTile(row, col) {
        root.paintTileRequested(row, col, root.currentTile);
        root.callWorkspace("paintTile", [row, col, root.currentTile]);
    }

    function eraseTile(row, col) {
        root.eraseTileRequested(row, col);
        root.callWorkspace("eraseTile", [row, col]);
    }

    function selectOrCreatePuzzle(row, col) {
        root.selectOrCreatePuzzleRequested(row, col);
        root.callWorkspace("selectOrCreatePuzzle", [row, col]);
    }

    function deletePuzzle(row, col) {
        root.deletePuzzleRequested(row, col);
        root.callWorkspace("deletePuzzle", [row, col]);
    }

    function routeGridAction(row, col, button, isDrag) {
        if (root.toolMode === "tile") {
            if (button === Qt.LeftButton) {
                root.paintTile(row, col);
            } else if (button === Qt.RightButton) {
                root.eraseTile(row, col);
            }
            return;
        }

        if (isDrag)
            return;

        if (root.toolMode === "puzzle") {
            if (button === Qt.LeftButton) {
                root.selectOrCreatePuzzle(row, col);
            } else if (button === Qt.RightButton) {
                root.deletePuzzle(row, col);
            }
        }
    }

    Viewport {
        id: viewport
        anchors.fill: parent
        anchors.margins: root.border.width
        workspace: root.workspace

        onWheelMoved: function (screenX, screenY, angleDeltaY) {
            viewport.zoomAt(screenX, screenY, angleDeltaY);
        }

        onPointerDragged: function (screenX, screenY, dx, dy, button) {
            if (button === Qt.MiddleButton || (root.toolMode === "view" && button === Qt.LeftButton))
                viewport.panBy(dx, dy);
        }

        onGridPressed: function (row, col, button) {
            root.routeGridAction(row, col, button, false);
        }

        onGridEntered: function (row, col, button) {
            root.routeGridAction(row, col, button, true);
        }
    }

    ToolBrushBar {
        id: toolBrushBar
        z: 10
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24

        toolMode: root.toolMode
        currentGroup: root.currentTileGroup
        currentTile: root.currentTile

        onToolModeRequested: function (mode) {
            root.toolMode = mode;
        }

        onTileGroupRequested: function (group) {
            root.currentTileGroup = group;
        }

        onTileRequested: function (tile) {
            root.currentTile = tile;
            root.toolMode = "tile";
        }
    }
}
