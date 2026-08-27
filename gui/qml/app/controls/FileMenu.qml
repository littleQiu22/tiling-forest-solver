import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import app.global
import app.controls
import app.manager

AppMenu {
    id: root
    title: "File"

    property WorkspaceManager workspaceManager

    // File/Confirm Dialogs
    ConfirmDialog {
        id: discardDialog
        parent: Overlay.overlay
        anchors.centerIn: parent

        headerText: qsTr("Discard Unsaved Workspace?")
        confirmText: qsTr("Discard && Continue")
    }

    FileDialog {
        id: openDialog
        title: qsTr("Open Workspace...")
        fileMode: FileDialog.OpenFile
        nameFilters: ["JSON files (*.json)", "All files (*)"]
        onAccepted: {
            openDocument(() => {
                let response = root.workspaceManager.load(selectedFile.toLocalFile());
                if (!response.status) {
                    Services.alert(response.message);
                    return;
                }
                AppSettings.addRecentFile(root.workspaceManager.filePath);
            });
        }
    }

    FileDialog {
        id: saveAsDialog
        title: qsTr("Save Workspace As")
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON files (*.json)", "All files (*)"]
        onAccepted: {
            let response = root.workspaceManager.save(selectedFile.toLocalFile());
            if (!response.status) {
                Services.alert(response.message);
                return;
            }
            AppSettings.addRecentFile(root.workspaceManager.filePath);
        }
    }

    // === Actions ===
    property Action newAction: Action {
        text: qsTr("New")
        shortcut: "Ctrl+N"
        onTriggered: openDocument(() => {
            root.workspaceManager.new();
        })
    }

    property Action openAction: Action {
        text: qsTr("Open...")
        shortcut: "Ctrl+O"
        onTriggered: openDocument(() => openDialog.open())
    }

    property Action saveAction: Action {
        text: qsTr("Save")
        shortcut: "Ctrl+S"
        onTriggered: {
            if (!!root.workspaceManager.filePath) {
                let response = root.workspaceManager.save();
                if (!response.status) {
                    Services.alert(response.message);
                }
            } else {
                saveAsDialog.open();
            }
        }
    }

    property Action saveAsAction: Action {
        text: qsTr("Save As...")
        shortcut: "Ctrl+Shift+S"
        onTriggered: saveAsDialog.open()
    }

    // Runs loadFn after handling an unsaved/untitled workspace.
    function openDocument(loadFn) {
        let ws = root.workspaceManager.workspace;
        if (ws.isDirty) {
            if (!!root.workspaceManager.filePath) {
                let response = root.workspaceManager.save();
                if (!response.status) {
                    Services.alert(response.message);
                    return;
                }
            } else {
                discardDialog.showConfirm(loadFn, "The current workspace has unsaved changes and no file path. They will be discarded.");
                return;
            }
        }
        loadFn();
    }

    // === UI ===
    AppMenuItem {
        text: qsTr("New")
        shortcutText: qsTr("Ctrl+N")
        action: root.newAction
    }

    AppMenuItem {
        text: qsTr("Open...")
        shortcutText: qsTr("Ctrl+O")
        action: root.openAction
    }

    AppMenu {
        title: qsTr("Open Recent")

        AppMenuItem {
            text: qsTr("Clear Recently Opened")
            onTriggered: AppSettings.clearRecentFiles()
        }

        Repeater {
            model: AppSettings.recentFiles
            delegate: AppMenuItem {
                text: modelData

                onTriggered: openDocument(() => {
                    const filePath = modelData;
                    let response = root.workspaceManager.load(filePath);
                    if (!response.status) {
                        Qt.callLater(() => AppSettings.removeRecentFile(filePath));
                    }
                })
            }
        }
    }

    AppMenu {
        title: qsTr("Open Template")

        Repeater {
            model: root.workspaceManager.templates
            delegate: AppMenuItem {
                text: modelData

                onTriggered: openDocument(() => {
                    let response = root.workspaceManager.loadTemplate(modelData);
                    if (!response.status) {
                        Services.alert(response.message);
                    }
                })
            }
        }
    }

    AppMenuItem {
        text: qsTr("Save")
        shortcutText: qsTr("Ctrl+S")
        action: root.saveAction
    }

    AppMenuItem {
        text: qsTr("Save As...")
        shortcutText: qsTr("Ctrl+Shift+S")
        action: root.saveAsAction
    }
}
