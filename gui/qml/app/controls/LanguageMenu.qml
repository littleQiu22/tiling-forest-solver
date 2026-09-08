import QtQuick
import QtQuick.Controls

import app.global
import app.controls

AppMenu {
    id: root
    title: qsTr("Language")
    width: 160

    function selectLanguage(languageCode) {
        Language.setLanguage(languageCode);
        AppSettings.languageCode = Language.languageCode;
    }

    AppMenuItem {
        text: qsTr("English")
        checkable: true
        checked: Language.languageCode === "en"
        onTriggered: root.selectLanguage("en")
    }

    AppMenuItem {
        text: qsTr("中文")
        checkable: true
        checked: Language.languageCode === "zh_CN"
        onTriggered: root.selectLanguage("zh_CN")
    }
}
