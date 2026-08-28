pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
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

    function deletePuzzle(puzzleId) {
        let reason = root.workspace.deletePuzzle(puzzleId, true);
        if (!!reason) {
            Services.confirm(
                () => root.workspace.deletePuzzle(puzzleId),
                reason,
                qsTr("Delete Puzzle?"),
                qsTr("Delete")
            );
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
            Layout.preferredHeight: Math.min(220, Math.max(96, contentHeight))
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

                    Canvas {
                        id: ring
                        Layout.preferredWidth: 22
                        Layout.preferredHeight: 22
                        property real phase: 0

                        onPaint: {
                            let ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            ctx.lineWidth = 3;
                            ctx.strokeStyle = root.statusColor(puzzleRecord.solveStatus);
                            ctx.beginPath();
                            if (puzzleRecord.solveStatus === "Solving") {
                                ctx.arc(width / 2, height / 2, 8, phase, phase + Math.PI * 1.35);
                            } else {
                                ctx.arc(width / 2, height / 2, 8, 0, Math.PI * 2);
                            }
                            ctx.stroke();
                        }

                        NumberAnimation on phase {
                            from: 0
                            to: Math.PI * 2
                            duration: 900
                            loops: Animation.Infinite
                            running: puzzleRecord.solveStatus === "Solving"
                        }

                        onPhaseChanged: requestPaint()
                        onVisibleChanged: requestPaint()
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

                    AppButton {
                        text: qsTr("Rename")
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
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                width: Math.max(parent.width, implicitWidth)
                spacing: 10

                Label {
                    Layout.fillWidth: true
                    text: root.workspace.puzzleView.hasPuzzle ? root.workspace.puzzleView.name : qsTr("No puzzle selected")
                    color: AppTheme.textPrimary
                    font.bold: true
                    elide: Text.ElideRight
                }

                Label {
                    Layout.fillWidth: true
                    visible: root.workspace.puzzleView.hasPuzzle
                    text: qsTr("Status: ") + root.workspace.puzzleView.solveStatus + (root.workspace.puzzleView.isGeometryStaled ? qsTr("  Geometry stale") : "")
                    color: root.workspace.puzzleView.isGeometryStaled ? AppTheme.warning : AppTheme.textSecondary
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                Label {
                    visible: root.workspace.puzzleView.hasPuzzle
                    text: qsTr("Tile Pool")
                    color: AppTheme.textSecondary
                    font.bold: true
                }

                Flow {
                    Layout.fillWidth: true
                    visible: root.workspace.puzzleView.hasPuzzle
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
                    visible: root.workspace.puzzleView.hasPuzzle
                    text: qsTr("Objectives")
                    color: AppTheme.textSecondary
                    font.bold: true
                }

                Repeater {
                    model: root.workspace.puzzleView.objectiveItems

                    delegate: RowLayout {
                        required property var modelData
                        visible: root.workspace.puzzleView.hasPuzzle
                        width: parent.width

                        CheckBox {
                            checked: modelData.enabled
                            text: modelData.label
                            onToggled: root.workspace.setPuzzleObjectiveEnabled(root.workspace.puzzleView.puzzleId, modelData.key, checked)
                        }
                        Item {
                            Layout.fillWidth: true
                        }
                        AppButton {
                            text: "<"
                            onClicked: root.workspace.movePuzzleObjective(root.workspace.puzzleView.puzzleId, modelData.key, -1)
                        }
                        AppButton {
                            text: ">"
                            onClicked: root.workspace.movePuzzleObjective(root.workspace.puzzleView.puzzleId, modelData.key, 1)
                        }
                    }
                }

                Label {
                    visible: root.workspace.puzzleView.hasPuzzle
                    text: qsTr("Constraints")
                    color: AppTheme.textSecondary
                    font.bold: true
                }

                Repeater {
                    model: root.workspace.puzzleView.constraintItems

                    delegate: CheckBox {
                        required property var modelData
                        visible: root.workspace.puzzleView.hasPuzzle
                        checked: modelData.enabled
                        text: modelData.label
                        onToggled: root.workspace.setPuzzleConstraintEnabled(root.workspace.puzzleView.puzzleId, modelData.key, checked)
                    }
                }

                RowLayout {
                    visible: root.workspace.puzzleView.hasPuzzle
                    Label {
                        text: qsTr("Time")
                        color: AppTheme.textSecondary
                    }
                    SpinBox {
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
                        from: 0
                        to: 10000
                        value: root.workspace.puzzleView.solutionLimit
                        onValueModified: root.workspace.setPuzzleSolutionLimit(root.workspace.puzzleView.puzzleId, value)
                    }
                }

                RowLayout {
                    visible: root.workspace.puzzleView.hasPuzzle

                    AppButton {
                        text: qsTr("Solve")
                        onClicked: root.workspace.solvePuzzle(root.workspace.puzzleView.puzzleId)
                    }
                    AppButton {
                        text: qsTr("Stop")
                        onClicked: root.workspace.stopSolver(root.workspace.puzzleView.puzzleId)
                    }
                }

                RowLayout {
                    visible: root.workspace.puzzleView.hasPuzzle

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
                }

                TextArea {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 140
                    visible: root.workspace.puzzleView.hasPuzzle
                    text: root.workspace.puzzleView.solvingLog
                    readOnly: true
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }
            }
        }
    }
}
