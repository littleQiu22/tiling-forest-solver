pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts

import app
import app.controls
import app.global
import app.models

Rectangle {
    id: root
    color: AppTheme.surface
    border.color: AppTheme.border
    implicitWidth: 340

    required property Workspace workspace
    property string renamingId: ""
    property string renamingText: ""
    readonly property int puzzleRecordHeight: 36
    property bool isDraggingPuzzle: false
    property Item draggedRecord: null
    property int dragSourceIndex: -1
    property int dropIndex: -1
    readonly property int dragAutoScrollMargin: 28
    readonly property real dragAutoScrollStep: 10

    function statusColor(solveStatus) {
        switch (solveStatus) {
        case "Solved":
            return AppTheme.success;
        case "TimeLimit":
        case "SolutionLimit":
            return AppTheme.warning;
        case "Unsolved":
            return AppTheme.primary;
        case "Solving":
            return AppTheme.solving;
        default:
            return AppTheme.danger;
        }
    }

    function puzzleSummary() {
        if (!root.workspace.puzzleView.hasPuzzle)
            return qsTr("No puzzle selected");

        let parts = [root.workspace.puzzleView.name, root.workspace.puzzleView.solveStatus];
        if (root.workspace.puzzleView.isGeometryStaled)
            parts.push(qsTr("Geometry-stale"));
        return parts.join(" | ");
    }

    function refreshLogText() {
        const flick = logScroll.contentItem;
        const canScroll = flick && typeof flick.contentY === "number";
        const oldContentY = canScroll ? flick.contentY : 0;
        const wasAtBottom = canScroll && flick.contentY + flick.height >= flick.contentHeight - 4;

        logTextArea.text = root.workspace.puzzleView.solvingLog;
        Qt.callLater(() => {
            const currentFlick = logScroll.contentItem;
            if (!currentFlick || typeof currentFlick.contentY !== "number")
                return;

            const maxContentY = Math.max(0, currentFlick.contentHeight - currentFlick.height);
            currentFlick.contentY = wasAtBottom ? maxContentY : Math.min(oldContentY, maxContentY);
        });
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

    function rebuildPuzzle() {
        let message = root.workspace.rebuildPuzzle(root.workspace.puzzleView.puzzleId);
        if (!!message)
            Services.alert(message);
    }

    function focusPuzzleRecord(puzzleId) {
        let index = root.workspace.puzzles.indexById(puzzleId);
        if (index < 0)
            return;

        let item = puzzleList.itemAtIndex(index);
        if (item && item.y >= puzzleList.contentY && item.y + item.height <= puzzleList.contentY + puzzleList.height)
            return;

        puzzleList.positionViewAtIndex(index, ListView.Center);
    }

    function puzzleStride() {
        return root.puzzleRecordHeight + puzzleList.spacing;
    }

    function updateDropIndex(item) {
        if (!item || puzzleList.count <= 0) {
            root.dropIndex = -1;
            return;
        }

        let targetIndex = Math.round(item.y / root.puzzleStride());
        root.dropIndex = Math.max(0, Math.min(puzzleList.count, targetIndex));
    }

    function finishPuzzleDrag(puzzleId, shouldCommit) {
        let wasDragging = root.isDraggingPuzzle;
        let targetIndex = root.dragSourceIndex < root.dropIndex ? root.dropIndex - 1 : root.dropIndex;
        targetIndex = Math.max(0, Math.min(puzzleList.count - 1, targetIndex));

        root.isDraggingPuzzle = false;
        root.draggedRecord = null;
        root.dragSourceIndex = -1;
        root.dropIndex = -1;

        if (wasDragging && shouldCommit && targetIndex >= 0)
            root.workspace.movePuzzle(puzzleId, targetIndex);
    }

    Component {
        id: puzzleRecordDelegate

        Item {
            id: puzzleRecord
            required property string puzzleId
            required property string name
            required property string solveStatus
            required property bool isGeometryStaled
            required property bool isSelected
            required property int index

            width: puzzleList.width
            height: root.puzzleRecordHeight

            Rectangle {
                id: recordBody
                width: puzzleRecord.width
                height: puzzleRecord.height
                radius: 4
                color: dragArea.drag.active || puzzleRecord.isSelected ? AppTheme.surfaceVariant : "transparent"
                border.color: dragArea.drag.active || puzzleRecord.isSelected ? AppTheme.primary : AppTheme.border
                z: dragArea.drag.active ? 10 : 0

                Drag.active: dragArea.drag.active
                Drag.source: puzzleRecord
                Drag.hotSpot.x: width / 2
                Drag.hotSpot.y: height / 2

                states: State {
                    when: dragArea.drag.active

                    ParentChange {
                        target: recordBody
                        parent: puzzleList.contentItem
                        x: 0
                    }
                }

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
                                    color: dragArea.containsMouse || dragArea.drag.active ? AppTheme.textSecondary : AppTheme.border
                                }
                            }
                        }

                        MouseArea {
                            id: dragArea
                            anchors.fill: parent
                            cursorShape: Qt.SizeVerCursor
                            preventStealing: true
                            drag.target: recordBody
                            drag.axis: Drag.YAxis
                            drag.threshold: 2
                            drag.smoothed: false
                            drag.minimumY: drag.active ? 0 : -puzzleRecord.y
                            drag.maximumY: Math.max(0, puzzleList.contentHeight - recordBody.height - (drag.active ? 0 : puzzleRecord.y))

                            onPressed: {
                                root.dragSourceIndex = puzzleRecord.index;
                                root.dropIndex = puzzleRecord.index;
                                root.workspace.selectPuzzle(puzzleRecord.puzzleId);
                            }

                            onPositionChanged: {
                                if (drag.active && !root.isDraggingPuzzle) {
                                    root.isDraggingPuzzle = true;
                                    root.draggedRecord = recordBody;
                                }
                                if (drag.active)
                                    root.updateDropIndex(recordBody);
                            }

                            onReleased: {
                                root.finishPuzzleDrag(puzzleRecord.puzzleId, true);
                            }

                            onCanceled: {
                                root.finishPuzzleDrag(puzzleRecord.puzzleId, false);
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
                            border.color: root.statusColor(puzzleRecord.solveStatus)
                        }
                    }

                    TextInput {
                        id: renameInput
                        Layout.fillWidth: true
                        visible: root.renamingId === puzzleRecord.puzzleId
                        text: root.renamingText
                        selectByMouse: true
                        color: AppTheme.textPrimary
                        onEditingFinished: {
                            root.workspace.renamePuzzle(puzzleRecord.puzzleId, text);
                            root.renamingId = "";
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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        Label {
            Layout.fillWidth: true
            text: qsTr("Puzzles (%1)").arg(puzzleList.count)
            color: AppTheme.textSecondary
            font.bold: true
        }

        ListView {
            id: puzzleList
            Layout.fillWidth: true
            Layout.preferredHeight: 220
            clip: true
            spacing: 4
            model: root.workspace.puzzles
            delegate: puzzleRecordDelegate
            cacheBuffer: Math.max(height * 4, puzzleList.count * (root.puzzleRecordHeight + spacing))
            interactive: !root.isDraggingPuzzle
            boundsBehavior: Flickable.StopAtBounds
            boundsMovement: Flickable.StopAtBounds

            Rectangle {
                parent: puzzleList.contentItem
                visible: root.isDraggingPuzzle && root.dropIndex >= 0
                x: 0
                y: root.dropIndex * root.puzzleStride()
                width: puzzleList.width
                height: 2
                radius: 1
                color: AppTheme.primary
                z: 100
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: AppTheme.border
        }

        ScrollView {
            id: detailsScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            padding: 4

            ColumnLayout {
                width: detailsScroll.availableWidth
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true

                    Label {
                        id: summaryLabel
                        Layout.fillWidth: true
                        text: root.puzzleSummary()
                        color: summaryHover.hovered ? AppTheme.primary : (root.workspace.puzzleView.isGeometryStaled ? AppTheme.warning : AppTheme.textPrimary)
                        font.bold: true
                        font.underline: root.workspace.puzzleView.hasPuzzle
                        elide: Text.ElideRight

                        HoverHandler {
                            id: summaryHover
                            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                        }

                        TapHandler {
                            acceptedButtons: Qt.LeftButton
                            onTapped: root.workspace.selectPuzzle(root.workspace.puzzleView.puzzleId)
                        }
                    }

                    Item {
                        Layout.preferredWidth: 76
                        Layout.preferredHeight: rebuildButton.implicitHeight

                        AppButton {
                            id: rebuildButton
                            anchors.fill: parent
                            visible: root.workspace.puzzleView.hasPuzzle && root.workspace.puzzleView.isGeometryStaled
                            text: qsTr("Rebuild")
                            onClicked: root.rebuildPuzzle()
                        }
                    }
                }

                ColumnLayout {
                    id: details
                    Layout.fillWidth: true
                    visible: root.workspace.puzzleView.hasPuzzle
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Tile Pool")
                            color: AppTheme.textSecondary
                            font.bold: true
                        }

                        AppButton {
                            text: qsTr("Sync All")
                            onClicked: root.workspace.syncPuzzleConfigToAll(root.workspace.puzzleView.puzzleId, "tilePool")
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        width: details.width
                        spacing: 6

                        Repeater {
                            model: root.workspace.puzzleView.tilePoolItems

                            delegate: Rectangle {
                                required property var modelData

                                width: 38
                                height: 38
                                radius: 4
                                color: modelData.enabled ? AppTheme.surfaceVariant : AppTheme.surface
                                border.color: modelData.enabled ? AppTheme.primary : AppTheme.border

                                Image {
                                    anchors.centerIn: parent
                                    width: 30
                                    height: 30
                                    source: Assets.tileImage(modelData.tile)
                                    fillMode: Image.PreserveAspectFit
                                }

                                TapHandler {
                                    acceptedButtons: Qt.LeftButton
                                    onTapped: root.workspace.setPuzzleTileEnabled(root.workspace.puzzleView.puzzleId, modelData.tile, !modelData.enabled)
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Objectives")
                            color: AppTheme.textSecondary
                            font.bold: true
                        }

                        AppButton {
                            text: qsTr("Sync All")
                            onClicked: root.workspace.syncPuzzleConfigToAll(root.workspace.puzzleView.puzzleId, "objectives")
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Repeater {
                            model: root.workspace.puzzleView.objectiveItems

                            delegate: RowLayout {
                                required property var modelData
                                width: parent.width
                                spacing: 6

                                CheckBox {
                                    Layout.fillWidth: true
                                    checked: modelData.enabled
                                    text: modelData.label
                                    onToggled: root.workspace.setPuzzleObjectiveEnabled(root.workspace.puzzleView.puzzleId, modelData.key, checked)
                                }

                                AppButton {
                                    text: qsTr("Raise")
                                    onClicked: root.workspace.movePuzzleObjective(root.workspace.puzzleView.puzzleId, modelData.key, -1)
                                }

                                AppButton {
                                    text: qsTr("Lower")
                                    onClicked: root.workspace.movePuzzleObjective(root.workspace.puzzleView.puzzleId, modelData.key, 1)
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Constraints")
                            color: AppTheme.textSecondary
                            font.bold: true
                        }

                        AppButton {
                            text: qsTr("Sync All")
                            onClicked: root.workspace.syncPuzzleConfigToAll(root.workspace.puzzleView.puzzleId, "constraints")
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Repeater {
                            model: root.workspace.puzzleView.constraintItems

                            delegate: CheckBox {
                                required property var modelData
                                checked: modelData.enabled
                                text: modelData.label
                                onToggled: root.workspace.setPuzzleConstraintEnabled(root.workspace.puzzleView.puzzleId, modelData.key, checked)
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Solving Configuration && Control")
                            color: AppTheme.textSecondary
                            font.bold: true
                        }

                        AppButton {
                            text: qsTr("Sync All")
                            onClicked: root.workspace.syncPuzzleConfigToAll(root.workspace.puzzleView.puzzleId, "limits")
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            CheckBox {
                                text: qsTr("Time limit(s)")
                                checked: root.workspace.puzzleView.hasTimeLimit
                                onClicked: root.workspace.setPuzzleLimit(root.workspace.puzzleView.puzzleId, "time", checked, timeLimitSpinBox.value)
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            Item {
                                Layout.preferredWidth: 88
                                Layout.preferredHeight: Math.max(timeLimitSpinBox.implicitHeight, timeLimitUnlimited.implicitHeight)

                                SpinBox {
                                    id: timeLimitSpinBox
                                    anchors.fill: parent
                                    visible: root.workspace.puzzleView.hasTimeLimit
                                    editable: true
                                    from: 1
                                    to: 86400
                                    value: root.workspace.puzzleView.timeLimit
                                    onValueModified: root.workspace.setPuzzleLimit(root.workspace.puzzleView.puzzleId, "time", root.workspace.puzzleView.hasTimeLimit, value)
                                }

                                Label {
                                    id: timeLimitUnlimited
                                    anchors.centerIn: parent
                                    visible: !root.workspace.puzzleView.hasTimeLimit
                                    text: qsTr("Unlimited")
                                    color: AppTheme.textSecondary
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            CheckBox {
                                text: qsTr("Solution limit")
                                checked: root.workspace.puzzleView.hasSolutionLimit
                                onClicked: root.workspace.setPuzzleLimit(root.workspace.puzzleView.puzzleId, "solution", checked, solutionLimitSpinBox.value)
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            Item {
                                Layout.preferredWidth: 88
                                Layout.preferredHeight: Math.max(solutionLimitSpinBox.implicitHeight, solutionLimitUnlimited.implicitHeight)

                                SpinBox {
                                    id: solutionLimitSpinBox
                                    anchors.fill: parent
                                    visible: root.workspace.puzzleView.hasSolutionLimit
                                    editable: true
                                    from: 1
                                    to: 10000
                                    value: root.workspace.puzzleView.solutionLimit
                                    onValueModified: root.workspace.setPuzzleLimit(root.workspace.puzzleView.puzzleId, "solution", root.workspace.puzzleView.hasSolutionLimit, value)
                                }

                                Label {
                                    id: solutionLimitUnlimited
                                    anchors.centerIn: parent
                                    visible: !root.workspace.puzzleView.hasSolutionLimit
                                    text: qsTr("Unlimited")
                                    color: AppTheme.textSecondary
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        AppButton {
                            text: qsTr("Solve")
                            onClicked: root.workspace.solvePuzzle(root.workspace.puzzleView.puzzleId)
                        }

                        AppButton {
                            text: qsTr("Stop")
                            onClicked: root.workspace.stopSolver(root.workspace.puzzleView.puzzleId)
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }

                    Label {
                        text: qsTr("Solutions Navigation && Log")
                        color: AppTheme.textSecondary
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        AppButton {
                            text: "<"
                            onClicked: root.workspace.previousPuzzleSolution(root.workspace.puzzleView.puzzleId)
                        }

                        TextField {
                            Layout.preferredWidth: 56
                            text: root.workspace.puzzleView.currentSolutionIndex >= 0 ? String(root.workspace.puzzleView.currentSolutionIndex + 1) : ""
                            horizontalAlignment: TextInput.AlignHCenter
                            validator: IntValidator {
                                bottom: 1
                            }
                            onAccepted: root.workspace.setPuzzleCurrentSolutionIndex(root.workspace.puzzleView.puzzleId, Number(text) - 1)
                        }

                        Label {
                            text: "/ " + root.workspace.puzzleView.solutionCount
                            color: AppTheme.textSecondary
                        }

                        AppButton {
                            text: ">"
                            onClicked: root.workspace.nextPuzzleSolution(root.workspace.puzzleView.puzzleId)
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }

                    ScrollView {
                        id: logScroll
                        Layout.fillWidth: true
                        Layout.preferredHeight: 140
                        clip: true

                        Basic.TextArea {
                            id: logTextArea
                            readOnly: true
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            background: Rectangle {
                                color: AppTheme.surface
                                border.color: AppTheme.border
                                radius: 4
                            }
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: root.workspace.puzzleView

        function onSolvingLogChanged() {
            root.refreshLogText();
        }
    }

    Component.onCompleted: root.refreshLogText()

    Timer {
        interval: 16
        repeat: true
        running: root.isDraggingPuzzle && root.draggedRecord !== null

        onTriggered: {
            let item = root.draggedRecord;
            let maxContentY = Math.max(0, puzzleList.contentHeight - puzzleList.height);
            let maxItemY = Math.max(0, puzzleList.contentHeight - item.height);
            let itemTopInView = item.y - puzzleList.contentY;
            let itemBottomInView = itemTopInView + item.height;
            let delta = 0;

            if (itemTopInView < root.dragAutoScrollMargin) {
                delta = -Math.min(root.dragAutoScrollStep, puzzleList.contentY);
            } else if (itemBottomInView > puzzleList.height - root.dragAutoScrollMargin) {
                delta = Math.min(root.dragAutoScrollStep, maxContentY - puzzleList.contentY);
            }

            if (delta === 0)
                return;

            puzzleList.contentY += delta;
            item.y = Math.max(0, Math.min(maxItemY, item.y + delta));
            root.updateDropIndex(item);
        }
    }

    Connections {
        target: root.workspace.puzzleView

        function onRequestPuzzleFocus(puzzleId) {
            root.focusPuzzleRecord(puzzleId);
        }
    }
}
