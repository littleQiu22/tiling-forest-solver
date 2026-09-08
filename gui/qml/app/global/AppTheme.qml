pragma Singleton
import QtQuick

QtObject {
    id: root

    // Underlying Background (e.g. window)
    property color background: "#F9FAFB"

    // Surface Background
    property color surface: "#FFFFFF" // e.g. card and pop dialog
    property color surfaceVariant: "#E5E7EB" // e.g. input box

    // ====== Text Color ======
    property color textPrimary: "#111827"
    property color textSecondary: "#6B7280"

    // ====== Border ======
    property color border: "#cdd0d4"
    property color gridLine: "#D1D5DB"

    // ====== Action Color ======
    property color primary: "#3B82F6"
    property color active: "#06B6D4"
    property color success: "#22C55E"
    property color warning: "#F59E0B"
    property color danger: "#EF4444"
    property color muted: "#9CA3AF"

    // ====== Interaction Color ======
    property color hoverOverlay: Qt.rgba(0, 0, 0, 0.05)
    property color pressOverlay: Qt.rgba(0, 0, 0, 0.1)
    property color selectionOverlay: Qt.rgba(0.23, 0.51, 0.96, 0.18)
    property color strongSelectionOverlay: Qt.rgba(0.23, 0.51, 0.96, 0.28)
    property color selectionBorder: primary
}
