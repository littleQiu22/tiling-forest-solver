import QtQuick.Window

import app.global
import app.layout

Window {
    id: root
    title: "Tiling Forest Solver"
    visible: false

    AppLayout {
        anchors.fill: parent

        menuBar: Rectangle {
            color: "red"
            implicitHeight: 300
        }

        tileEditor: Rectangle {
            color: "blue"
        }

        puzzlePanel: Rectangle {
            color: "yellow"
            implicitWidth: 200
        }
    }

    Component.onCompleted: {
        AppSettings.restoreWindow(root);
        visible = true;
    }

    onClosing: AppSettings.saveWindow(root)
}
