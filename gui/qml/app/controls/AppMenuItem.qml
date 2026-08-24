import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import app.global

MenuItem {
    id: root

    property string shortcutText: ""

    leftPadding: 8
    rightPadding: 8
    topPadding: 4
    bottomPadding: 4

    background: Rectangle {
        radius: 4
        color: root.highlighted ? AppTheme.hoverOverlay : "transparent"
    }

    arrow: Item {}

    contentItem: RowLayout {

        Text {
            id: itemText
            text: root.text
            font: root.font
            color: AppTheme.textPrimary
            verticalAlignment: Text.AlignVCenter
            Layout.alignment: Qt.AlignVCenter
        }

        Item {
            Layout.fillWidth: true
        }

        Text {
            text: root.shortcutText
            font: root.font
            color: AppTheme.textSecondary
            visible: text.length > 0
            verticalAlignment: Text.AlignVCenter
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            text: root.subMenu ? ">" : ""
            font: root.font
            color: AppTheme.textPrimary
            visible: root.subMenu
            verticalAlignment: Text.AlignVCenter
            Layout.alignment: Qt.AlignVCenter
        }
    }
}
