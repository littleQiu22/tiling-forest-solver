pragma Singleton
import QtQuick

QtObject {
    signal alertRequested(string message)

    function alert(message) {
        alertRequested(message);
    }
}
