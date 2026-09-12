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
    readonly property string mode: toolBrushBar.mode
    readonly property int currentTile: toolBrushBar.currentTile
    readonly property int currentStatus: toolBrushBar.currentStatus

    function selectOrCreatePuzzle(row, col) {
        const message = root.workspace.selectOrCreatePuzzle(row, col);
        if (!!message) {
            Services.alert(message);
        }
    }

    function focusPuzzleInViewport(puzzleId) {
        const geometry = root.workspace.puzzles.geometryById(puzzleId);
        if (viewport.isWorldRectVisible(geometry.x, geometry.y, geometry.width, geometry.height))
            return;

        viewport.centerOnWorldRect(geometry.x, geometry.y, geometry.width, geometry.height);
    }

    function cameraState() {
        return viewport.cameraState();
    }

    function restoreCameraState(state) {
        viewport.restoreCameraState(state);
    }

    function applyBrush(row, col, button) {
        if (toolBrushBar.mode === ToolMode.tileStatus) {
            if (button === Qt.LeftButton)
                root.workspace.setTileStatus(row, col, toolBrushBar.currentStatus);
            else if (button === Qt.RightButton)
                root.workspace.resetTileStatus(row, col);
        } else if (toolBrushBar.mode === ToolMode.tile) {
            if (button === Qt.LeftButton)
                root.workspace.paintTile(row, col, toolBrushBar.currentTile);
            else if (button === Qt.RightButton)
                root.workspace.eraseTile(row, col);
        }
    }

    function makeGhostTile() {
        if (viewport.hoveredGrid === null)
            return null;

        if (toolBrushBar.mode === ToolMode.tile) {
            return {
                "row": viewport.hoveredGrid.row,
                "col": viewport.hoveredGrid.col,
                "tile": toolBrushBar.currentTile,
                "status": Tile.NORMAL
            };
        }

        if (toolBrushBar.mode === ToolMode.tileStatus) {
            return {
                "row": viewport.hoveredGrid.row,
                "col": viewport.hoveredGrid.col,
                "status": toolBrushBar.currentStatus
            };
        }

        return null;
    }

    function handleGridClick(row, col, button) {
        if (toolBrushBar.mode === ToolMode.puzzle) {
            if (button === Qt.LeftButton)
                root.selectOrCreatePuzzle(row, col);
            return;
        }

        root.applyBrush(row, col, button);
    }

    function handleGridStroke(row, col, button) {
        root.applyBrush(row, col, button);
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
            if (button === Qt.MiddleButton)
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
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
    }

    Connections {
        target: root.workspace.puzzleView

        function onRequestPuzzleFocus(puzzleId) {
            root.focusPuzzleInViewport(puzzleId);
        }
    }
}
