import QtQuick.Window

import app.global

Window {
    id: root
    title: "Tiling Forest Solver"
    visible: false

    Component.onCompleted: {
        AppSettings.restoreWindow(root);
        visible = true;
    }

    onClosing: AppSettings.saveWindow(root)
}
