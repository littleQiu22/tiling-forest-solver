import QtQuick
import QtQuick.Controls

import app.global

Menu {
    id: root

    implicitWidth: 200
    leftInset: 0
    rightInset: 0
    topInset: 0
    bottomInset: 0

    leftPadding: 0
    rightPadding: 0
    topPadding: 0
    bottomPadding: 0

    delegate: AppMenuItem {}

    background: Rectangle {
        color: AppTheme.surface
        border.color: AppTheme.border
        radius: 4
    }
}
