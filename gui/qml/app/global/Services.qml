pragma Singleton
import QtQuick

QtObject {
    signal alertRequested(string message)
    signal confirmRequested(var confirmAction, string text, string headerText, string confirmText)

    function alert(message) {
        alertRequested(message);
    }

    function confirm(confirmAction, text, headerText, confirmText) {
        confirmRequested(confirmAction, text, headerText ?? "", confirmText ?? "");
    }
}
