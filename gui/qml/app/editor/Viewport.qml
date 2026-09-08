pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Shapes

import app.models
import app.global
import app

Item {
    id: root
    implicitWidth: 300
    implicitHeight: 300

    property Workspace workspace
    property var ghostTile: null
    readonly property var hoveredGrid: hoverState.grid
    clip: true

    signal pointerDragged(real screenX, real screenY, real dx, real dy, int button)
    signal wheelMoved(real screenX, real screenY, real angleDeltaY)

    signal gridClicked(int row, int col, int button)
    signal gridStrokeStarted(int row, int col, int button)
    signal gridStrokeEntered(int row, int col, int button)

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

    function isWorldRectVisible(worldX, worldY, worldWidth, worldHeight) {
        if (worldWidth <= 0 || worldHeight <= 0)
            return true;

        let screenLeft = (worldX - camera.worldX) * camera.zoom;
        let screenTop = (worldY - camera.worldY) * camera.zoom;
        let screenRight = screenLeft + worldWidth * camera.zoom;
        let screenBottom = screenTop + worldHeight * camera.zoom;

        return screenRight > 0
            && screenBottom > 0
            && screenLeft < root.width
            && screenTop < root.height;
    }

    function centerOnWorldRect(worldX, worldY, worldWidth, worldHeight) {
        if (worldWidth <= 0 || worldHeight <= 0)
            return;

        camera.worldX = worldX + worldWidth / 2 - root.width / (2 * camera.zoom);
        camera.worldY = worldY + worldHeight / 2 - root.height / (2 * camera.zoom);
    }

    function cameraState() {
        return {
            "worldX": camera.worldX,
            "worldY": camera.worldY,
            "zoom": camera.zoom
        };
    }

    function restoreCameraState(state) {
        camera.worldX = state?.worldX ?? 0;
        camera.worldY = state?.worldY ?? 0;
        camera.zoom = clamp(state?.zoom ?? 1, camera.minZoom, camera.maxZoom);
    }

    function puzzleStrokeColor(solveStatus) {
        switch (solveStatus) {
        case "Solved":
            return AppTheme.success;
        case "TimeLimit":
        case "SolutionLimit":
            return AppTheme.warning;
        case "Unsolved":
            return AppTheme.primary;
        case "Solving":
            return AppTheme.active;
        default:
            return AppTheme.danger;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: AppTheme.surface
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
                required property int index

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
                required property int index

                x: 0
                y: Math.round(gridOverlay.startScreenY + index * gridOverlay.tileScreenSize)
                width: gridOverlay.width
                height: 2
                color: AppTheme.gridLine
                opacity: gridOverlay.gridOpacity
            }
        }
    }

    Item {
        // The container maps world coordinates to screen coordinates, so its children can use world coordinates.
        id: worldContainer

        x: Math.round(-camera.worldX * camera.zoom) // worldXOfPoint = 0 => screenX = - cameraWorldX * zoom
        y: Math.round(-camera.worldY * camera.zoom) // worldXOfPoint = 0 => screenY = - cameraWorldY * zoom

        scale: camera.zoom
        transformOrigin: Item.TopLeft

        // Puzzle fill overlays
        Repeater {
            model: root.workspace ? root.workspace.puzzles : null

            delegate: Item {
                id: puzzleFillDelegate

                required property var svgPaths
                required property real svgX
                required property real svgY
                required property real svgWidth
                required property real svgHeight
                required property bool isSelected

                z: 10
                x: svgX
                y: svgY
                width: svgWidth
                height: svgHeight

                Repeater {
                    model: puzzleFillDelegate.svgPaths

                    delegate: Shape {
                        id: puzzleFillShape

                        required property string modelData

                        z: 0
                        anchors.fill: parent
                        containsMode: Shape.FillContains

                        ShapePath {
                            fillColor: puzzleFillDelegate.isSelected ? AppTheme.strongSelectionOverlay : "transparent"
                            strokeColor: "transparent"
                            strokeWidth: 0

                            PathSvg {
                                path: puzzleFillShape.modelData
                            }
                        }
                    }
                }
            }
        }

        // Puzzle solution tiles
        Repeater {
            model: root.workspace ? root.workspace.puzzles : null

            delegate: Item {
                id: puzzleSolutionDelegate

                required property real svgX
                required property real svgY
                required property real svgWidth
                required property real svgHeight
                required property var currentSolution

                z: 20
                x: svgX
                y: svgY
                width: svgWidth
                height: svgHeight

                Repeater {
                    model: puzzleSolutionDelegate.currentSolution

                    delegate: Image {
                        required property var modelData

                        x: modelData.col * Assets.tileSize - puzzleSolutionDelegate.svgX
                        y: modelData.row * Assets.tileSize - puzzleSolutionDelegate.svgY
                        width: Assets.tileSize
                        height: Assets.tileSize
                        source: Assets.tileImage(modelData.tile)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        opacity: 0.82
                    }
                }
            }
        }

        // Tiles
        Repeater {
            model: root.workspace ? root.workspace.tiles : null

            delegate: Item {
                required property int row
                required property int col
                required property int tile
                required property int status

                z: 30
                x: col * Assets.tileSize
                y: row * Assets.tileSize
                width: Assets.tileSize
                height: Assets.tileSize

                Image {
                    anchors.fill: parent
                    source: Assets.tileImage(parent.tile)
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                Image {
                    width: parent.width * 0.52
                    height: parent.height * 0.52
                    anchors.centerIn: parent
                    source: Assets.tileStatusImage(parent.status)
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    visible: source !== ""
                    opacity: 0.92
                }
            }
        }

        // Puzzle outlines and labels
        Repeater {
            model: root.workspace ? root.workspace.puzzles : null

            delegate: Item {
                id: puzzleOutlineDelegate

                required property var svgPaths
                required property real svgX
                required property real svgY
                required property real svgWidth
                required property real svgHeight
                required property string solveStatus
                required property bool isSelected
                required property bool isGeometryStaled

                z: 40
                x: svgX
                y: svgY
                width: svgWidth
                height: svgHeight

                Repeater {
                    model: puzzleOutlineDelegate.svgPaths

                    delegate: Shape {
                        id: puzzleHaloShape

                        required property string modelData

                        z: 0
                        anchors.fill: parent
                        containsMode: Shape.FillContains

                        ShapePath {
                            fillColor: "transparent"
                            strokeColor: puzzleOutlineDelegate.isSelected ? AppTheme.selectionHalo : "transparent"
                            strokeWidth: puzzleOutlineDelegate.isSelected ? 11 / camera.zoom : 0
                            capStyle: ShapePath.RoundCap
                            joinStyle: ShapePath.RoundJoin

                            PathSvg {
                                path: puzzleHaloShape.modelData
                            }
                        }
                    }
                }

                Repeater {
                    model: puzzleOutlineDelegate.svgPaths

                    delegate: Shape {
                        id: puzzleStatusShape

                        required property string modelData

                        z: 1
                        anchors.fill: parent
                        containsMode: Shape.FillContains

                        ShapePath {
                            fillColor: "transparent"
                            strokeColor: root.puzzleStrokeColor(puzzleOutlineDelegate.solveStatus)
                            strokeWidth: 5 / camera.zoom
                            capStyle: ShapePath.RoundCap
                            joinStyle: ShapePath.RoundJoin
                            strokeStyle: puzzleOutlineDelegate.solveStatus === "Solving" ? ShapePath.DashLine : ShapePath.SolidLine
                            dashPattern: puzzleOutlineDelegate.solveStatus === "Solving" ? [6, 4] : []
                            dashOffset: 0

                            NumberAnimation on dashOffset {
                                from: 0
                                to: 10
                                duration: 900
                                loops: Animation.Infinite
                                running: puzzleOutlineDelegate.solveStatus === "Solving"
                            }

                            PathSvg {
                                path: puzzleStatusShape.modelData
                            }
                        }
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    visible: puzzleOutlineDelegate.isGeometryStaled
                    z: 10
                    width: staleText.implicitWidth + 14
                    height: staleText.implicitHeight + 6
                    radius: 4
                    scale: 1 / camera.zoom
                    color: AppTheme.surface
                    border.color: AppTheme.warning

                    Text {
                        id: staleText
                        anchors.centerIn: parent
                        text: qsTr("Stale")
                        color: AppTheme.warning
                        font.bold: true
                        font.pixelSize: 12
                    }
                }
            }
        }

        // Ghost tile
        Item {
            visible: root.ghostTile !== null
            z: 50
            x: visible ? root.ghostTile.col * Assets.tileSize : 0
            y: visible ? root.ghostTile.row * Assets.tileSize : 0
            width: Assets.tileSize
            height: Assets.tileSize
            opacity: 0.58

            Image {
                anchors.fill: parent
                source: root.ghostTile && root.ghostTile.tile !== undefined ? Assets.tileImage(root.ghostTile.tile) : ""
                fillMode: Image.PreserveAspectFit
                smooth: true
                visible: source !== ""
            }

            Image {
                width: parent.width * 0.52
                height: parent.height * 0.52
                anchors.centerIn: parent
                source: root.ghostTile && root.ghostTile.status !== undefined ? Assets.tileStatusImage(root.ghostTile.status) : ""
                fillMode: Image.PreserveAspectFit
                smooth: true
                visible: source !== ""
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

            reset(handler);
        }
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

        onTapped: function (eventPoint, button) {
            let point = eventPoint.position;
            let grid = root.screenToGrid(point.x, point.y);
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

    HoverHandler {
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad

        onPointChanged: {
            let grid = root.screenToGrid(point.position.x, point.position.y);
            hoverState.setGrid(grid.row, grid.col);
        }

        onHoveredChanged: {
            if (!hovered)
                hoverState.grid = null;
        }
    }

    QtObject {
        id: hoverState

        property var grid: null

        function setGrid(row, col) {
            if (grid !== null && grid.row === row && grid.col === col)
                return;

            grid = {
                "row": row,
                "col": col
            };
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
