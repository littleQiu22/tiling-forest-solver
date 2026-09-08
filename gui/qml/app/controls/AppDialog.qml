import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import app.global

Dialog {
    id: root
    modal: true

    property bool autoClose: false
    closePolicy: autoClose ? Popup.CloseOnPressOutside : Popup.NoAutoClose
    property alias headerText: header.text
    property alias text: message.text
    property var footerItems: []
    readonly property int minDialogWidth: 200
    readonly property int maxDialogWidth: 400

    implicitWidth: Math.max(minDialogWidth, header.implicitWidth, footer.implicitWidth, Math.min(message.implicitWidth + message.leftPadding + message.rightPadding, maxDialogWidth))

    padding: 0

    background: Rectangle {
        color: AppTheme.surface
        border.color: AppTheme.border
        radius: 4
    }

    header: Label {
        id: header
        color: AppTheme.textSecondary
        font.bold: true
        padding: 8

        background: Rectangle {
            color: "transparent"
            border.color: AppTheme.border
        }
    }

    Label {
        id: message
        text: ""
        width: root.availableWidth
        padding: 8
        visible: text.length > 0
        color: AppTheme.textPrimary
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
    }

    footer: Pane {
        id: footer
        padding: 8

        background: Rectangle {
            color: "transparent"
        }

        contentItem: RowLayout {

            Item {
                Layout.fillWidth: true
            }

            Repeater {
                model: root.footerItems
                AppButton {
                    text: modelData.text
                    backgroundColor: modelData.backgroundColor

                    onClicked: {
                        root.close();
                        modelData.callback?.();
                    }
                }
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}
