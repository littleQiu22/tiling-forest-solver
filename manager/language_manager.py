from __future__ import annotations

from PySide6.QtCore import QObject, Property, QCoreApplication, QLocale, QSettings, QTranslator, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine

from common import getTranslation


class LanguageManager(QObject):
    languageCodeChanged = Signal()

    _supportedLanguageCodes = ("en", "zh_CN")

    def __init__(self, app: QCoreApplication, engine: QQmlApplicationEngine, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self._engine = engine
        self._translator: QTranslator | None = None
        self._languageCode = self._initialLanguageCode()
        self._installTranslator()

    @Property(str, notify=languageCodeChanged)
    def languageCode(self) -> str:
        return self._languageCode

    @Slot(str)
    def setLanguage(self, languageCode: str) -> None:
        languageCode = self._normalizeLanguageCode(languageCode)
        if languageCode == self._languageCode:
            return

        self._languageCode = languageCode
        self._installTranslator()
        self._engine.retranslate()
        self.languageCodeChanged.emit()

    def _initialLanguageCode(self) -> str:
        languageCode = str(QSettings().value("UISettings/languageCode", "") or "")
        if languageCode:
            return self._normalizeLanguageCode(languageCode)
        return self._bestSystemLanguageCode()

    def _bestSystemLanguageCode(self) -> str:
        for language in QLocale.system().uiLanguages():
            languageCode = self._supportedLanguageCode(language)
            if languageCode:
                return languageCode
        return "en"

    def _normalizeLanguageCode(self, languageCode: str) -> str:
        return self._supportedLanguageCode(languageCode) or "en"

    def _supportedLanguageCode(self, languageCode: str) -> str:
        languageCode = languageCode.replace("-", "_")
        if languageCode == "zh":
            return "zh_CN"
        if languageCode in self._supportedLanguageCodes:
            return languageCode
        if languageCode.startswith("zh_"):
            return "zh_CN"
        if languageCode.startswith("en_"):
            return "en"
        return ""

    def _installTranslator(self) -> None:
        if self._translator is not None:
            self._app.removeTranslator(self._translator)
            self._translator = None

        if self._languageCode == "en":
            return

        translator = QTranslator(self)
        if translator.load(getTranslation(f"app_{self._languageCode}.qm")):
            self._app.installTranslator(translator)
            self._translator = translator
