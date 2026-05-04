from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    show_notification = Signal(dict)

    settings_changed = Signal()
    show_settings = Signal()

    tray_icon_activated = Signal()
    exit_app = Signal()

    message_received = Signal(dict)


app_signals = AppSignals()


def get_signals() -> AppSignals:
    """获取全局信号实例"""
    return app_signals
