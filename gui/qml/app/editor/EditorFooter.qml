pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import app
import app.global
import app.models

Rectangle {
    id: root

    property var editor: null

    implicitHeight: 34
    color: AppTheme.surface
    border.color: AppTheme.border

    function modeTitle(mode) {
        switch (mode) {
        case ToolMode.puzzle:
            return qsTr("Puzzle Mode");
        case ToolMode.tile:
            return qsTr("Tile Brush");
        case ToolMode.tileStatus:
            return qsTr("Tile Status");
        default:
            return qsTr("Inspect");
        }
    }

    function guideText(mode) {
        switch (mode) {
        case ToolMode.puzzle:
            return qsTr("Left click: select/create puzzle | Wheel: zoom | Middle drag: pan");
        case ToolMode.tile:
            return qsTr("Left drag: paint | Right drag: erase | Wheel: zoom | Middle drag: pan");
        case ToolMode.tileStatus:
            return qsTr("Left drag: set status | Right drag: reset status | Wheel: zoom | Middle drag: pan");
        default:
            return qsTr("Wheel: zoom | Middle drag: pan");
        }
    }

    readonly property string editorMode: editor?.mode ?? ToolMode.inspect
    readonly property int editorTile: editor?.currentTile ?? Tile.GRASSLAND
    readonly property int editorStatus: editor?.currentStatus ?? Tile.NORMAL
    readonly property bool hasTilePreview: editorMode === ToolMode.tile
    readonly property bool hasStatusPreview: editorMode === ToolMode.tileStatus

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 10

        Label {
            text: root.modeTitle(root.editorMode)
            color: AppTheme.textPrimary
            font.bold: true
        }

        Rectangle {
            visible: root.hasTilePreview || root.hasStatusPreview
            Layout.preferredWidth: 24
            Layout.preferredHeight: 24
            radius: 4
            color: AppTheme.surfaceVariant
            border.color: AppTheme.border

            Image {
                anchors.centerIn: parent
                width: 20
                height: 20
                source: root.hasTilePreview ? Assets.tileImage(root.editorTile) : Assets.tileStatusImage(root.editorStatus)
                fillMode: Image.PreserveAspectFit
                smooth: true
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.guideText(root.editorMode)
            color: AppTheme.textSecondary
            elide: Text.ElideRight
        }
    }
}
