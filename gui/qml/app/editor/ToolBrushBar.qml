pragma ComponentBehavior: Bound
import QtQuick

import app
import app.global
import app.models

Item {
    id: root

    readonly property string mode: selection.getMode()
    readonly property int currentTile: selection.getTile()
    readonly property int currentStatus: selection.getStatus()

    QtObject {
        id: selection

        property int primaryIndex: 0
        property int secondaryIndex: 0

        readonly property var primaryItems: [
            {
                "mode": "view",
                "label": "View"
            },
            {
                "mode": "puzzle",
                "label": "Puzzle"
            },
            {
                "mode": "tileStatus",
                "label": "Status",
                "secondaryItems": statusItems([Tile.UNEXPLORED, Tile.BLOOMING])
            },
            {
                "mode": "tile",
                "tile": Tile.GRASSLAND,
                "secondaryItems": tileItems([Tile.GRASSLAND, Tile.CLEARING])
            },
            {
                "mode": "tile",
                "tile": Tile.ROAD_E,
                "secondaryItems": tileItems([Tile.ROAD_E, Tile.ROAD_W, Tile.ROAD_N, Tile.ROAD_S])
            },
            {
                "mode": "tile",
                "tile": Tile.ROAD_WE,
                "secondaryItems": tileItems([Tile.ROAD_WE, Tile.ROAD_NS, Tile.ROAD_WS, Tile.ROAD_WN, Tile.ROAD_ES, Tile.ROAD_EN])
            },
            {
                "mode": "tile",
                "tile": Tile.CLEARING_EN,
                "secondaryItems": tileItems([Tile.CLEARING_EN, Tile.CLEARING_ES, Tile.CLEARING_WS, Tile.CLEARING_WN])
            },
            {
                "mode": "tile",
                "tile": Tile.CLEARING_E,
                "secondaryItems": tileItems([Tile.CLEARING_E, Tile.CLEARING_W, Tile.CLEARING_S, Tile.CLEARING_N])
            },
            {
                "mode": "tile",
                "tile": Tile.STUMP_E,
                "secondaryItems": tileItems([Tile.STUMP_W, Tile.STUMP_E, Tile.STUMP_N, Tile.STUMP_S])
            },
            {
                "mode": "tile",
                "tile": Tile.CLEARING_W_ROAD_E,
                "secondaryItems": tileItems([Tile.CLEARING_E_ROAD_W, Tile.CLEARING_W_ROAD_E, Tile.CLEARING_S_ROAD_N, Tile.CLEARING_N_ROAD_S])
            }
        ]

        property var primaryItem: primaryItems[primaryIndex]
        property var secondaryItems: primaryItem.secondaryItems

        function tileItems(tiles) {
            let items = [];
            for (let index = 0; index < tiles.length; index++) {
                items.push({
                    "tile": tiles[index]
                });
            }
            return items;
        }

        function statusItems(statuses) {
            let items = [];
            for (let index = 0; index < statuses.length; index++) {
                items.push({
                    "status": statuses[index]
                });
            }
            return items;
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
            let secondaryItems = getSecondaryItems();
            if (!!secondaryItems) {
                secondaryIndex = wrapIndex(index, secondaryItems.length);
            }
        }

        function getPrimaryItem() {
            return primaryItems[primaryIndex];
        }

        function getSecondaryItems() {
            return getPrimaryItem().secondaryItems;
        }

        function getActiveItem() {
            let primaryItem = getPrimaryItem();
            let secondaryItems = getSecondaryItems();
            return !!secondaryItems ? secondaryItems[secondaryIndex] : primaryItem;
        }

        function getMode() {
            let primaryItem = getPrimaryItem();
            return primaryItem.mode !== undefined ? primaryItem.mode : "view";
        }

        function getTile() {
            let activeItem = getActiveItem();
            return activeItem.tile !== undefined ? activeItem.tile : Tile.GRASSLAND;
        }

        function getStatus() {
            let activeItem = getActiveItem();
            return activeItem.status !== undefined ? activeItem.status : Tile.UNEXPLORED;
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

    function choosePrimary(index) {
        selection.setPrimaryIndex(index);
    }

    function chooseSecondary(index) {
        selection.setSecondaryIndex(index);
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
                    width: root.secondaryButtonSize
                    height: root.secondaryButtonSize
                    radius: root.buttonRadius
                    color: index === selection.secondaryIndex ? AppTheme.surfaceVariant : AppTheme.surface
                    border.color: index === selection.secondaryIndex ? AppTheme.primary : AppTheme.border

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
                            root.chooseSecondary(index);
                        }
                    }

                    HoverHandler {
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
                    root.chooseSecondary(selection.secondaryIndex + delta);
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
                    width: root.primaryButtonSize
                    height: root.primaryButtonSize
                    radius: root.buttonRadius
                    color: index === selection.primaryIndex ? AppTheme.surfaceVariant : AppTheme.surface
                    border.color: index === selection.primaryIndex ? AppTheme.primary : AppTheme.border

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
                            font.pixelSize: 14
                        }
                    }

                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        gesturePolicy: TapHandler.WithinBounds
                        grabPermissions: PointerHandler.CanTakeOverFromAnything
                        onTapped: {
                            root.choosePrimary(index);
                        }
                    }

                    HoverHandler {
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
                    root.choosePrimary(selection.primaryIndex + delta);
                    event.accepted = true;
                }
            }
        }
    }
}
