import QtQuick

import app
import app.global
import app.models

Item {
    id: root

    property string toolMode: "view"
    property string currentGroup: "road"
    property int currentTile: Tile.ROAD_WS

    signal toolModeRequested(string mode)
    signal tileRequested(int tile)
    signal tileGroupRequested(string group)

    readonly property int primaryButtonSize: 48
    readonly property int secondaryButtonSize: 42
    readonly property int buttonRadius: 6
    readonly property int itemSpacing: 6
    readonly property int rowSpacing: 6
    readonly property int primaryIconSize: 36
    readonly property int secondaryIconSize: 32

    implicitWidth: Math.max(primaryRow.implicitWidth, secondaryRow.implicitWidth)
    implicitHeight: secondaryButtonSize + rowSpacing + primaryButtonSize

    readonly property var primaryItems: [
        { "kind": "mode", "mode": "view", "label": "V" },
        { "kind": "mode", "mode": "puzzle", "label": "P" },
        { "kind": "tileGroup", "group": "road", "tile": Tile.ROAD_WS },
        { "kind": "tileGroup", "group": "clearing", "tile": Tile.CLEARING },
        { "kind": "tileGroup", "group": "stump", "tile": Tile.STUMP_N },
        { "kind": "tileGroup", "group": "mixed", "tile": Tile.CLEARING_E_ROAD_W }
    ]
    property int hoveredPrimaryIndex: -1
    property bool secondaryHovered: false
    readonly property bool secondaryVisible: toolMode === "tile"
                                             || secondaryHovered
                                             || (hoveredPrimaryIndex >= 0
                                                 && primaryItems[hoveredPrimaryIndex].kind === "tileGroup")

    function groupTiles(group) {
        switch (group) {
        case "road":
            return [
                Tile.GRASSLAND,
                Tile.ROAD_WS, Tile.ROAD_WE, Tile.ROAD_WN, Tile.ROAD_ES, Tile.ROAD_EN,
                Tile.ROAD_NS, Tile.ROAD_E, Tile.ROAD_W, Tile.ROAD_N, Tile.ROAD_S
            ];
        case "clearing":
            return [
                Tile.CLEARING, Tile.CLEARING_EN, Tile.CLEARING_ES, Tile.CLEARING_WS,
                Tile.CLEARING_WN, Tile.CLEARING_E, Tile.CLEARING_W, Tile.CLEARING_S, Tile.CLEARING_N
            ];
        case "stump":
            return [Tile.STUMP_W, Tile.STUMP_E, Tile.STUMP_N, Tile.STUMP_S];
        case "mixed":
            return [
                Tile.CLEARING_E_ROAD_W, Tile.CLEARING_W_ROAD_E,
                Tile.CLEARING_S_ROAD_N, Tile.CLEARING_N_ROAD_S
            ];
        default:
            return [];
        }
    }

    function currentPrimaryIndex() {
        if (toolMode === "view")
            return 0;
        if (toolMode === "puzzle")
            return 1;

        for (let index = 0; index < primaryItems.length; index++) {
            let item = primaryItems[index];
            if (item.kind === "tileGroup" && item.group === currentGroup)
                return index;
        }
        return 0;
    }

    function choosePrimary(item) {
        if (item.kind === "mode") {
            root.toolModeRequested(item.mode);
            return;
        }

        let tiles = groupTiles(item.group);
        root.tileGroupRequested(item.group);
        if (tiles.indexOf(currentTile) === -1)
            root.tileRequested(tiles[0]);
        else
            root.toolModeRequested("tile");
    }

    function selectPrimaryOffset(delta) {
        let index = currentPrimaryIndex();
        let nextIndex = (index + delta + primaryItems.length) % primaryItems.length;
        choosePrimary(primaryItems[nextIndex]);
    }

    function selectTileOffset(delta) {
        let tiles = groupTiles(currentGroup);
        if (tiles.length === 0)
            return;

        let index = tiles.indexOf(currentTile);
        if (index === -1)
            index = 0;
        else
            index = (index + delta + tiles.length) % tiles.length;
        root.tileRequested(tiles[index]);
    }

    Item {
        anchors.fill: parent

        Row {
            id: secondaryRow
            anchors.horizontalCenter: parent.horizontalCenter
            y: 0
            visible: root.secondaryVisible
            spacing: root.itemSpacing

            Repeater {
                model: root.groupTiles(root.currentGroup)

                delegate: Rectangle {
                    id: tileButton
                    width: root.secondaryButtonSize
                    height: root.secondaryButtonSize
                    radius: root.buttonRadius
                    color: modelData === root.currentTile ? AppTheme.surfaceVariant : AppTheme.surface
                    border.color: modelData === root.currentTile ? AppTheme.primary : AppTheme.border

                    Image {
                        anchors.centerIn: parent
                        width: root.secondaryIconSize
                        height: root.secondaryIconSize
                        source: Assets.tileImage(modelData)
                        fillMode: Image.PreserveAspectFit
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true

                        onEntered: root.secondaryHovered = true
                        onExited: root.secondaryHovered = false
                        onClicked: root.tileRequested(modelData)
                        onWheel: function(wheel) {
                            root.selectTileOffset(wheel.angleDelta.y > 0 ? -1 : 1);
                            wheel.accepted = true;
                        }
                    }
                }
            }
        }

        Row {
            id: primaryRow
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.secondaryButtonSize + root.rowSpacing
            spacing: root.itemSpacing

            Repeater {
                model: root.primaryItems

                delegate: Rectangle {
                    id: primaryButton
                    width: root.primaryButtonSize
                    height: root.primaryButtonSize
                    radius: root.buttonRadius

                    readonly property bool selected: index === root.currentPrimaryIndex()

                    color: selected ? AppTheme.surfaceVariant : AppTheme.surface
                    border.color: selected ? AppTheme.primary : AppTheme.border

                    Text {
                        anchors.centerIn: parent
                        visible: modelData.kind === "mode"
                        text: modelData.label
                        color: AppTheme.textPrimary
                        font.bold: true
                        font.pixelSize: 18
                    }

                    Image {
                        anchors.centerIn: parent
                        visible: modelData.kind === "tileGroup"
                        width: root.primaryIconSize
                        height: root.primaryIconSize
                        source: modelData.kind === "tileGroup" ? Assets.tileImage(modelData.tile) : ""
                        fillMode: Image.PreserveAspectFit
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true

                        onEntered: root.hoveredPrimaryIndex = index
                        onExited: {
                            if (root.hoveredPrimaryIndex === index)
                                root.hoveredPrimaryIndex = -1;
                        }
                        onClicked: root.choosePrimary(modelData)
                        onWheel: function(wheel) {
                            root.selectPrimaryOffset(wheel.angleDelta.y > 0 ? -1 : 1);
                            wheel.accepted = true;
                        }
                    }
                }
            }
        }
    }
}
