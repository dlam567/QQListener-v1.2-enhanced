import asyncio
import hashlib
import sys

from loguru import logger
from PySide6.QtCore import QThread, Signal

from src.core.settings import get_settings
from src.core.signals import get_signals
from src.utils.message_processor import MessageProcessor


class NotificationWorker(QThread):
    """通知监控工作线程"""

    notification_ready = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = get_settings()
        self.signals = get_signals()
        self.processor = MessageProcessor()
        self._running = True
        self._is_win11 = sys.getwindowsversion().build >= 22000

    def run(self):
        """线程主循环"""
        try:
            if self.settings.uia_mode:
                asyncio.run(self._run_uia_mode())
            else:
                asyncio.run(self._run_winsdk_mode())
        except Exception:
            logger.exception("工作线程异常")

    def stop(self):
        """停止工作线程"""
        self._running = False
        self.wait(5000)

    async def _run_uia_mode(self):
        """UIA模式运行"""
        import uiautomation as auto

        while self._running:
            try:
                current_found_keys: set[str] = set()
                toasts = self._get_uia_toasts(auto)

                for texts in toasts:
                    if not texts or not isinstance(texts, list):
                        continue

                    norm = [" ".join(t.split()) for t in texts if t and isinstance(t, str)]
                    if not norm:
                        continue

                    key = hashlib.md5("|".join(norm).encode("utf-8")).hexdigest()
                    current_found_keys.add(key)

                    result = self.processor.process_notification(texts)
                    if result and isinstance(result, dict):
                        self.notification_ready.emit(result)

                self.processor.update_active_toasts(current_found_keys)

            except Exception:
                logger.exception("UIA异常")

            await asyncio.sleep(self.settings.scan_interval)

    def _get_uia_toasts(self, auto) -> list[list[str]]:
        """获取UIA模式下的通知"""
        if not auto:
            return []

        try:
            desktop = auto.GetRootControl()
        except Exception:
            return []

        texts_list: list[list[str]] = []

        if not self._is_win11:
            try:
                for pane in desktop.GetChildren():
                    if not pane or pane.ClassName != "Windows.UI.Core.CoreWindow":
                        continue
                    for win in pane.GetChildren():
                        if not win or win.ControlTypeName != "WindowControl":
                            continue
                        try:
                            childs = win.GetChildren()
                            texts = [
                                c.Name
                                for c in childs
                                if c and c.ControlTypeName == "TextControl" and c.Name
                            ]
                            if len(texts) >= 2:
                                texts_list.append(texts)
                        except Exception:
                            continue
            except Exception:
                logger.exception("获取UIA通知失败")
        else:
            try:
                container = auto.WindowControl(
                    searchDepth=1,
                    ClassName="Windows.UI.Core.CoreWindow",
                    Name="新通知",
                )
                if container and container.Exists(0):
                    for toast, _ in auto.WalkControl(container, maxDepth=3):
                        if not toast or toast.ClassName != "FlexibleToastView":
                            continue
                        try:
                            childs = toast.GetChildren()
                            texts = [
                                c.Name
                                for c in childs
                                if c
                                and c.ControlTypeName == "TextControl"
                                and c.Name
                                and len(c.Name) > 1
                            ]
                            if len(texts) >= 2:
                                texts_list.append(texts)
                        except Exception:
                            continue
            except Exception:
                logger.exception("获取Win11 UIA通知失败")

        return texts_list

    async def _run_winsdk_mode(self):
        """WinSDK模式运行"""
        try:
            import winsdk.windows.ui.notifications as notifications
            import winsdk.windows.ui.notifications.management as mgmt
        except ImportError:
            logger.error("WinSDK未安装，无法使用WinSDK模式")
            return

        try:
            listener = mgmt.UserNotificationListener.current
            if not listener:
                logger.error("无法获取通知监听器")
                return

            status = await listener.request_access_async()

            if status != mgmt.UserNotificationListenerAccessStatus.ALLOWED:
                logger.error("未获得通知访问权限")
                return

            known_ids: set[int] = set()
            try:
                initial_notifs = await listener.get_notifications_async(
                    notifications.NotificationKinds.TOAST
                )
                if initial_notifs:
                    known_ids = {n.id for n in initial_notifs if n and hasattr(n, "id")}
            except Exception:
                logger.exception("获取初始通知失败")

            while self._running:
                try:
                    notifs = await listener.get_notifications_async(
                        notifications.NotificationKinds.TOAST
                    )

                    if not notifs:
                        await asyncio.sleep(self.settings.scan_interval)
                        continue

                    current_ids = {n.id for n in notifs if n and hasattr(n, "id")}

                    for n in notifs:
                        if not n or not hasattr(n, "id"):
                            continue

                        if n.id in known_ids:
                            continue

                        try:
                            if self.settings.qq_only:
                                app_name = ""
                                try:
                                    if n.app_info and n.app_info.display_info:
                                        app_name = n.app_info.display_info.display_name
                                except Exception:
                                    pass
                                if app_name != "QQ":
                                    known_ids.add(n.id)
                                    continue

                            if not n.notification:
                                known_ids.add(n.id)
                                continue

                            visual = n.notification.visual
                            if not visual:
                                known_ids.add(n.id)
                                continue

                            texts = []
                            try:
                                bindings = visual.bindings
                                if bindings:
                                    for b in bindings:
                                        if b:
                                            text_elements = b.get_text_elements()
                                            if text_elements:
                                                texts.extend(
                                                    [
                                                        t.text.strip()
                                                        for t in text_elements
                                                        if t and t.text
                                                    ]
                                                )
                            except Exception:
                                pass

                            if texts:
                                result = self.processor.process_notification(texts)
                                if result and isinstance(result, dict):
                                    self.notification_ready.emit(result)

                        except Exception:
                            logger.exception("处理通知异常")

                        known_ids.add(n.id)

                    known_ids &= current_ids

                except Exception:
                    logger.exception("WinSDK异常")

                await asyncio.sleep(self.settings.scan_interval)

        except Exception:
            logger.exception("WinSDK模式初始化失败")
