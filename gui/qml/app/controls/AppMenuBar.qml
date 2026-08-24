pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import app.global
import app.manager

MenuBar {
    id: root

    required property WorkspaceManager workspaceManager

    property alias color: background.color
    property color itemHoverColor: AppTheme.hoverOverlay
    property color itemTextColor: AppTheme.textPrimary

    property int itemLeftPadding: 8
    property int itemRightPadding: 8
    property int itemTopPadding: 4
    property int itemBottomPadding: 4
    property int itemRadius: 4

    spacing: 4

    background: Rectangle {
        id: background
        color: "transparent"
    }

    delegate: MenuBarItem {
        id: menuBarItem

        leftPadding: root.itemLeftPadding
        rightPadding: root.itemRightPadding
        topPadding: root.itemTopPadding
        bottomPadding: root.itemBottomPadding

        background: Rectangle {
            color: menuBarItem.highlighted ? root.itemHoverColor : "transparent"
            radius: root.itemRadius
        }

        contentItem: Text {
            id: itemText
            text: menuBarItem.text
            font: menuBarItem.font
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            color: root.itemTextColor
        }
    }

    FileMenu {
        workspaceManager: root.workspaceManager
    }

    Menu {
        id: editMenu
        title: qsTr("Edit")
    }
}
