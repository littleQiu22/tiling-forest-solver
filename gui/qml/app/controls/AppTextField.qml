import QtQuick
import QtQuick.Controls.Basic

import app.global

TextField {
    id: root

    implicitWidth: Math.max(80, contentItem.implicitWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(26, contentItem.implicitHeight + topPadding + bottomPadding)
    leftPadding: 8
    rightPadding: 8
    topPadding: 4
    bottomPadding: 4
    color: AppTheme.textPrimary
    selectionColor: AppTheme.selectionOverlay
    selectedTextColor: AppTheme.textPrimary

    background: Rectangle {
        radius: 4
        color: root.enabled ? AppTheme.surface : AppTheme.surfaceVariant
        border.width: 1
        border.color: root.activeFocus ? AppTheme.primary : AppTheme.border

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: root.hovered ? AppTheme.hoverOverlay : "transparent"
        }
    }
}
