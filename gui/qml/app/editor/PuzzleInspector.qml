pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts

import app
import app.controls
import app.global
import app.models

ScrollView {
    id: root

    required property Workspace workspace

    clip: true
    padding: 4

    function puzzleSummary() {
        if (!root.workspace.puzzleView.hasPuzzle)
            return qsTr("No puzzle selected");

        let parts = [root.workspace.puzzleView.name, root.solveStatusLabel(root.workspace.puzzleView.solveStatus)];
        if (root.workspace.puzzleView.isGeometryStaled)
            parts.push(qsTr("Stale"));
        return parts.join(" | ");
    }

    function solveStatusLabel(solveStatus) {
        switch (solveStatus) {
        case "Solved":
            return qsTr("Solved");
        case "Solving":
            return qsTr("Solving");
        case "TimeLimit":
            return qsTr("Time limit");
        case "SolutionLimit":
            return qsTr("Solution limit");
        case "Infeasible":
            return qsTr("Infeasible");
        case "InternalError":
            return qsTr("Internal error");
        case "Interrupted":
            return qsTr("Interrupted");
        default:
            return qsTr("Unsolved");
        }
    }

    function objectiveLabel(key) {
        switch (key) {
        case "MIN_UNEXPLORED":
            return qsTr("Min unexplored");
        case "MAX_DENSITY":
            return qsTr("Max density");
        case "MAX_CONNECTIVITY":
            return qsTr("Max connectivity");
        default:
            return key;
        }
    }

    function constraintLabel(key) {
        switch (key) {
        case "FIGURE_ALIGNED":
            return qsTr("Figure aligned");
        case "ROAD_MUST_EXIT":
            return qsTr("Road must exit");
        case "STUMP_PAIRED":
            return qsTr("Stump paired");
        case "ROAD_BLOOM":
            return qsTr("Road bloom");
        default:
            return key;
        }
    }

    function rebuildPuzzle() {
        let message = root.workspace.rebuildPuzzle(root.workspace.puzzleView.puzzleId);
        if (!!message)
            Services.alert(message);
    }

    function refreshLogText() {
        const flick = logScroll.contentItem;
        const canScroll = flick && typeof flick.contentY === "number";
        const oldContentY = canScroll ? flick.contentY : 0;
        const wasAtBottom = canScroll && flick.contentY + flick.height >= flick.contentHeight - 4;

        logTextArea.text = root.workspace.puzzleView.solvingLog;
        root.restoreLogScroll(wasAtBottom, oldContentY);
    }

    function restoreLogScroll(wasAtBottom, oldContentY) {
        Qt.callLater(() => {
            const currentFlick = logScroll.contentItem;
            if (!currentFlick || typeof currentFlick.contentY !== "number")
                return;

            const maxContentY = Math.max(0, currentFlick.contentHeight - currentFlick.height);
            currentFlick.contentY = wasAtBottom ? maxContentY : Math.min(oldContentY, maxContentY);
            Qt.callLater(() => {
                const finalFlick = logScroll.contentItem;
                if (!finalFlick || typeof finalFlick.contentY !== "number")
                    return;

                const finalMaxContentY = Math.max(0, finalFlick.contentHeight - finalFlick.height);
                finalFlick.contentY = wasAtBottom ? finalMaxContentY : Math.min(finalFlick.contentY, finalMaxContentY);
            });
        });
    }

    ColumnLayout {
        width: root.availableWidth
        spacing: 10

        RowLayout {
            Layout.fillWidth: true

            Label {
                id: summaryLabel

                text: root.puzzleSummary()
                color: summaryHover.hovered ? AppTheme.primary : (root.workspace.puzzleView.hasPuzzle ? PuzzleStyle.resultStatusColor(root.workspace.puzzleView.resultStatus) : AppTheme.textPrimary)
                font.bold: true
                elide: Text.ElideRight

                HoverHandler {
                    id: summaryHover
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                }

                TapHandler {
                    acceptedButtons: Qt.LeftButton
                    onTapped: root.workspace.selectPuzzle(root.workspace.puzzleView.puzzleId)
                }

                Rectangle {
                    visible: root.workspace.puzzleView.hasPuzzle
                    anchors.left: summaryLabel.left
                    anchors.right: summaryLabel.right
                    anchors.top: summaryLabel.bottom
                    anchors.topMargin: 3
                    height: 1
                    color: summaryLabel.color
                }
            }

            Item {
                Layout.fillWidth: true
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
                spacing: 6

                Repeater {
                    model: root.workspace.puzzleView.tilePoolItems

                    delegate: Rectangle {
                        required property var modelData
                        readonly property bool isSelected: modelData.enabled

                        width: 38
                        height: 38
                        radius: 4
                        color: AppTheme.surface
                        border.width: isSelected ? 2 : 1
                        border.color: isSelected ? AppTheme.selectionBorder : AppTheme.border

                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            color: parent.isSelected ? AppTheme.selectionOverlay : (tilePoolHover.hovered ? AppTheme.hoverOverlay : "transparent")
                        }

                        Image {
                            anchors.centerIn: parent
                            width: 30
                            height: 30
                            source: Assets.tileImage(modelData.tile)
                            fillMode: Image.PreserveAspectFit
                        }

                        HoverHandler {
                            id: tilePoolHover
                            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
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
                            text: root.objectiveLabel(modelData.key)
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
                        text: root.constraintLabel(modelData.key)
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

                    width: logScroll.availableWidth
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

    Connections {
        target: root.workspace.puzzleView

        function onSolvingLogChanged() {
            root.refreshLogText();
        }
    }

    Component.onCompleted: root.refreshLogText()
}
