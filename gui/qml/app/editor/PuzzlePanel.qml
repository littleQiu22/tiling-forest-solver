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

    function statusColor(solveStatus) {
        switch (solveStatus) {
        case "Infeasible":
            return AppTheme.danger;
        case "TimeLimit":
        case "SolutionLimit":
            return AppTheme.warning;
        case "Solved":
            return AppTheme.success;
        case "Solving":
            return AppTheme.primary;
        default:
            return AppTheme.primary;
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

    function deletePuzzle(puzzleId) {
        let queryHeavyReason = true;
        let heavyReason = root.workspace.deletePuzzle(puzzleId, queryHeavyReason);
        if (!!heavyReason) {
            Services.confirm(() => root.workspace.deletePuzzle(puzzleId), heavyReason, qsTr("Delete Puzzle?"), qsTr("Delete"));
        } else {
            root.workspace.deletePuzzle(puzzleId);
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        Label {
            Layout.fillWidth: true
            text: qsTr("Puzzles")
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

            delegate: Rectangle {
                id: puzzleRecord
                required property string puzzleId
                required property string name
                required property string solveStatus
                required property bool isGeometryStaled

                width: puzzleList.width
                height: 36
                radius: 4
                color: root.workspace.puzzleView.puzzleId === puzzleId ? AppTheme.surfaceVariant : "transparent"
                border.color: root.workspace.puzzleView.puzzleId === puzzleId ? AppTheme.primary : AppTheme.border

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 6

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

                        Item {
                            id: statusRing
                            anchors.fill: parent
                            rotation: puzzleRecord.solveStatus === "Solving" ? phase : 0
                            property real phase: 0

                            Rectangle {
                                visible: puzzleRecord.solveStatus === "Solving"
                                x: Math.round(parent.width / 2 - width / 2)
                                y: 1
                                width: 5
                                height: 5
                                radius: 2.5
                                color: root.statusColor(puzzleRecord.solveStatus)
                            }

                            NumberAnimation on phase {
                                from: 0
                                to: 360
                                duration: 900
                                loops: Animation.Infinite
                                running: puzzleRecord.solveStatus === "Solving"
                            }
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
                        text: puzzleRecord.name
                        color: AppTheme.textPrimary
                        elide: Text.ElideRight
                    }
                    //

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

            ColumnLayout {
                width: detailsScroll.availableWidth
                spacing: 10

                Label {
                    Layout.fillWidth: true
                    text: root.puzzleSummary()
                    color: root.workspace.puzzleView.isGeometryStaled ? AppTheme.warning : AppTheme.textPrimary
                    font.bold: true
                    elide: Text.ElideRight
                }

                ColumnLayout {
                    id: details
                    Layout.fillWidth: true
                    visible: root.workspace.puzzleView.hasPuzzle
                    spacing: 10

                    Label {
                        text: qsTr("Tile Pool")
                        color: AppTheme.textSecondary
                        font.bold: true
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

                    Label {
                        text: qsTr("Objectives")
                        color: AppTheme.textSecondary
                        font.bold: true
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

                    Label {
                        text: qsTr("Constraints")
                        color: AppTheme.textSecondary
                        font.bold: true
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

                    Label {
                        text: qsTr("Solving Configuration && Control")
                        color: AppTheme.textSecondary
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Label {
                            text: qsTr("Time(s)")
                            color: AppTheme.textSecondary
                        }

                        SpinBox {
                            Layout.preferredWidth: 88
                            editable: true
                            from: 0
                            to: 86400
                            value: root.workspace.puzzleView.timeLimit
                            onValueModified: root.workspace.setPuzzleTimeLimit(root.workspace.puzzleView.puzzleId, value)
                        }

                        Label {
                            text: qsTr("Solutions")
                            color: AppTheme.textSecondary
                        }

                        SpinBox {
                            Layout.preferredWidth: 88
                            editable: true
                            from: 0
                            to: 10000
                            value: root.workspace.puzzleView.solutionLimit
                            onValueModified: root.workspace.setPuzzleSolutionLimit(root.workspace.puzzleView.puzzleId, value)
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
                        Layout.fillWidth: true
                        Layout.preferredHeight: 140
                        clip: true

                        Basic.TextArea {
                            text: root.workspace.puzzleView.solvingLog
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
}
