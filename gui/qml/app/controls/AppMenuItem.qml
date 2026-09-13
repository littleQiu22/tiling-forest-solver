import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import app.global

MenuItem {
    id: root

    property string shortcutText: ""
    property int textElide: Text.ElideRight

    leftPadding: 8
    rightPadding: 8
    topPadding: 4
    bottomPadding: 4

    background: Rectangle {
        radius: 4
        color: root.highlighted ? AppTheme.hoverOverlay : "transparent"
    }

    indicator: Item {}
    arrow: Item {}

    contentItem: RowLayout {
        spacing: 8

        Item {
            visible: root.checkable
            Layout.preferredWidth: 14
            Layout.preferredHeight: 14
            Layout.alignment: Qt.AlignVCenter

            Rectangle {
                anchors.centerIn: parent
                width: 12
                height: 12
                radius: 3
                visible: root.checked
                color: AppTheme.primary

                Text {
                    anchors.centerIn: parent
                    text: "✓"
                    color: AppTheme.surface
                    font.pixelSize: 9
                    font.bold: true
                }
            }
        }

        Text {
            id: itemText
            text: root.text
            font: root.font
            color: AppTheme.textPrimary
            elide: root.textElide
            verticalAlignment: Text.AlignVCenter
            Layout.alignment: Qt.AlignVCenter
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
