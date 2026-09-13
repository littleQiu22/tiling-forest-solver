pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import app.controls
import app.global
import app.models

ColumnLayout {
    id: root

    required property Workspace workspace

    property string renamingId: ""
    property string renamingText: ""
    readonly property int recordHeight: 36
    readonly property int preferredPanelHeight: 246
    readonly property int dragAutoScrollMargin: 28
    readonly property real dragAutoScrollStep: 10

    spacing: 4
    implicitHeight: preferredPanelHeight

    QtObject {
        id: dragState

        property bool active: false
        property string puzzleId: ""
        property string puzzleName: ""
        property string resultStatus: ""
        property bool isGeometryStaled: false
        property int dropIndex: -1
        property real pointerY: 0
        property string hoveredPuzzleId: ""

        property real pressedY: 0
        property string pressedPuzzleId: ""
        property string pressedPuzzleName: ""
        property string pressedResultStatus: ""
        property bool pressedIsGeometryStaled: false

        readonly property int dragThreshold: 2

        function pressRecord(item, listY) {
            pressedY = listY;
            pressedPuzzleId = item.puzzleId;
            pressedPuzzleName = item.name;
            pressedResultStatus = item.resultStatus;
            pressedIsGeometryStaled = item.isGeometryStaled;
            hoveredPuzzleId = pressedPuzzleId;
            updateDropIndexFromListY(listY);
        }

        function hoverRecord(item) {
            hoveredPuzzleId = item?.puzzleId ?? "";
        }

        function canStartDrag(listY) {
            return Math.abs(listY - pressedY) >= dragThreshold;
        }

        function startDrag(listY) {
            active = true;
            puzzleId = pressedPuzzleId;
            puzzleName = pressedPuzzleName;
            resultStatus = pressedResultStatus;
            isGeometryStaled = pressedIsGeometryStaled;
            updateDropIndexFromListY(listY);
        }

        function updateDropIndexFromListY(listY) {
            pointerY = listY;
            dropIndex = root.dropIndexFromListY(root.clamp(listY, 0, listFrame.height));
        }

        function resetPressed() {
            pressedY = 0;
            pressedPuzzleId = "";
            pressedPuzzleName = "";
            pressedResultStatus = "";
            pressedIsGeometryStaled = false;
        }

        function resetDrag() {
            active = false;
            puzzleId = "";
            puzzleName = "";
            resultStatus = "";
            isGeometryStaled = false;
            dropIndex = -1;
            pointerY = 0;
        }

        function resetAll() {
            resetPressed();
            resetDrag();
            hoveredPuzzleId = "";
        }
    }

    function clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value));
    }

    function clampDropIndex(index) {
        return Math.max(0, Math.min(puzzleList.count, index));
    }

    function deletePuzzle(puzzleId) {
        let queryHeavyReason = true;
        let heavyReason = root.workspace.deletePuzzle(puzzleId, queryHeavyReason);
        if (!!heavyReason) {
            Services.confirm(() => root.workspace.deletePuzzle(puzzleId), heavyReason, qsTr("Delete Puzzle?"), qsTr("Delete"));
        } else {
            root.workspace.deletePuzzle(puzzleId);
        }
    }

    function finishRename(puzzleId, name) {
        if (root.renamingId !== puzzleId)
            return;

        root.workspace.renamePuzzle(puzzleId, name);
        root.renamingId = "";
        listFrame.forceActiveFocus();
    }

    function focusPuzzleRecord(puzzleId) {
        let index = root.workspace.puzzles.indexById(puzzleId);
        if (index < 0)
            return;

        let item = puzzleList.itemAtIndex(index);
        let itemTop = item ? item.mapToItem(listFrame, 0, 0).y : 0;
        if (item && itemTop >= 0 && itemTop + item.height <= listFrame.height)
            return;

        puzzleList.positionViewAtIndex(index, ListView.Center);
    }

    function puzzleStride() {
        return root.recordHeight + puzzleList.spacing;
    }

    function puzzleContentHeight() {
        if (puzzleList.count <= 0)
            return 0;
        return puzzleList.count * root.recordHeight + (puzzleList.count - 1) * puzzleList.spacing;
    }

    function contentStartY() {
        return puzzleList.originY;
    }

    function minContentY() {
        return root.contentStartY();
    }

    function maxContentY() {
        return Math.max(root.minContentY(), root.contentStartY() + root.puzzleContentHeight() - puzzleList.height);
    }

    function indexContentY(index) {
        return root.contentStartY() + index * root.puzzleStride();
    }

    function listYToContentY(listY) {
        return listFrame.mapToItem(puzzleList.contentItem, 0, listY).y;
    }

    function contentYToListY(contentY) {
        return puzzleList.contentItem.mapToItem(listFrame, 0, contentY).y;
    }

    function itemTopInList(item) {
        return item.mapToItem(listFrame, 0, 0).y;
    }

    function dropIndexFromListY(listY) {
        if (puzzleList.count <= 0)
            return 0;

        let pointerListY = root.clamp(listY, 0, listFrame.height);
        let pointerContentY = root.listYToContentY(pointerListY);
        let fallbackIndex = root.clampDropIndex(Math.round((pointerContentY - root.contentStartY()) / root.puzzleStride()));

        for (let index = 0; index < puzzleList.count; ++index) {
            let item = puzzleList.itemAtIndex(index);
            if (!item)
                continue;

            if (pointerListY < item.mapToItem(listFrame, 0, item.height / 2).y)
                return index;

            fallbackIndex = index + 1;
        }

        return root.clampDropIndex(fallbackIndex);
    }

    function recordAtListY(listY) {
        let pointerListY = root.clamp(listY, 0, listFrame.height);
        for (let index = 0; index < puzzleList.count; ++index) {
            let item = puzzleList.itemAtIndex(index);
            if (!item)
                continue;

            let itemTop = root.itemTopInList(item);
            if (pointerListY >= itemTop && pointerListY <= itemTop + item.height)
                return item;
        }
        return null;
    }

    function dropLineY() {
        if (puzzleList.count <= 0 || dragState.dropIndex < 0)
            return 0;

        let index = root.clampDropIndex(dragState.dropIndex);
        if (index <= 0) {
            let firstItem = puzzleList.itemAtIndex(0);
            return firstItem ? root.itemTopInList(firstItem) : 0;
        }

        if (index >= puzzleList.count) {
            let lastItem = puzzleList.itemAtIndex(puzzleList.count - 1);
            return lastItem ? root.itemTopInList(lastItem) + lastItem.height : listFrame.height;
        }

        let item = puzzleList.itemAtIndex(index);
        if (item)
            return root.itemTopInList(item) - puzzleList.spacing / 2;

        let previousItem = puzzleList.itemAtIndex(index - 1);
        if (previousItem)
            return root.itemTopInList(previousItem) + previousItem.height + puzzleList.spacing / 2;

        return root.contentYToListY(root.indexContentY(index));
    }

    function dragPreviewY() {
        return root.clamp(dragState.pointerY - root.recordHeight / 2, 0, Math.max(0, listFrame.height - root.recordHeight));
    }

    function finishPuzzleDrag(puzzleId, shouldCommit) {
        let wasDragging = dragState.active;
        let targetDropIndex = dragState.dropIndex;

        dragState.resetAll();

        if (wasDragging && shouldCommit && targetDropIndex >= 0)
            root.workspace.movePuzzle(puzzleId, targetDropIndex);
    }

    Label {
        Layout.fillWidth: true
        text: qsTr("Puzzles (%1)").arg(puzzleList.count)
        color: AppTheme.textSecondary
        font.bold: true
    }

    Item {
        id: listFrame

        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        focus: true

        ListView {
            id: puzzleList

            anchors.fill: parent
            clip: true
            spacing: 4
            model: root.workspace.puzzles
            contentHeight: root.puzzleContentHeight()
            interactive: !dragState.active
            boundsBehavior: Flickable.StopAtBounds
            boundsMovement: Flickable.StopAtBounds

            delegate: Item {
                id: puzzleRecord

                required property string puzzleId
                required property string name
                required property string resultStatus
                required property bool isGeometryStaled
                required property bool isSelected
                width: puzzleList.width
                height: root.recordHeight

                Rectangle {
                    id: recordBody

                    anchors.fill: parent
                    radius: 4
                    opacity: dragState.active && dragState.puzzleId === puzzleRecord.puzzleId ? 0.35 : 1
                    color: puzzleRecord.isSelected ? AppTheme.surfaceVariant : "transparent"
                    border.color: puzzleRecord.isSelected ? AppTheme.primary : AppTheme.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 6

                        Item {
                            id: dragHandle

                            Layout.preferredWidth: 28
                            Layout.preferredHeight: 30

                            Grid {
                                anchors.centerIn: parent
                                columns: 2
                                rowSpacing: 3
                                columnSpacing: 3

                                Repeater {
                                    model: 6

                                    delegate: Rectangle {
                                        width: 3
                                        height: 3
                                        radius: 1.5
                                        color: dragState.hoveredPuzzleId === puzzleRecord.puzzleId || dragState.puzzleId === puzzleRecord.puzzleId ? AppTheme.textSecondary : AppTheme.border
                                    }
                                }
                            }
                        }

                        Item {
                            Layout.preferredWidth: 22
                            Layout.preferredHeight: 22

                            Rectangle {
                                anchors.centerIn: parent
                                width: 8
                                height: 8
                                radius: 4
                                color: PuzzleStyle.resultStatusColor(puzzleRecord.resultStatus)
                            }
                        }

                        AppTextField {
                            id: renameInput

                            Layout.fillWidth: true
                            visible: root.renamingId === puzzleRecord.puzzleId
                            text: root.renamingText
                            selectByMouse: true

                            onEditingFinished: {
                                root.finishRename(puzzleRecord.puzzleId, text);
                            }
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: root.renamingId !== puzzleRecord.puzzleId
                            text: puzzleRecord.name + (puzzleRecord.isGeometryStaled ? qsTr(" | Stale") : "")
                            color: AppTheme.textPrimary
                            elide: Text.ElideRight
                        }

                        AppButton {
                            text: qsTr("Rename")
                            color: AppTheme.textSecondary

                            onClicked: {
                                root.workspace.selectPuzzle(puzzleRecord.puzzleId);
                                root.renamingId = puzzleRecord.puzzleId;
                                root.renamingText = puzzleRecord.name;
                                renameInput.forceActiveFocus();
                                renameInput.selectAll();
                            }
                        }

                        AppButton {
                            text: qsTr("Delete")
                            color: AppTheme.textSecondary
                            onClicked: root.deletePuzzle(puzzleRecord.puzzleId)
                        }
                    }

                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        onTapped: root.workspace.selectPuzzle(puzzleRecord.puzzleId)
                    }
                }
            }
        }

        MouseArea {
            id: dragArea

            x: 0
            y: 0
            width: 40
            height: listFrame.height
            z: 200
            hoverEnabled: true
            cursorShape: dragState.hoveredPuzzleId !== "" || dragState.active ? Qt.SizeVerCursor : Qt.ArrowCursor
            preventStealing: true

            onPressed: function (mouse) {
                let item = root.recordAtListY(mouse.y);
                if (!item) {
                    mouse.accepted = false;
                    return;
                }

                dragState.pressRecord(item, mouse.y);
                root.workspace.selectPuzzle(dragState.pressedPuzzleId);
                mouse.accepted = true;
            }

            onPositionChanged: function (mouse) {
                if (!pressed && !dragState.active) {
                    dragState.hoverRecord(root.recordAtListY(mouse.y));
                    return;
                }

                if (dragState.pressedPuzzleId === "")
                    return;

                let pointerY = mouse.y;

                if (!dragState.active) {
                    if (!dragState.canStartDrag(pointerY))
                        return;

                    dragState.startDrag(pointerY);
                    return;
                }

                dragState.updateDropIndexFromListY(pointerY);
            }

            onReleased: function (mouse) {
                if (dragState.active) {
                    dragState.updateDropIndexFromListY(mouse.y);
                    root.finishPuzzleDrag(dragState.puzzleId, true);
                } else {
                    dragState.resetAll();
                }
            }

            onCanceled: {
                if (dragState.active)
                    root.finishPuzzleDrag(dragState.puzzleId, false);
                else
                    dragState.resetAll();
            }

            onExited: {
                if (!pressed && !dragState.active)
                    dragState.hoveredPuzzleId = "";
            }
        }

        Rectangle {
            visible: dragState.active && dragState.dropIndex >= 0
            x: 0
            y: root.dropLineY() - height / 2
            width: listFrame.width
            height: 2
            radius: 1
            color: AppTheme.primary
            z: 100
        }

        Rectangle {
            id: dragPreview

            visible: dragState.active
            x: 0
            y: root.dragPreviewY()
            width: listFrame.width
            height: root.recordHeight
            radius: 4
            color: AppTheme.surfaceVariant
            border.color: AppTheme.primary
            z: 101

            RowLayout {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 6

                Item {
                    Layout.preferredWidth: 28
                    Layout.preferredHeight: 30

                    Grid {
                        anchors.centerIn: parent
                        columns: 2
                        rowSpacing: 3
                        columnSpacing: 3

                        Repeater {
                            model: 6

                            delegate: Rectangle {
                                width: 3
                                height: 3
                                radius: 1.5
                                color: AppTheme.textSecondary
                            }
                        }
                    }
                }

                Item {
                    Layout.preferredWidth: 22
                    Layout.preferredHeight: 22

                    Rectangle {
                        anchors.centerIn: parent
                        width: 18
                        height: 18
                        radius: 9
                        color: "transparent"
                        border.width: 2
                        border.color: PuzzleStyle.resultStatusColor(dragState.resultStatus)
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: dragState.puzzleName + (dragState.isGeometryStaled ? qsTr(" | Stale") : "")
                    color: AppTheme.textPrimary
                    elide: Text.ElideRight
                }
            }
        }
    }

    Timer {
        interval: 16
        repeat: true
        running: dragState.active

        onTriggered: {
            let minContentY = root.minContentY();
            let maxContentY = root.maxContentY();
            let delta = 0;

            if (dragState.pointerY < root.dragAutoScrollMargin) {
                delta = -Math.min(root.dragAutoScrollStep, puzzleList.contentY - minContentY);
            } else if (dragState.pointerY > listFrame.height - root.dragAutoScrollMargin) {
                delta = Math.min(root.dragAutoScrollStep, maxContentY - puzzleList.contentY);
            }

            if (delta === 0)
                return;

            puzzleList.contentY = root.clamp(puzzleList.contentY + delta, minContentY, maxContentY);
            dragState.updateDropIndexFromListY(dragState.pointerY);
        }
    }

    Connections {
        target: root.workspace.puzzleView

        function onRequestPuzzleFocus(puzzleId) {
            root.focusPuzzleRecord(puzzleId);
        }
    }
}
