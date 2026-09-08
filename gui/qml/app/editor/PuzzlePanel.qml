pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

import app.global
import app.models

Rectangle {
    id: root

    required property Workspace workspace

    color: AppTheme.surface
    border.color: AppTheme.border
    implicitWidth: 340

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        PuzzleList {
            Layout.fillWidth: true
            Layout.preferredHeight: 246
            Layout.maximumHeight: 246
            workspace: root.workspace
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: AppTheme.border
        }

        PuzzleInspector {
            Layout.fillWidth: true
            Layout.fillHeight: true
            workspace: root.workspace
        }
    }
}
