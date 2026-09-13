import QtQuick
import QtQuick.Controls.Basic

import app.global

CheckBox {
    id: root

    property int indicatorSize: 14

    spacing: 6
    leftPadding: 0
    rightPadding: 0
    topPadding: 2
    bottomPadding: 2

    indicator: Rectangle {
        x: root.leftPadding
        y: root.topPadding + Math.round((root.availableHeight - height) / 2)
        implicitWidth: root.indicatorSize
        implicitHeight: root.indicatorSize
        radius: 3
        color: root.checked ? AppTheme.primary : AppTheme.surface
        border.width: 1
        border.color: root.checked ? AppTheme.primary : AppTheme.border

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: root.down ? AppTheme.pressOverlay : (root.hovered ? AppTheme.hoverOverlay : "transparent")
        }

        Text {
            anchors.centerIn: parent
            visible: root.checked
            text: "✓"
            color: AppTheme.surface
            font.pixelSize: 10
            font.bold: true
        }
    }

    contentItem: Text {
        text: root.text
        font: root.font
        color: root.enabled ? AppTheme.textPrimary : AppTheme.textSecondary
        verticalAlignment: Text.AlignVCenter
        leftPadding: root.indicator.width + root.spacing
    }
}
