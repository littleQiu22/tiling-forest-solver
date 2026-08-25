import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import app.global
import app.controls
import app.manager

AppMenu {
    id: root
    title: "Edit"

    property WorkspaceManager workspaceManager

    // Confirm Dialogs
    ConfirmDialog {
        id: heavyDialog
        parent: Overlay.overlay
        anchors.centerIn: parent

        headerText: qsTr("Confirm Action")
        confirmText: qsTr("Continue")
    }

    // === Actions ===
    property Action undoAction: Action {
        text: qsTr("Undo")
        shortcut: "Ctrl+Z"
        onTriggered: {
            let ws = root.workspaceManager.workspace;
            let undoHeavyReason = ws.getUndoHeavyReason();
            if (!!undoHeavyReason) {
                heavyDialog.showConfirm(() => {
                    ws.undo();
                }, undoHeavyReason);
            } else {
                ws.undo();
            }
        }
    }

    property Action redoAction: Action {
        text: qsTr("Redo")
        shortcut: "Ctrl+Y"
        onTriggered: root.workspaceManager.workspace.redo()
    }

    property Action clearAction: Action {
        text: qsTr("Clear")
        onTriggered: heavyDialog.showConfirm(() => {
            let ws = root.workspaceManager.workspace;
            ws.clear();
        }, "All tiles and puzzles will be removed. The action can still be undone afterwards.")
    }

    property Action revertAction: Action {
        id: revertAction
        text: qsTr("Revert")
        onTriggered: heavyDialog.showConfirm(() => {
            let response = root.workspaceManager.revert();
            if (!response.status) {
                Services.alert(response.message);
            }
        }, "The workspace will be restored to the state stored in the file.")
    }

    // === UI ===
    AppMenuItem {
        text: qsTr("Undo")
        shortcutText: qsTr("Ctrl+Z")
        action: root.undoAction
    }

    AppMenuItem {
        text: qsTr("Redo")
        shortcutText: qsTr("Ctrl+Y")
        action: root.redoAction
    }

    AppMenuItem {
        text: qsTr("Clear")
        action: root.clearAction
    }

    AppMenuItem {
        text: qsTr("Revert")
        action: root.revertAction
    }
}
