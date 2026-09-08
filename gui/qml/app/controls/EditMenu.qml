import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import app.global
import app.controls
import app.manager

AppMenu {
    id: root
    title: qsTr("Edit")

    property WorkspaceManager workspaceManager

    // === Actions ===
    property Action undoAction: Action {
        text: qsTr("Undo")
        shortcut: "Ctrl+Z"
        onTriggered: {
            let ws = root.workspaceManager.workspace;
            let undoHeavyReason = ws.getUndoHeavyReason();
            if (!!undoHeavyReason) {
                Services.confirm(() => {
                    ws.undo();
                }, undoHeavyReason, qsTr("Confirm Action"), qsTr("Continue"));
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
        onTriggered: {
            let ws = root.workspaceManager.workspace;
            let queryHeavyReason = true;
            let executeHeavyReason = ws.clear(queryHeavyReason);
            if (executeHeavyReason) {
                Services.confirm(() => {
                    let ws = root.workspaceManager.workspace;
                    ws.clear();
                }, executeHeavyReason, qsTr("Confirm Action"), qsTr("Continue"));
            } else {
                ws.clear();
            }
        }
    }

    property Action revertAction: Action {
        id: revertAction
        text: qsTr("Revert")
        onTriggered: Services.confirm(() => {
            let response = root.workspaceManager.revert();
            if (!response.status) {
                Services.alert(response.message);
            }
        }, qsTr("The workspace will be restored to the state stored in the file."), qsTr("Confirm Action"), qsTr("Continue"))
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
