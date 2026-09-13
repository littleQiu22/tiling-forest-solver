pragma Singleton
import QtQuick

QtObject {
    function resultStatusColor(resultStatus) {
        switch (resultStatus) {
        case "CompleteSolution":
            return AppTheme.success;
        case "PartialSolution":
            return AppTheme.muted;
        case "Solving":
            return AppTheme.active;
        case "Infeasible":
        case "Error":
            return AppTheme.danger;
        default:
            return AppTheme.warning;
        }
    }
}
