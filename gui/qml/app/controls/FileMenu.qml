import QtQuick
import QtQuick.Controls

import app.global
import app.manager

AppMenu {
    id: root
    title: "File"

    property WorkspaceManager workspaceManager

    // === Actions ===
    Action {
        id: newAction
        text: qsTr("New")
        shortcut: "Ctrl+N"
        onTriggered: () => {}
    }

    // Runs loadFn after handling an unsaved/untitled workspace.
    function openDocument(loadFn) {
        let ws = root.workspaceManager.workspace;
        if (ws.isDirty) {
            if (!!root.workspaceManager.filePath) {
                let response = root.workspaceManager.save();
                if (!response.status) {
                    AlterDialog.alert(response.message);
                    return;
                }
            }
        }
        loadFn();
    }

    // === UI ===
    AppMenuItem {
        text: qsTr("New")
        shortcutText: qsTr("Ctrl+N")
    }

    AppMenuItem {
        text: qsTr("Open...")
        shortcutText: qsTr("Ctrl+O")
    }

    AppMenu {
        title: qsTr("Recent Files")

        AppMenuItem {
            text: qsTr("Clear Recently Opened")
        }
    }

    AppMenu {
        title: qsTr("Open Template")
    }

    AppMenuItem {
        text: qsTr("Save")
        shortcutText: qsTr("Ctrl+S")
    }

    AppMenuItem {
        text: qsTr("Save As...")
        shortcutText: qsTr("Ctrl+Shift+S")
    }
}
