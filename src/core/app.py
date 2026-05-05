import os
import sys
import winreg

import pygame
from loguru import logger

# from loguru import logger
from PySide6.QtCore import QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.core.logging import setup_logging
from src.core.settings import get_settings
from src.core.signals import get_signals
from src.core.worker import NotificationWorker
from src.ui.notify_manager import get_notify_manager
from src.ui.settings_window import SettingsWindow
from src.ui.tray_icon import TrayIcon


class QQListenerApp:
    def __init__(self):
        self.app: QApplication | None = None
        self.settings = get_settings()
        self.signals = get_signals()
        self.worker: NotificationWorker | None = None
        self.settings_window: SettingsWindow | None = None
        self.tray_icon: TrayIcon | None = None
        self.translator: QTranslator | None = None
        self.notify_manager = get_notify_manager()

    def initialize(self) -> bool:
        setup_logging()

        try:
            pygame.mixer.init()
        except Exception:
            logger.exception("初始化音频失败")

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self._sync_auto_start()

        self._load_translator()

        self._connect_signals()

        self.worker = NotificationWorker()
        self.worker.notification_ready.connect(self._on_notification_ready)

        self.tray_icon = TrayIcon()
        self.tray_icon.show_settings_signal.connect(self.show_settings)
        self.tray_icon.exit_signal.connect(self.exit)

        if not self.tray_icon.create():
            logger.error("创建托盘图标失败")

        return True

    def _sync_auto_start(self):
        """同步注册表中的自启状态到配置文件并保存"""
        try:
            settings = get_settings()
            app_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
            app_name = os.path.splitext(os.path.basename(app_path))[0]
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, app_name)
                settings.set("auto_start", True)
            except FileNotFoundError:
                settings.set("auto_start", False)
            winreg.CloseKey(key)
            settings.save()
        except Exception:
            logger.exception("同步自启状态失败")

    def _load_translator(self):
        lang = self.settings.language
        if lang != "zh_CN" and self.app:
            self.translator = QTranslator()
            if self.translator.load(f"translations/{lang}.qm"):
                self.app.installTranslator(self.translator)

    def _connect_signals(self):
        self.signals.show_settings.connect(self.show_settings)
        self.signals.exit_app.connect(self.exit)

    def run(self):
        if not self.initialize():
            logger.error("初始化失败")
            sys.exit(1)

        if self.settings.is_first_run():
            if self.settings_window is None:
                self.settings_window = SettingsWindow()
            QMessageBox.information(
                self.settings_window,
                self.settings_window.tr("你是新来的吧？"),
                self.settings_window.tr(
                    '这个程序配置较为复杂，所以建议你先看了教程再来用喵~\n请点击"关于"选项卡并点击"查看教程"按钮\n第一次保存设置后这条消息将不再出现\n\n\n本程序免费开源，如果你是花钱买的那一定是被骗了！'
                ),
            )
            self.show_settings()
        if self.worker:
            self.worker.start()
        exit_code = self.app.exec() if self.app else 1
        self.cleanup()
        sys.exit(exit_code)

    def show_settings(self):
        if self.settings_window is None or not self.settings_window.isVisible():
            self.settings_window = SettingsWindow()
            self.settings_window.setWindowIcon(QIcon("icon.ico"))
            self.settings_window.show()
        else:
            self.settings_window.raise_()
            self.settings_window.activateWindow()

    def _on_notification_ready(self, data: dict):
        self.push_notification(data)

    def push_notification(self, data: dict):
        try:
            self.notify_manager.show_notification(data)
        except Exception:
            logger.exception("推送通知失败")

    def exit(self):
        self.cleanup()
        if self.app:
            self.app.quit()

    def cleanup(self):
        self.notify_manager.close_all_notifications()
        if self.worker and self.worker.isRunning():
            self.worker.stop()

        if self.tray_icon:
            self.tray_icon.destroy()
        if self.settings_window:
            self.settings_window.close()
            self.settings_window = None


def run_app():
    app = QQListenerApp()
    app.run()
