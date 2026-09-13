pragma ComponentBehavior: Bound
import QtQuick

import app
import app.global
import app.models

Item {
    id: root

    readonly property string mode: selection.primaryItem?.mode ?? ToolMode.inspect
    readonly property int currentTile: selection.activeItem?.tile ?? Tile.GRASSLAND
    readonly property int currentStatus: selection.activeItem?.status ?? Tile.UNEXPLORED

    QtObject {
        id: selection

        property int primaryIndex: 0
        property int secondaryIndex: 0

        readonly property var primaryItems: [
            {
                "mode": ToolMode.inspect,
                "label": qsTr("Inspect")
            },
            {
                "mode": ToolMode.puzzle,
                "label": qsTr("Puzzle")
            },
            {
                "mode": ToolMode.tileStatus,
                "status": Tile.UNEXPLORED,
                "secondaryItems": items("status", [Tile.UNEXPLORED, Tile.BLOOMING])
            },
            {
                "mode": ToolMode.tile,
                "tile": Tile.GRASSLAND,
                "secondaryItems": items("tile", [Tile.GRASSLAND, Tile.CLEARING])
            },
            {
                "mode": ToolMode.tile,
                "tile": Tile.ROAD_E,
                "secondaryItems": items("tile", [Tile.ROAD_E, Tile.ROAD_S, Tile.ROAD_W, Tile.ROAD_N])
            },
            {
                "mode": ToolMode.tile,
                "tile": Tile.ROAD_WE,
                "secondaryItems": items("tile", [Tile.ROAD_WE, Tile.ROAD_NS, Tile.ROAD_ES, Tile.ROAD_WS, Tile.ROAD_WN, Tile.ROAD_EN])
            },
            {
                "mode": ToolMode.tile,
                "tile": Tile.CLEARING_EN,
                "secondaryItems": items("tile", [Tile.CLEARING_ES, Tile.CLEARING_WS, Tile.CLEARING_WN, Tile.CLEARING_EN])
            },
            {
                "mode": ToolMode.tile,
                "tile": Tile.CLEARING_E,
                "secondaryItems": items("tile", [Tile.CLEARING_E, Tile.CLEARING_S, Tile.CLEARING_W, Tile.CLEARING_N])
            },
            {
                "mode": ToolMode.tile,
                "tile": Tile.CLEARING_W_ROAD_E,
                "secondaryItems": items("tile", [Tile.CLEARING_W_ROAD_E, Tile.CLEARING_N_ROAD_S, Tile.CLEARING_E_ROAD_W, Tile.CLEARING_S_ROAD_N])
            },
            {
                "mode": ToolMode.tile,
                "tile": Tile.STUMP_E,
                "secondaryItems": items("tile", [Tile.STUMP_E, Tile.STUMP_S, Tile.STUMP_W, Tile.STUMP_N])
            },
        ]

        readonly property var primaryItem: primaryItems[primaryIndex]
        readonly property var secondaryItems: primaryItem?.secondaryItems ?? null
        readonly property var activeItem: secondaryItems ? secondaryItems[secondaryIndex] : primaryItem

        function items(role, values) {
            return values.map(value => {
                let item = {};
                item[role] = value;
                return item;
            });
        }

        function wrapIndex(index, count) {
            if (count <= 0)
                return 0;
            return (index % count + count) % count;
        }

        function setPrimaryIndex(index) {
            let oldPrimaryIndex = primaryIndex;
            primaryIndex = wrapIndex(index, primaryItems.length);

            if (primaryIndex !== oldPrimaryIndex) {
                setSecondaryIndex(0);
            }
        }

        function setSecondaryIndex(index) {
            if (!!secondaryItems) {
                secondaryIndex = wrapIndex(index, secondaryItems.length);
            }
        }
    }

    readonly property int primaryButtonSize: 48
    readonly property int secondaryButtonSize: 42
    readonly property int buttonRadius: 6
    readonly property int itemSpacing: 6
    readonly property int rowSpacing: 6
    readonly property int primaryIconSize: 36
    readonly property int secondaryIconSize: 32

    implicitWidth: Math.max(primaryRow.implicitWidth, secondaryRow.implicitWidth)
    implicitHeight: secondaryButtonSize + rowSpacing + primaryButtonSize

    function iconSource(item) {
        if (item && item.tile !== undefined) {
            return Assets.tileImage(item.tile);
        }
        if (item && item.status !== undefined) {
            return Assets.tileStatusImage(item.status);
        }
        if (item && item.icon !== undefined) {
            return item.icon;
        }
        return "";
    }

    Item {
        anchors.fill: parent

        Row {
            id: secondaryRow
            anchors.horizontalCenter: parent.horizontalCenter
            y: 0
            visible: !!selection.secondaryItems
            spacing: root.itemSpacing

            Repeater {
                model: selection.secondaryItems

                delegate: Rectangle {
                    id: tileButton
                    required property int index
                    required property var modelData
                    readonly property bool isSelected: index === selection.secondaryIndex
                    width: root.secondaryButtonSize
                    height: root.secondaryButtonSize
                    radius: root.buttonRadius
                    color: AppTheme.surface
                    border.width: isSelected ? 2 : 1
                    border.color: isSelected ? AppTheme.selectionBorder : AppTheme.border

                    Rectangle {
                        anchors.fill: parent
                        radius: parent.radius
                        color: tileButton.isSelected ? AppTheme.selectionOverlay : (secondaryHover.hovered ? AppTheme.hoverOverlay : "transparent")
                    }

                    Loader {
                        anchors.centerIn: parent
                        sourceComponent: root.iconSource(modelData) !== "" ? secondaryIconComponent : (modelData.label !== undefined ? secondaryLabelComponent : null)
                    }

                    Component {
                        id: secondaryIconComponent

                        Image {
                            width: root.secondaryIconSize
                            height: root.secondaryIconSize
                            source: root.iconSource(modelData)
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Component {
                        id: secondaryLabelComponent

                        Text {
                            text: modelData.label
                            color: AppTheme.textPrimary
                            font.bold: true
                            font.pixelSize: 10
                        }
                    }

                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        gesturePolicy: TapHandler.WithinBounds
                        grabPermissions: PointerHandler.CanTakeOverFromAnything
                        onTapped: {
                            selection.setSecondaryIndex(index);
                        }
                    }

                    HoverHandler {
                        id: secondaryHover
                        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                        blocking: true
                    }
                }
            }

            WheelHandler {
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                blocking: true

                onWheel: function (event) {
                    let delta = event.angleDelta.y > 0 ? -1 : 1;
                    selection.setSecondaryIndex(selection.secondaryIndex + delta);
                    event.accepted = true;
                }
            }
        }

        Row {
            id: primaryRow
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.secondaryButtonSize + root.rowSpacing
            spacing: root.itemSpacing

            Repeater {
                model: selection.primaryItems

                delegate: Rectangle {
                    id: primaryButton
                    required property int index
                    required property var modelData
                    readonly property bool isSelected: index === selection.primaryIndex
                    width: root.primaryButtonSize
                    height: root.primaryButtonSize
                    radius: root.buttonRadius
                    color: AppTheme.surface
                    border.width: isSelected ? 2 : 1
                    border.color: isSelected ? AppTheme.selectionBorder : AppTheme.border

                    Rectangle {
                        anchors.fill: parent
                        radius: parent.radius
                        color: primaryButton.isSelected ? AppTheme.selectionOverlay : (primaryHover.hovered ? AppTheme.hoverOverlay : "transparent")
                    }

                    Loader {
                        anchors.centerIn: parent
                        sourceComponent: root.iconSource(modelData) !== "" ? primaryIconComponent : (modelData.label !== undefined ? primaryLabelComponent : null)
                    }

                    Component {
                        id: primaryIconComponent

                        Image {
                            width: root.primaryIconSize
                            height: root.primaryIconSize
                            source: root.iconSource(modelData)
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Component {
                        id: primaryLabelComponent

                        Text {
                            text: modelData.label
                            color: AppTheme.textPrimary
                            font.bold: true
                            font.pixelSize: 12
                        }
                    }

                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        gesturePolicy: TapHandler.WithinBounds
                        grabPermissions: PointerHandler.CanTakeOverFromAnything
                        onTapped: {
                            selection.setPrimaryIndex(index);
                        }
                    }

                    HoverHandler {
                        id: primaryHover
                        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                        blocking: true
                    }
                }
            }

            WheelHandler {
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                blocking: true

                onWheel: function (event) {
                    let delta = event.angleDelta.y > 0 ? -1 : 1;
                    selection.setPrimaryIndex(selection.primaryIndex + delta);
                    event.accepted = true;
                }
            }
        }
    }
}
