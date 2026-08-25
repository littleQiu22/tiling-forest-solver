import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Controls.impl

import app.global

Button {
    id: root

    property var backgroundColor
    property bool borderEnabled: true

    background: Rectangle {
        id: background
        color: root.backgroundColor ?? "transparent"
        radius: 4
        border.color: root.borderEnabled ? AppTheme.border : "transparent"

        Rectangle {
            anchors.fill: parent
            color: root.hovered ? AppTheme.hoverOverlay : "transparent"
        }
    }

    contentItem: IconLabel {
        icon: root.icon
        text: root.text
        font: root.font

        color: AppTheme.textPrimary
    }
}
