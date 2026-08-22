import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 0

    property Component menuBar
    property Component tileEditor
    property Component puzzlePanel

    Loader {
        id: menuBarLoader
        Layout.fillWidth: true
        Layout.preferredHeight: menuBarLoader.implicitHeight

        sourceComponent: root.menuBar
        Binding {
            target: menuBarLoader.item
            property: "width"
            value: menuBarLoader.width
            when: menuBarLoader.item !== null
        }
        Binding {
            target: menuBarLoader.item
            property: "height"
            value: menuBarLoader.height
            when: menuBarLoader.item !== null
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 0

        Loader {
            id: tileEditorLoader
            Layout.fillWidth: true
            Layout.fillHeight: true

            sourceComponent: root.tileEditor
            Binding {
                target: tileEditorLoader.item
                property: "width"
                value: tileEditorLoader.width
                when: tileEditorLoader.item !== null
            }
            Binding {
                target: tileEditorLoader.item
                property: "height"
                value: tileEditorLoader.height
                when: tileEditorLoader.item !== null
            }
        }

        Loader {
            id: puzzlePanelLoader
            Layout.preferredWidth: puzzlePanelLoader.implicitWidth
            Layout.fillHeight: true

            sourceComponent: root.puzzlePanel
            Binding {
                target: puzzlePanelLoader.item
                property: "width"
                value: puzzlePanelLoader.width
                when: puzzlePanelLoader.item !== null
            }
            Binding {
                target: puzzlePanelLoader.item
                property: "height"
                value: puzzlePanelLoader.height
                when: puzzlePanelLoader.item !== null
            }
        }
    }
}
