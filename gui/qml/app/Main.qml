import QtQuick.Window
import QtQuick.Controls

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
    property bool closeConfirmed: false

    AlterDialog {
        id: alterDialog

        Connections {
            target: Services

            function onAlertRequested(message) {
                alterDialog.showAlert(message);
            }
        }
    }

    ConfirmDialog {
        id: confirmDialog

        Connections {
            target: Services

            function onConfirmRequested(confirmAction, text, headerText, confirmText) {
                confirmDialog.showConfirm(confirmAction, text, headerText, confirmText);
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

            puzzlePanel: PuzzlePanel {
                workspace: root.workspaceManager.workspace
            }
        }
    }

    Component.onCompleted: {
        AppSettings.restoreWindow(root);
        visible = true;
    }

    onClosing: function (close) {
        AppSettings.saveWindow(root);
        if (root.workspaceManager.workspace.isDirty && !root.closeConfirmed) {
            close.accepted = false;
            Services.confirm(() => {
                root.workspaceManager.workspace.stopAllSolvers();
                root.closeConfirmed = true;
                root.close();
            }, qsTr("The current workspace has unsaved changes. They will be discarded."), qsTr("Discard Unsaved Workspace?"), qsTr("Discard && Exit"));
        } else {
            root.workspaceManager.workspace.stopAllSolvers();
        }
    }
}
