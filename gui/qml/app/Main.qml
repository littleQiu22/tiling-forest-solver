import QtQuick.Window

import app.global
import app.layout
import app.controls
import app.manager
import app.editor

Window {
    id: root
    title: "Tiling Forest Solver"
    visible: false

    readonly property WorkspaceManager workspaceManager: WorkspaceManager {}

    AlterDialog {
        id: alterDialog

        Connections {
            target: Services

            function onAlertRequested(message) {
                alterDialog.showAlert(message);
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: AppTheme.background

        AppLayout {
            anchors.fill: parent

            workspaceManager: root.workspaceManager

            menuBar: AppMenuBar {
                workspaceManager: root.workspaceManager
            }

            tileEditor: Editor {
                workspace: root.workspaceManager.workspace
            }

            puzzlePanel: Rectangle {
                color: "yellow"
                implicitWidth: 200
            }
        }
    }

    Component.onCompleted: {
        AppSettings.restoreWindow(root);
        visible = true;
    }

    onClosing: AppSettings.saveWindow(root)
}
