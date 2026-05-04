from datetime import datetime, timedelta
from loguru import logger
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QCursor, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from src.core.settings import get_settings
from src.core.time_restriction import get_time_restriction_config


class TrayIcon(QObject):
    """系统托盘图标管理 - Qt实现"""

    show_settings_signal = Signal()
    exit_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = get_settings()
        self._tray_icon: QSystemTrayIcon = None
        self._menu: QMenu = None
        self._tooltip_timer: QTimer = None

    def create(self) -> bool:
        """创建托盘图标"""
        try:
            # 创建托盘图标
            self._tray_icon = QSystemTrayIcon(self)
            self._tray_icon.setIcon(QIcon("icon.ico"))
            self._update_tooltip()

            # 创建右键菜单
            self._menu = QMenu()

            # 设置动作
            settings_action = QAction("设置", self)
            settings_action.triggered.connect(self.show_settings_signal.emit)
            self._menu.addAction(settings_action)

            # 分隔线
            self._menu.addSeparator()

            # 退出动作
            exit_action = QAction("退出", self)
            exit_action.triggered.connect(self.exit_signal.emit)
            self._menu.addAction(exit_action)

            # 连接托盘图标激活信号
            self._tray_icon.activated.connect(self._on_activated)

            # 创建定时器更新提示
            self._tooltip_timer = QTimer(self)
            self._tooltip_timer.timeout.connect(self._update_tooltip)
            self._tooltip_timer.start(5000)  # 每5秒更新一次

            # 显示托盘图标
            self._tray_icon.show()

            return True

        except Exception:
            logger.exception("创建托盘图标失败")
            return False

    def _on_activated(self, reason):
        """托盘图标被激活时的处理"""
        # QSystemTrayIcon.Context 表示右键点击
        if reason == QSystemTrayIcon.Context:
            self._menu.popup(QCursor.pos())

    def _update_tooltip(self):
        """更新托盘图标提示信息"""
        try:
            config = get_time_restriction_config()
            now = datetime.now()
            weekday = now.weekday()  # 0=周一, 6=周日
            # 转换为配置中的格式：1=周一, 7=周日
            config_weekday = weekday + 1
            current_time = now.strftime("%H:%M")

            if not config.enabled:
                self._tray_icon.setToolTip("QQListener\n未启用上课禁用")
                return

            matched_range = self._find_current_range(config, now, config_weekday, current_time)

            if matched_range:
                start_str, end_str = matched_range["time_range"].split("-")
                end_t = datetime.strptime(end_str, "%H:%M").time()
                start_t = datetime.strptime(start_str, "%H:%M").time()

                end_dt = datetime.combine(now.date(), end_t)
                current_t = datetime.strptime(current_time, "%H:%M").time()

                if start_t > end_t:
                    if current_t >= start_t:
                        end_dt += timedelta(days=1)
                else:
                    if end_dt < now:
                        end_dt += timedelta(days=1)

                remain = end_dt - now
                hours = int(remain.total_seconds() // 3600)
                minutes = int((remain.total_seconds() % 3600) // 60)
                tooltip = (
                    f"QQListener\n"
                    f"上课禁用中\n"
                    f"解除时间: {end_str}\n"
                    f"剩余{hours}小时{minutes}分钟"
                )
                self._tray_icon.setToolTip(tooltip)
            else:
                tooltip = "QQListener\n未处于上课禁用状态"
                next_time = self._find_next_restriction(config, now, config_weekday, current_time)
                if next_time:
                    tooltip += f"\n下次禁用: {next_time}"
                self._tray_icon.setToolTip(tooltip)
        except Exception as e:
            logger.exception("更新托盘提示失败")
            self._tray_icon.setToolTip("QQListener")

    def _find_current_range(self, config, now, weekday, current_time):
        """查找当前处于的时间段"""
        try:
            current_t = datetime.strptime(current_time, "%H:%M").time()
        except ValueError:
            return None

        for range_data in config.get_time_ranges():
            if not isinstance(range_data, dict):
                continue

            days = range_data.get("days", "")
            time_range = range_data.get("time_range", "")
            if not days or not time_range:
                continue

            try:
                day_list = [int(d.strip()) for d in days.split(",") if d.strip().isdigit()]
                start_str, end_str = time_range.split("-")
                start_t = datetime.strptime(start_str, "%H:%M").time()
                end_t = datetime.strptime(end_str, "%H:%M").time()
            except ValueError:
                continue

            if start_t <= end_t:
                # 当天时间段：需要当天在days中，且start <= current <= end
                if weekday not in day_list:
                    continue
                if start_t <= current_t <= end_t:
                    return range_data
            else:
                # 跨天时间段：两种情况
                # 1. 当前时间在start之后：需要当天在days中
                # 2. 当前时间在end之前：需要前一天在days中
                if current_t >= start_t and weekday in day_list:
                    return range_data
                if current_t <= end_t:
                    prev_day = (weekday - 1) % 7
                    if prev_day in day_list:
                        return range_data

        return None

    def _find_next_restriction(self, config, now, weekday, current_time):
        """查找下次禁用时间"""
        try:
            ranges = config.get_time_ranges()
            min_diff = None
            next_info = None

            for range_data in ranges:
                if not isinstance(range_data, dict):
                    continue
                days = range_data.get("days", "")
                time_range = range_data.get("time_range", "")
                if not days or not time_range:
                    continue

                day_list = [int(d.strip()) for d in days.split(",") if d.strip().isdigit()]
                try:
                    start_str, end_str = time_range.split("-")
                except ValueError:
                    continue

                # 检查今天及未来几天
                for day_offset in range(8):  # 最多查看未来7天
                    check_weekday = (weekday + day_offset) % 7
                    if check_weekday not in day_list:
                        continue

                    # 计算目标日期
                    target_date = now.date() + timedelta(days=day_offset)
                    target_dt = datetime.combine(target_date, datetime.strptime(start_str, "%H:%M").time())

                    # 如果目标时间已经过去，跳过
                    if target_dt <= now:
                        continue

                    diff = target_dt - now
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        days_str = "今天" if day_offset == 0 else f"{day_offset}天后"
                        next_info = f"{days_str} {start_str}"
                    break  # 找到最早的就跳出

            return next_info
        except Exception:
            logger.exception("查找下次禁用时间失败")
            return None

    def destroy(self):
        """销毁托盘"""
        if self._tooltip_timer:
            self._tooltip_timer.stop()
            self._tooltip_timer = None
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None

    def run_message_loop(self):
        """Qt实现不需要单独的消息循环，此函数保留用于兼容性"""
        pass
