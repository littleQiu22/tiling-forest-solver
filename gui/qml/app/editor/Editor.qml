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
    property int currentTile: Tile.GRASSLAND

    function paintTile(row, col) {
        root.workspace.paintTile(row, col, root.currentTile);
    }

    function eraseTile(row, col) {
        root.workspace.eraseTile(row, col);
    }

    function selectOrCreatePuzzle(row, col) {
        root.workspace.selectOrCreatePuzzle(row, col);
    }

    function deletePuzzle(row, col) {
        root.workspace.deletePuzzle(row, col);
    }

    function handleGridClick(row, col, button) {
        if (root.toolMode === "puzzle") {
            if (button === Qt.LeftButton) {
                root.selectOrCreatePuzzle(row, col);
            } else if (button === Qt.RightButton) {
                root.deletePuzzle(row, col);
            }
            return;
        }

        if (root.toolMode === "tile") {
            if (button === Qt.LeftButton) {
                root.paintTile(row, col);
            } else if (button === Qt.RightButton) {
                root.eraseTile(row, col);
            }
            return;
        }
    }

    function handleGridStroke(row, col, button) {
        if (root.toolMode !== "tile")
            return;

        if (button === Qt.LeftButton) {
            root.paintTile(row, col);
        } else if (button === Qt.RightButton) {
            root.eraseTile(row, col);
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

        onGridClicked: function (row, col, button) {
            root.handleGridClick(row, col, button);
        }

        onGridStrokeStarted: function (row, col, button) {
            root.handleGridStroke(row, col, button);
        }

        onGridStrokeEntered: function (row, col, button) {
            root.handleGridStroke(row, col, button);
        }
    }

    ToolBrushBar {
        id: toolBrushBar
        z: 10
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24

        onToolModeRequested: function (mode) {
            root.toolMode = mode;
        }

        onTileRequested: function (tile) {
            root.currentTile = tile;
        }
    }
}
