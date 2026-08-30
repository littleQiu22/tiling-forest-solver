import QtQuick.Window
import QtQuick.Controls

import app.global
import app.layout
import app.controls
import app.manager
import app.editor

Window {
    id: root
    title: (root.workspaceManager.workspace.isDirty ? "* " : "") + root.workspaceManager.displayName + qsTr(" | Tiling Forest Solver")
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
            id: appLayout
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

    function loadStartupRecentFile() {
        if (!AppSettings.recentFiles || AppSettings.recentFiles.length === 0)
            return false;

        const filePath = AppSettings.recentFiles[0];
        const response = root.workspaceManager.load(filePath);
        if (!response.status) {
            AppSettings.removeRecentFile(filePath);
            return false;
        }

        AppSettings.addRecentFile(root.workspaceManager.filePath);
        return true;
    }

    Component.onCompleted: {
        AppSettings.restoreWindow(root);
        if (root.loadStartupRecentFile())
            appLayout.tileEditorItem?.restoreCameraState(AppSettings.cameraState());
        visible = true;
    }

    onClosing: function (close) {
        AppSettings.saveWindow(root);
        AppSettings.saveCameraState(appLayout.tileEditorItem?.cameraState());
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
