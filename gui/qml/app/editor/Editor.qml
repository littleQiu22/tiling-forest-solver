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

    function paintTile(row, col) {
        root.workspace.paintTile(row, col, toolBrushBar.currentTile);
    }

    function eraseTile(row, col) {
        root.workspace.eraseTile(row, col);
    }

    function setTileStatus(row, col) {
        root.workspace.setTileStatus(row, col, toolBrushBar.currentStatus);
    }

    function resetTileStatus(row, col) {
        root.workspace.resetTileStatus(row, col);
    }

    function selectOrCreatePuzzle(row, col) {
        const message = root.workspace.selectOrCreatePuzzle(row, col);
        if (!!message) {
            Services.alert(message);
        }
    }

    function deletePuzzle(row, col) {
        root.workspace.deletePuzzleAt(row, col);
    }

    function makeGhostTile() {
        if (viewport.hoveredGrid === null)
            return null;

        if (toolBrushBar.mode === "tile") {
            return {
                "row": viewport.hoveredGrid.row,
                "col": viewport.hoveredGrid.col,
                "tile": toolBrushBar.currentTile,
                "status": Tile.NORMAL
            };
        }

        if (toolBrushBar.mode === "tileStatus") {
            return {
                "row": viewport.hoveredGrid.row,
                "col": viewport.hoveredGrid.col,
                "status": toolBrushBar.currentStatus
            };
        }

        return null;
    }

    function handleGridClick(row, col, button) {
        if (toolBrushBar.mode === "puzzle") {
            if (button === Qt.LeftButton) {
                root.selectOrCreatePuzzle(row, col);
            } else if (button === Qt.RightButton) {
                root.deletePuzzle(row, col);
            }
            return;
        }

        if (toolBrushBar.mode === "tileStatus") {
            if (button === Qt.LeftButton) {
                root.setTileStatus(row, col);
            } else if (button === Qt.RightButton) {
                root.resetTileStatus(row, col);
            }
            return;
        }

        if (toolBrushBar.mode === "tile") {
            if (button === Qt.LeftButton) {
                root.paintTile(row, col);
            } else if (button === Qt.RightButton) {
                root.eraseTile(row, col);
            }
            return;
        }
    }

    function handleGridStroke(row, col, button) {
        if (toolBrushBar.mode === "tileStatus") {
            if (button === Qt.LeftButton) {
                root.setTileStatus(row, col);
            } else if (button === Qt.RightButton) {
                root.resetTileStatus(row, col);
            }
            return;
        }

        if (toolBrushBar.mode !== "tile")
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
        ghostTile: root.makeGhostTile()

        onWheelMoved: function (screenX, screenY, angleDeltaY) {
            viewport.zoomAt(screenX, screenY, angleDeltaY);
        }

        onPointerDragged: function (screenX, screenY, dx, dy, button) {
            if (button === Qt.MiddleButton || (toolBrushBar.mode === "view" && button === Qt.LeftButton))
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
    }
}
