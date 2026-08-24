import QtQuick
import QtQuick.Controls

import app.controls

AppDialog {
    id: root
    parent: Overlay.overlay
    anchors.centerIn: parent

    headerText: qsTr("Alert")

    footerItems: [
        {
            text: qsTr("Close")
        }
    ]

    function alert(message) {
        root.text = message;
        root.open();
    }
}
