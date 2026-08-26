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

    signal pointerClicked(real screenX, real screenY, int button)
    signal pointerDragStarted(real screenX, real screenY, int button)
    signal pointerDragged(real screenX, real screenY, real dx, real dy, int button)
    signal pointerDragEnded(real screenX, real screenY, int button)
    signal wheelMoved(real screenX, real screenY, real angleDeltaY)

    signal gridClicked(int row, int col, int button)
    signal gridStrokeStarted(int row, int col, int button)
    signal gridStrokeEntered(int row, int col, int button)
    signal gridStrokeEnded(int row, int col, int button)

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
        // Let the same world point at the same screen position
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

    QtObject {
        id: dragState

        property int lastGridRow: 0
        property int lastGridCol: 0
        property bool hasLastGrid: false

        function reset(handler) {
            handler.lastTranslationX = 0;
            handler.lastTranslationY = 0;
            hasLastGrid = false;
        }

        function start(handler) {
            let button = handler.activeButton;
            if (button === Qt.NoButton)
                return;

            let pressPoint = handler.centroid.pressPosition;
            let grid = root.screenToGrid(pressPoint.x, pressPoint.y);
            lastGridRow = grid.row;
            lastGridCol = grid.col;
            hasLastGrid = true;

            root.pointerDragStarted(handler.centroid.position.x, handler.centroid.position.y, button);
            root.gridStrokeStarted(grid.row, grid.col, button);
        }

        function move(handler) {
            let button = handler.activeButton;
            if (!handler.active || button === Qt.NoButton)
                return;

            let dx = handler.translation.x - handler.lastTranslationX;
            let dy = handler.translation.y - handler.lastTranslationY;
            handler.lastTranslationX = handler.translation.x;
            handler.lastTranslationY = handler.translation.y;

            let point = handler.centroid.position;
            root.pointerDragged(point.x, point.y, dx, dy, button);

            let grid = root.screenToGrid(point.x, point.y);
            if (!hasLastGrid || grid.row !== lastGridRow || grid.col !== lastGridCol) {
                lastGridRow = grid.row;
                lastGridCol = grid.col;
                hasLastGrid = true;
                root.gridStrokeEntered(grid.row, grid.col, button);
            }
        }

        function finish(handler) {
            let button = handler.activeButton;
            if (button === Qt.NoButton) {
                reset(handler);
                return;
            }

            let point = handler.centroid.position;
            let grid = root.screenToGrid(point.x, point.y);
            root.pointerDragEnded(point.x, point.y, button);
            root.gridStrokeEnded(grid.row, grid.col, button);
            reset(handler);
        }
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

        onTapped: function (eventPoint, button) {
            let point = eventPoint.position;
            let grid = root.screenToGrid(point.x, point.y);
            root.pointerClicked(point.x, point.y, button);
            root.gridClicked(grid.row, grid.col, button);
        }
    }

    WheelHandler {
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad

        onWheel: function (event) {
            root.wheelMoved(event.x, event.y, event.angleDelta.y);
            event.accepted = true;
        }
    }

    DragHandler {
        id: dragHandler
        target: null
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

        property int activeButton: Qt.NoButton
        property real lastTranslationX: 0
        property real lastTranslationY: 0

        function firstPressedButton(buttons) {
            if (buttons & Qt.LeftButton)
                return Qt.LeftButton;
            if (buttons & Qt.RightButton)
                return Qt.RightButton;
            if (buttons & Qt.MiddleButton)
                return Qt.MiddleButton;
            return Qt.NoButton;
        }

        onTranslationChanged: function () {
            dragState.move(dragHandler);
        }

        onActiveChanged: {
            if (dragHandler.active) {
                dragHandler.activeButton = dragHandler.firstPressedButton(dragHandler.centroid.pressedButtons);
                dragState.reset(dragHandler);
                dragState.start(dragHandler);
            } else {
                dragState.finish(dragHandler);
                dragHandler.activeButton = Qt.NoButton;
            }
        }
    }
}
