pragma Singleton
import QtQuick
import QtQuick.Window
import QtCore

QtObject {
    id: root

    readonly property int defaultWindowWidth: Math.min(1100, Screen.desktopAvailableWidth)
    readonly property int defaultWindowHeight: Math.min(760, Screen.desktopAvailableHeight)

    property Settings storage: Settings {
        id: settings
        category: "UISettings"

        property var recentFiles: []
        property int windowWidth: root.defaultWindowWidth
        property int windowHeight: root.defaultWindowHeight
        property int windowX: Math.max(0, (Screen.width - windowWidth) / 2)
        property int windowY: Math.max(0, (Screen.height - windowHeight) / 2)
        property bool windowMaximized: false
    }

    property alias windowHeight: settings.windowHeight
    property alias windowWidth: settings.windowWidth
    property alias windowX: settings.windowX
    property alias windowY: settings.windowY
    property alias windowMaximized: settings.windowMaximized
    property alias recentFiles: settings.recentFiles

    function restoreWindow(window) {
        window.width = Math.max(480, Math.min(windowWidth, Screen.desktopAvailableWidth));
        window.height = Math.max(320, Math.min(windowHeight, Screen.desktopAvailableHeight));
        window.x = Math.max(Screen.virtualX, Math.min(windowX, Screen.virtualX + Screen.desktopAvailableWidth - window.width));
        window.y = Math.max(Screen.virtualY, Math.min(windowY, Screen.virtualY + Screen.desktopAvailableHeight - window.height));

        if (windowMaximized) {
            window.showMaximized();
        }
    }

    function saveWindow(window) {
        windowMaximized = window.visibility === Window.Maximized;
        if (windowMaximized)
            return;

        windowWidth = window.width;
        windowHeight = window.height;
        windowX = window.x;
        windowY = window.y;
    }

    function addRecentFile(filePath) {
        if (!filePath)
            return;

        var list = Array.from(recentFiles);

        var index = list.indexOf(filePath);
        if (index !== -1) {
            list.splice(index, 1);
        }
        list.unshift(filePath);

        // Limit record length
        if (list.length > 10) {
            list.pop();
        }

        recentFiles = list;
    }

    function removeRecentFile(filePath) {
        if (!filePath)
            return;

        var list = Array.from(recentFiles);

        var index = list.indexOf(filePath);
        if (index !== -1) {
            list.splice(index, 1);
        }

        recentFiles = list;
    }

    function clearRecentFiles() {
        recentFiles = [];
    }
}
