pragma Singleton
import QtQuick

QtObject {
    function solveStatusColor(solveStatus) {
        switch (solveStatus) {
        case "Solved":
            return AppTheme.success;
        case "TimeLimit":
        case "SolutionLimit":
            return AppTheme.warning;
        case "Unsolved":
            return AppTheme.primary;
        case "Solving":
            return AppTheme.active;
        default:
            return AppTheme.danger;
        }
    }
}
