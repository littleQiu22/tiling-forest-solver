pragma ComponentBehavior: Bound

import QtQuick

import app.manager

AppMenuBar {
    id: root

    required property WorkspaceManager workspaceManager

    FileMenu {
        workspaceManager: root.workspaceManager
    }

    EditMenu {
        workspaceManager: root.workspaceManager
    }

    LanguageMenu {}
}
