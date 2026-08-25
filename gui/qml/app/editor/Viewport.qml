import QtQuick

import app.models
import app.global
import app

Item {
    id: root
    implicitWidth: 300
    implicitHeight: 300

    property Workspace workspace
    clip: true

    signal pointerPressed(real screenX, real screenY, int button)
    signal pointerDragged(real screenX, real screenY, real dx, real dy, int button)
    signal pointerReleased(real screenX, real screenY, int button)
    signal wheelMoved(real screenX, real screenY, real angleDeltaY)

    signal gridPressed(int row, int col, int button)
    signal gridEntered(int row, int col, int button)
    signal gridReleased(int row, int col, int button)

    // Camera
    QtObject {
        id: camera

        property real worldX: 0
        property real worldY: 0
        property real zoom: 1
        readonly property real maxZoom: 2
        readonly property real minZoom: 0.2

        // screenX = (worldXOfPoint - cameraWorldX) * zoom
        // screenY = (worldYOfPoint - cameraWorldY) * zoom
    }

    function clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value));
    }

    function screenToWorld(screenX, screenY) {
        return {
            x: camera.worldX + screenX / camera.zoom,
            y: camera.worldY + screenY / camera.zoom
        };
    }

    function screenToGrid(screenX, screenY) {
        let worldPoint = screenToWorld(screenX, screenY);
        return {
            row: Math.floor(worldPoint.y / Assets.tileSize),
            col: Math.floor(worldPoint.x / Assets.tileSize)
        };
    }

    function panBy(screenDx, screenDy) {
        camera.worldX -= screenDx / camera.zoom;
        camera.worldY -= screenDy / camera.zoom;
    }

    function zoomAt(screenX, screenY, angleDeltaY) {
        if (angleDeltaY === 0)
            return;

        let worldPoint = screenToWorld(screenX, screenY);
        let factor = angleDeltaY > 0 ? 1.1 : 1 / 1.1;
        camera.zoom = clamp(camera.zoom * factor, camera.minZoom, camera.maxZoom);
        camera.worldX = worldPoint.x - screenX / camera.zoom;
        camera.worldY = worldPoint.y - screenY / camera.zoom;
    }

    Rectangle {
        anchors.fill: parent
        color: AppTheme.surface
    }

    Item {
        // The container maps world coordinates to screen coordinates, so its children can use world coordinates.
        id: worldContainer

        x: Math.round(-camera.worldX * camera.zoom) // worldXOfPoint = 0 => screenX = - cameraWorldX * zoom
        y: Math.round(-camera.worldY * camera.zoom) // worldXOfPoint = 0 => screenY = - cameraWorldY * zoom

        scale: camera.zoom
        transformOrigin: Item.TopLeft

        // Tiles

        // Puzzles

    }

    Item {
        id: gridOverlay
        anchors.fill: parent

        readonly property real tileScreenSize: Assets.tileSize * camera.zoom
        readonly property real startScreenX: Math.floor(camera.worldX / Assets.tileSize) * tileScreenSize - camera.worldX * camera.zoom
        readonly property real startScreenY: Math.floor(camera.worldY / Assets.tileSize) * tileScreenSize - camera.worldY * camera.zoom
        readonly property int verticalLineCount: Math.ceil(root.width / tileScreenSize) + 3
        readonly property int horizontalLineCount: Math.ceil(root.height / tileScreenSize) + 3
        readonly property real gridOpacity: Math.max(0.3, Math.min(0.9, 0.8 * camera.zoom))

        Repeater {
            model: gridOverlay.verticalLineCount

            delegate: Rectangle {
                x: Math.round(gridOverlay.startScreenX + index * gridOverlay.tileScreenSize)
                y: 0
                width: 2
                height: gridOverlay.height
                color: AppTheme.gridLine
                opacity: gridOverlay.gridOpacity
            }
        }

        Repeater {
            model: gridOverlay.horizontalLineCount

            delegate: Rectangle {
                x: 0
                y: Math.round(gridOverlay.startScreenY + index * gridOverlay.tileScreenSize)
                width: gridOverlay.width
                height: 2
                color: AppTheme.gridLine
                opacity: gridOverlay.gridOpacity
            }
        }
    }

    MouseArea {
        id: pointerArea
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        hoverEnabled: true

        property int activeButton: Qt.NoButton
        property real lastScreenX: 0
        property real lastScreenY: 0
        property int lastGridRow: 0
        property int lastGridCol: 0
        property bool hasLastGrid: false

        function updateLastGrid(screenX, screenY) {
            let grid = root.screenToGrid(screenX, screenY);
            lastGridRow = grid.row;
            lastGridCol = grid.col;
            hasLastGrid = true;
            return grid;
        }

        onPressed: function (mouse) {
            activeButton = mouse.button;
            lastScreenX = mouse.x;
            lastScreenY = mouse.y;

            let grid = updateLastGrid(mouse.x, mouse.y);
            root.pointerPressed(mouse.x, mouse.y, mouse.button);
            root.gridPressed(grid.row, grid.col, mouse.button);
        }

        onPositionChanged: function (mouse) {
            if (activeButton === Qt.NoButton)
                return;

            let dx = mouse.x - lastScreenX;
            let dy = mouse.y - lastScreenY;
            lastScreenX = mouse.x;
            lastScreenY = mouse.y;
            root.pointerDragged(mouse.x, mouse.y, dx, dy, activeButton);

            let grid = root.screenToGrid(mouse.x, mouse.y);
            if (!hasLastGrid || grid.row !== lastGridRow || grid.col !== lastGridCol) {
                lastGridRow = grid.row;
                lastGridCol = grid.col;
                hasLastGrid = true;
                root.gridEntered(grid.row, grid.col, activeButton);
            }
        }

        onReleased: function (mouse) {
            let grid = root.screenToGrid(mouse.x, mouse.y);
            root.pointerReleased(mouse.x, mouse.y, mouse.button);
            root.gridReleased(grid.row, grid.col, mouse.button);
            activeButton = Qt.NoButton;
            hasLastGrid = false;
        }

        onCanceled: {
            activeButton = Qt.NoButton;
            hasLastGrid = false;
        }

        onWheel: function (wheel) {
            root.wheelMoved(wheel.x, wheel.y, wheel.angleDelta.y);
            wheel.accepted = true;
        }
    }
}
