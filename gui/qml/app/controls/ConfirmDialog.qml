import QtQuick.Controls
import app.controls

AppDialog {
    id: root
    parent: Overlay.overlay
    anchors.centerIn: parent

    property string confirmText: qsTr("Confirm")
    property string cancelText: qsTr("Cancel")
    property var confirmAction: null

    footerItems: [
        {
            text: root.confirmText,
            callback: () => {
                root.confirmAction?.();
            }
        },
        {
            text: root.cancelText
        }
    ]

    function showConfirm(confirmAction, text, headerText, confirmText) {
        root.confirmAction = confirmAction;
        root.text = text;
        root.headerText = headerText || qsTr("Confirm Action");
        root.confirmText = confirmText || qsTr("Confirm");
        root.open();
    }
}
