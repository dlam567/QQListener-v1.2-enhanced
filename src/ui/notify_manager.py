from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

from src.core.settings import get_settings
from src.ui.notify_window import NotifyWindow


class NotifyManager(QObject):
    _instance = None
    _initialized = False
    notification_closed = Signal(str)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, parent=None):
        if NotifyManager._initialized:
            return

        super().__init__(parent)
        self.settings = get_settings()
        self._active_notifications: list[NotifyWindow] = []
        NotifyManager._initialized = True

    def show_notification(self, data: dict) -> NotifyWindow:
        win = NotifyWindow(data)

        # 应用阴影效果
        if self.settings.notify_shadow:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(50)
            shadow.setXOffset(0)
            shadow.setYOffset(0)
            shadow.setColor(QColor(0, 0, 0, 200))
            win.bg_widget.setGraphicsEffect(shadow)

        # 添加到活动通知列表
        self._active_notifications.append(win)

        # 连接关闭信号，以便从列表中移除
        win.destroyed.connect(lambda: self._on_notification_closed(win))

        # 显示窗口
        win.show()
        win.setWindowTitle("QQListener - 通知")

        return win

    def _on_notification_closed(self, win: NotifyWindow):
        """通知窗口关闭时的处理"""
        if win in self._active_notifications:
            self._active_notifications.remove(win)

    def close_all_notifications(self):
        """关闭所有活动通知"""
        for win in self._active_notifications[:]:
            win.close()
        self._active_notifications.clear()

    def get_active_count(self) -> int:
        """获取当前活动通知数量"""
        return len(self._active_notifications)


def get_notify_manager() -> NotifyManager:
    """获取通知管理器单例实例"""
    return NotifyManager()
