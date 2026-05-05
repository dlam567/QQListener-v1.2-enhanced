import os
import subprocess
import sys
import time
import webbrowser
import winreg

import pygame
import pyttsx3
from PySide6.QtCore import QFileSystemWatcher, Qt, QTranslator
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from src.core.settings import get_settings
from src.core.signals import get_signals
from src.core.time_restriction import get_time_restriction_config

DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class SettingsWindow(QWidget):
    """设置窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = get_settings()
        self.signals = get_signals()
        self.time_restriction_config = get_time_restriction_config()

        self._file_watcher = QFileSystemWatcher()
        self._file_watcher.fileChanged.connect(self._on_settings_file_changed)
        self._start_file_watcher()

        self.setWindowTitle(self.tr("QQ Listener - 设置"))
        self.resize(720, 600)
        self.setMinimumSize(680, 500)

        self.data = self.settings.get_all()
        self.init_ui()
        self._init_auto_start_from_registry()
        self._apply_theme()

    def _start_file_watcher(self):
        self._file_watcher.blockSignals(True)
        paths = self._file_watcher.files()
        if paths:
            self._file_watcher.removePaths(paths)
        settings_path = os.path.abspath("setting.json")
        if os.path.exists(settings_path):
            self._file_watcher.addPath(settings_path)
        self._file_watcher.blockSignals(False)

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._create_basic_tab(), self.tr("基本"))
        self.tabs.addTab(self._create_rule_tab(), self.tr("规则"))
        self.tabs.addTab(self._create_timer_tab(), self.tr("定时"))
        self.tabs.addTab(self._create_appearance_tab(), self.tr("外观"))
        self.tabs.addTab(self._create_notify_tab(), self.tr("通知"))
        self.tabs.addTab(self._create_calling_tab(), self.tr("呼叫"))
        self.tabs.addTab(self._create_sound_tab(), self.tr("声音"))
        self.tabs.addTab(self._create_debug_tab(), self.tr("调试"))
        self.tabs.addTab(self._create_about_tab(), self.tr("关于"))

        btn_save = QPushButton(self.tr("保存设置"))
        btn_test = QPushButton(self.tr("测试弹窗"))
        buttom_layout = QHBoxLayout()
        buttom_layout.addWidget(btn_save)
        buttom_layout.addWidget(btn_test)
        btn_save.clicked.connect(self.save_settings)
        btn_test.clicked.connect(self._test_notify)
        layout.addLayout(buttom_layout)

    def _create_basic_tab(self):
        """基本设置标签页"""
        widget = QWidget()
        form = QFormLayout(widget)

        self.scan_interval = QDoubleSpinBox()
        self.scan_interval.setRange(0.1, 10)
        self.scan_interval.setValue(self.data.get("ScanInterval", self.settings.scan_interval))

        self.cooldown = QSpinBox()
        self.cooldown.setRange(0, 60)
        self.cooldown.setValue(self.data.get("Cooldown", self.settings.cooldown))

        self.user_qq = QLineEdit(self.data.get("User_QQ", ""))

        self.tencent_path = QLineEdit(self.data.get("Tencent_Files_Path", ""))
        btn_path = QPushButton(self.tr("浏览"))
        btn_path.clicked.connect(self._select_path)

        path_row = QHBoxLayout()
        path_row.addWidget(self.tencent_path)
        path_row.addWidget(btn_path)

        self.uia_mode = QCheckBox(self.tr("启用 UIA 模式"))
        self.uia_mode.setChecked(self.data.get("UIAMode", self.settings.uia_mode))
        uia_row = QHBoxLayout()
        uia_row.addWidget(self.uia_mode)
        uia_row.addWidget(
            QLabel(self.tr("UI Automation（UIA）模式识别准确率较低，性能较差，非必要勿勾选"))
        )

        self.whereis_tencentfile = QLabel(self.tr("我的聊天信息保存在哪里？"))
        self.whereis_tencentfile.mousePressEvent = lambda event: QMessageBox.information(
            self,
            self.tr("提示"),
            self.tr(
                '打开 QQ 主面板，点击左下角设置，在存储设置选项卡中显示"聊天消息默认保存到..."'
            ),
        )

        self.language_combo = QComboBox()
        self.language_combo.addItems([self.tr("English"), self.tr("日本語"), self.tr("简体中文")])
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

        lang = self.data.get("Language", self.settings.language)
        if lang == "en-US":
            self.language_combo.setCurrentIndex(0)
        elif lang == "ja-JP":
            self.language_combo.setCurrentIndex(1)
        else:
            self.language_combo.setCurrentIndex(2)

        self.auto_start = QCheckBox(self.tr("开机自启动"))
        self.auto_start.setChecked(self.data.get("auto_start", self.settings.auto_start))

        form.addRow(self.tr("扫描间隔 (秒)"), self.scan_interval)
        form.addRow(self.tr("冷却时间 (秒)"), self.cooldown)
        form.addRow(self.tr("QQ 号"), self.user_qq)
        form.addRow(self.tr("聊天信息保存文件夹"), path_row)
        form.addRow(self.whereis_tencentfile)
        form.addRow(uia_row)
        form.addRow(self.tr("界面语言"), self.language_combo)
        form.addRow(self.tr("开机自启动"), self.auto_start)

        return widget

    def _create_rule_tab(self):
        """规则设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel(self.tr("重要人物")))
        self.list_persons = self._create_list(
            self.data.get("Important_Persons", self.settings.important_persons)
        )
        layout.addWidget(self.list_persons)

        layout.addWidget(QLabel(self.tr("重要关键词")))
        self.list_keywords = self._create_list(
            self.data.get("Important_Keywords", self.settings.important_keywords)
        )
        layout.addWidget(self.list_keywords)

        layout.addWidget(QLabel(self.tr("黑名单")))
        self.list_black = self._create_list(self.data.get("BlackList", self.settings.blacklist))
        layout.addWidget(self.list_black)

        self.someone_at_me = QCheckBox(self.tr("当 [有人@我] 时将通知优先级设为最高"))
        self.someone_at_me.setChecked(self.data.get("Someone_At_Me", self.settings.someone_at_me))
        self.qq_only = QCheckBox(self.tr("仅监控 QQ 消息（推荐）"))
        self.qq_only.setChecked(self.data.get("QQ_Only", self.settings.qq_only))
        layout.addWidget(self.someone_at_me)
        layout.addWidget(self.qq_only)

        return widget

    def _create_timer_tab(self):
        """时间限制设置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        enable_layout = QHBoxLayout()
        self.time_restriction_enabled = QCheckBox(self.tr("上课时禁用"))
        self.time_restriction_enabled.setChecked(self.time_restriction_config.enabled)
        enable_label = QLabel("启用后，在设定的时段内将暂停通知推送")
        enable_label.setStyleSheet("color: gray;")
        enable_layout.addWidget(self.time_restriction_enabled)
        enable_layout.addWidget(enable_label)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)

        hint_label = QLabel("💡 提示：双击行可编辑，单击选中行后点击「删除选中」可移除")
        hint_label.setStyleSheet("color: #888; font-size: 12px; padding: 4px 0;")
        layout.addWidget(hint_label)

        self.time_table = QTableWidget()
        self.time_table.setColumnCount(3)
        self.time_table.setHorizontalHeaderLabels(["星期", "时间范围", "操作"])
        self.time_table.horizontalHeader().setStretchLastSection(False)
        self.time_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.time_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.time_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.time_table.setColumnWidth(2, 80)
        self.time_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.time_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.time_table.doubleClicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.time_table)

        self._load_time_ranges()

        btn_layout = QHBoxLayout()
        self.btn_add_time = QPushButton("新增时段")
        self.btn_delete_time = QPushButton("删除选中")
        self.btn_clear_all = QPushButton("清空全部")
        self.btn_refresh_time = QPushButton("刷新时段")
        self.btn_add_time.clicked.connect(self._add_time_range)
        self.btn_delete_time.clicked.connect(self._delete_selected_ranges)
        self.btn_clear_all.clicked.connect(self._clear_all_ranges)
        self.btn_refresh_time.clicked.connect(self._refresh_time_ranges)
        btn_layout.addWidget(self.btn_add_time)
        btn_layout.addWidget(self.btn_delete_time)
        btn_layout.addWidget(self.btn_clear_all)
        btn_layout.addWidget(self.btn_refresh_time)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        return widget

    def _load_time_ranges(self):
        self.time_table.setRowCount(0)
        ranges = self.time_restriction_config.get_time_ranges()
        for r in ranges:
            row = self.time_table.rowCount()
            self.time_table.insertRow(row)

            days_str = r["days"]
            try:
                day_indices = [int(d) for d in days_str.split(",")]
                day_names = [DAY_NAMES[d - 1] for d in day_indices if 1 <= d <= 7]
            except ValueError:
                day_names = [days_str]
            days_item = QTableWidgetItem(", ".join(day_names))
            days_item.setTextAlignment(Qt.AlignCenter)
            self.time_table.setItem(row, 0, days_item)

            time_range_item = QTableWidgetItem(r["time_range"])
            time_range_item.setTextAlignment(Qt.AlignCenter)
            self.time_table.setItem(row, 1, time_range_item)

            btn_delete = QPushButton("删除")
            btn_delete.setProperty("range_id", r["id"])
            btn_delete.clicked.connect(lambda checked, rid=r["id"]: self._delete_range_by_id(rid))
            self.time_table.setCellWidget(row, 2, btn_delete)

    def _on_table_double_clicked(self, index):
        row = index.row()
        if row < 0 or row >= self.time_table.rowCount():
            return
        btn = self.time_table.cellWidget(row, 2)
        if btn:
            range_id = btn.property("range_id")
            if range_id:
                self._edit_time_range(range_id, row)

    def _edit_time_range(self, range_id: str, row: int):
        ranges = self.time_restriction_config.get_time_ranges()
        target = next((r for r in ranges if r["id"] == range_id), None)
        if not target:
            return

        dialog = AddTimeRangeDialog(self, editing=True)
        try:
            days = [int(d) for d in target["days"].split(",")]
            dialog.set_days(days)
        except ValueError:
            pass

        if "-" in target["time_range"]:
            start_str, end_str = target["time_range"].split("-", 1)
            dialog.set_start_time(start_str.strip())
            dialog.set_end_time(end_str.strip())

        if dialog.exec() == QDialog.Accepted:
            days = dialog.get_selected_days()
            if not days:
                QMessageBox.warning(self, "提示", "请至少选择一个星期")
                return
            start = dialog.get_start_time()
            end = dialog.get_end_time()
            self.time_restriction_config.remove_time_range(range_id)
            self.time_restriction_config.add_time_range(days, start, end)
            self._load_time_ranges()

    def _add_time_range(self):
        dialog = AddTimeRangeDialog(self)
        if dialog.exec() == QDialog.Accepted:
            days = dialog.get_selected_days()
            if not days:
                QMessageBox.warning(self, "提示", "请至少选择一个星期")
                return
            start = dialog.get_start_time()
            end = dialog.get_end_time()
            self.time_restriction_config.add_time_range(days, start, end)
            self._load_time_ranges()

    def _delete_selected_ranges(self):
        selected_rows = set()
        for item in self.time_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要删除的时段")
            return
        rows = sorted(selected_rows, reverse=True)
        for row in rows:
            btn = self.time_table.cellWidget(row, 2)
            if btn:
                range_id = btn.property("range_id")
                if range_id:
                    self.time_restriction_config.remove_time_range(range_id)
        self._refresh_time_ranges()

    def _delete_range_by_id(self, range_id: str):
        self.time_restriction_config.remove_time_range(range_id)
        self._refresh_time_ranges()

    def _clear_all_ranges(self):
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清空所有禁用时段吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.time_restriction_config.clear_all_ranges()
            self._refresh_time_ranges()

    def _refresh_time_ranges(self):
        self.time_restriction_config._load()
        self.time_restriction_config.get_time_ranges()
        self._load_time_ranges()

    def _on_settings_file_changed(self, path):
        self._file_watcher.blockSignals(True)
        try:
            if "time_restriction.json" in path:
                self._load_time_ranges()
            else:
                self.data = self.settings.get_all()
                self._load_time_ranges()
        finally:
            self._file_watcher.blockSignals(False)
            self._start_file_watcher()

    def _create_appearance_tab(self):
        """外观设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel(self.tr("设置界面主题")))
        self.theme_setting_combo = QComboBox()
        self.theme_setting_combo.addItems(
            [
                "Fusion",
                "Windows9x",
                "Windows11",
                "dark_amber.xml",
                "dark_blue.xml",
                "dark_cyan.xml",
                "dark_lightgreen.xml",
                "dark_pink.xml",
                "dark_purple.xml",
                "dark_red.xml",
                "dark_teal.xml",
                "dark_yellow.xml",
                "light_amber.xml",
                "light_blue.xml",
                "light_cyan.xml",
                "light_cyan_500.xml",
                "light_lightgreen.xml",
                "light_pink.xml",
                "light_purple.xml",
                "light_red.xml",
                "light_teal.xml",
                "light_yellow.xml",
            ]
        )
        self.theme_setting_combo.setCurrentText(
            self.data.get("Theme_Setting_Combo", self.settings.theme_setting)
        )
        self.theme_setting_combo.currentIndexChanged.connect(self._on_setting_theme_changed)
        layout.addWidget(self.theme_setting_combo)

        layout.addWidget(QLabel(self.tr("通知样式")))
        self.theme_notify_combo = QComboBox()
        self.theme_notify_combo.addItems(["FluentDark", "FluentLight", "Material"])
        self.theme_notify_combo.setCurrentText(
            self.data.get("Theme_Notify_Combo", self.settings.theme_notify)
        )

        self.notify_shadow = QCheckBox(self.tr("通知窗口启用阴影"))
        self.notify_shadow.setChecked(self.data.get("Notify_Shadow", self.settings.notify_shadow))
        self.notify_animation = QCheckBox(self.tr("通知窗口启用动画"))
        self.notify_animation.setChecked(
            self.data.get("Notify_Animation", self.settings.notify_animation)
        )
        self.notify_mask = QCheckBox(self.tr("通知窗口启用遮罩"))
        self.notify_mask.setChecked(self.data.get("Notify_Mask", self.settings.notify_mask))
        self.notify_label = QLineEdit(self.data.get("Notify_Label", self.settings.notify_label))

        # 图标选择
        self.notify_ok_layout = QHBoxLayout()
        self.notify_icon_ok = QLineEdit(self.data.get("icon_ok", self.settings.icon_ok))
        self.notify_ok_select = QPushButton(self.tr("浏览"))
        self.notify_ok_select.clicked.connect(lambda: self._select_file(self.notify_icon_ok))
        self.notify_ok_layout.addWidget(self.notify_icon_ok)
        self.notify_ok_layout.addWidget(self.notify_ok_select)

        self.notify_dismiss_layout = QHBoxLayout()
        self.notify_icon_cancel = QLineEdit(self.data.get("icon_cancel", self.settings.icon_cancel))
        self.notify_cancel_select = QPushButton(self.tr("浏览"))
        self.notify_cancel_select.clicked.connect(
            lambda: self._select_file(self.notify_icon_cancel)
        )
        self.notify_dismiss_layout.addWidget(self.notify_icon_cancel)
        self.notify_dismiss_layout.addWidget(self.notify_cancel_select)

        # 字体选择
        self.notify_title_layout = QHBoxLayout()
        self.notify_title_font = QLineEdit(
            self.data.get("Notify_Title_Font", self.settings.notify_title_font)
        )
        self.notify_title_select = QPushButton(self.tr("浏览"))
        self.notify_title_select.clicked.connect(lambda: self._select_file(self.notify_title_font))
        self.notify_title_layout.addWidget(self.notify_title_font)
        self.notify_title_layout.addWidget(self.notify_title_select)

        self.notify_message_layout = QHBoxLayout()
        self.notify_message_font = QLineEdit(
            self.data.get("Notify_Message_Font", self.settings.notify_message_font)
        )
        self.notify_message_select = QPushButton(self.tr("浏览"))
        self.notify_message_select.clicked.connect(
            lambda: self._select_file(self.notify_message_font)
        )
        self.notify_message_layout.addWidget(self.notify_message_font)
        self.notify_message_layout.addWidget(self.notify_message_select)

        # QSS覆写
        self.override_layout = QHBoxLayout()
        self.override = QCheckBox(self.tr("覆写通知样式表"))
        self.override.setChecked(self.data.get("Override_qss", self.settings.override_qss))
        self.override_layout.addWidget(self.override)
        self.override_qss = QLineEdit(
            self.data.get("Override_Path", self.settings.override_qss_path)
        )
        self.override_select = QPushButton(self.tr("浏览"))
        self.override_select.clicked.connect(lambda: self._select_file(self.override_qss))
        self.override_layout.addWidget(self.override_qss)
        self.override_layout.addWidget(self.override_select)

        layout.addWidget(self.notify_shadow)
        layout.addWidget(self.notify_animation)
        layout.addWidget(self.notify_mask)
        layout.addWidget(self.theme_notify_combo)
        layout.addWidget(QLabel(self.tr("通知下方显示文本（可留空）")))
        layout.addWidget(self.notify_label)
        layout.addWidget(QLabel(self.tr("通知收到按钮图标")))
        layout.addLayout(self.notify_ok_layout)
        layout.addWidget(QLabel(self.tr("通知关闭按钮图标")))
        layout.addLayout(self.notify_dismiss_layout)
        layout.addWidget(QLabel(self.tr("通知标题字体（TTF 文件）")))
        layout.addLayout(self.notify_title_layout)
        layout.addWidget(QLabel(self.tr("通知内容字体（TTF 文件）")))
        layout.addLayout(self.notify_message_layout)
        layout.addLayout(self.override_layout)
        layout.addStretch()

        return widget

    def _create_notify_tab(self):
        """通知设置标签页"""
        widget = QWidget()
        form = QFormLayout(widget)

        self.auto_thumb = QCheckBox(self.tr("当有人发送[图片]自动显示缩略图（不稳定）"))
        self.auto_thumb.setChecked(self.data.get("Auto_Show_Thumb", self.settings.auto_show_thumb))

        self.always_on_top = QCheckBox(self.tr("通知始终置顶"))
        self.always_on_top.setChecked(self.data.get("Always_On_Top", self.settings.always_on_top))

        self.max_wait = QSpinBox()
        self.max_wait.setRange(1, 20)
        self.max_wait.setValue(
            self.data.get("Max_Wait_Thumb_Time", self.settings.max_wait_thumb_time)
        )

        self.duration_everyone = QSpinBox()
        self.duration_everyone.setRange(1000, 20000)
        self.duration_everyone.setValue(
            self.data.get("Duration_Everyone", self.settings.duration_everyone)
        )

        self.duration_important = QSpinBox()
        self.duration_important.setRange(1000, 30000)
        self.duration_important.setValue(
            self.data.get("Duration_Important", self.settings.duration_important)
        )

        self.tts = QCheckBox(self.tr("全局 TTS（语音播报） 开关"))
        self.tts.setChecked(self.data.get("TTS", self.settings.tts_enabled))
        self.tts.checkStateChanged.connect(self._on_tts_changed)

        self.edge_tts = QCheckBox(self.tr("使用新版 EdgeTTS"))
        self.edge_tts.setChecked(self.data.get("Edge_TTS", self.settings.edge_tts_enabled))

        self.edge_voice = QComboBox()
        self.edge_voice.setEditable(True)
        voices = [
            "zh-CN-XiaoxiaoNeural",
            "zh-CN-YunxiNeural",
            "zh-CN-YunjianNeural",
            "ja-JP-NanamiNeural",
            "ja-JP-KeitaNeural",
            "en-US-JennyNeural",
        ]
        self.edge_voice.addItems(voices)
        current_voice = self.data.get("Edge_Voice", self.settings.edge_voice)
        if current_voice not in voices:
            self.edge_voice.addItem(current_voice)
        self.edge_voice.setCurrentText(current_voice)
        self.edge_voice.setEnabled(self.edge_tts.isChecked())

        self.edge_rate = QSlider(Qt.Horizontal)
        self.edge_rate.setRange(-100, 100)
        rate_str = self.data.get("Edge_Rate", self.settings.edge_rate)
        rate_value = int(rate_str.replace("%", "").replace("+", ""))
        self.edge_rate.setValue(rate_value)
        self.edge_rate.setEnabled(self.edge_tts.isChecked())

        self.edge_pitch = QSlider(Qt.Horizontal)
        self.edge_pitch.setRange(-100, 100)
        pitch_str = self.data.get("Edge_Pitch", self.settings.edge_pitch)
        pitch_value = int(pitch_str.replace("Hz", "").replace("+", ""))
        self.edge_pitch.setValue(pitch_value)
        self.edge_pitch.setEnabled(self.edge_tts.isChecked())

        self.edge_volume = QSlider(Qt.Horizontal)
        self.edge_volume.setRange(-100, 100)
        vol_str = self.data.get("Edge_Volume", self.settings.edge_volume)
        vol_value = int(vol_str.replace("%", "").replace("+", ""))
        self.edge_volume.setValue(vol_value)
        self.edge_volume.setEnabled(self.edge_tts.isChecked())

        self.edge_test_text = QLineEdit(self.tr("你好呀，这里是 EdgeTTS 酱哦~"))
        self.edge_test_layout = QHBoxLayout()
        self.edge_test_btn = QPushButton(self.tr("试听"))
        self.edge_test_btn.clicked.connect(self._on_edge_test)
        self.edge_test_layout.addWidget(self.edge_test_text)
        self.edge_test_layout.addWidget(self.edge_test_btn)
        self.edge_tts_warning = QLabel(
            self.tr(
                "EdgeTTS 基于神经网络，需要联网，但可自定义效果，若不勾选使用系统自带 TTS（已知问题：EdgeTTS 音调和语速设为负数可能会报错，也不是所有系统支持EdgeTTS，若无声音请取消勾选此复选框）"
            )
        )
        self.edge_tts_warning.setWordWrap(True)
        form.addRow(self.auto_thumb)
        form.addRow(self.always_on_top)
        form.addRow(self.tr("最大等待缩略图时间(s)"), self.max_wait)
        form.addRow(self.tr("普通通知时长(ms)"), self.duration_everyone)
        form.addRow(self.tr("重要通知时长(ms)"), self.duration_important)
        form.addRow(self.tts)
        form.addRow(self.edge_tts_warning)
        form.addRow(self.tr("EdgeTTS 音色"), self.edge_voice)
        form.addRow(self.tr("EdgeTTS 语速"), self.edge_rate)
        form.addRow(self.tr("EdgeTTS 音高"), self.edge_pitch)
        form.addRow(self.tr("EdgeTTS 音量"), self.edge_volume)
        form.addRow(self.tr("测试 TTS"), self.edge_test_layout)

        return widget

    def _create_calling_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.calling = QCheckBox(self.tr("允许老师呼叫"))
        self.calling.setChecked(self.data.get("Calling", self.settings.calling_enabled))
        self.calling_keyword = QLineEdit(
            self.data.get("Calling_Keyword", self.settings.calling_keyword)
        )
        self.calling_during = QSpinBox()
        self.calling_during.setRange(0, 999999)
        self.calling_during.setValue(
            self.data.get("Calling_Duration", self.settings.calling_duration)
        )
        self.calling_anim = QCheckBox(self.tr("呼叫启用动画"))
        self.calling_anim.setChecked(
            self.data.get("Calling_Animation", self.settings.calling_animation)
        )
        self.calling_bpm = QSpinBox()
        self.calling_bpm.setRange(0, 1000)
        self.calling_bpm.setValue(self.data.get("Calling_BPM", self.settings.calling_bpm))

        self.calling_hint = QLabel(
            self.tr(
                "当老师按一定格式（例如 呼叫XXX，来办公室搬下作业）呼叫，弹出窗口将持续更长时间，并且循环播放铃声和夸张的动画效果直到有人响应。使用本功能前请先和老师约定好呼叫关键词（只能设置一个）"
            )
        )
        self.calling_hint.setWordWrap(True)

        form.addRow(self.calling_hint)
        form.addRow(self.calling)
        form.addRow(self.tr("呼叫关键词"), self.calling_keyword)
        form.addRow(self.tr("呼叫窗口弹出时间(ms)"), self.calling_during)
        form.addRow(self.calling_anim)
        form.addRow(self.tr("呼叫动画 BPM"), self.calling_bpm)

        return widget

    def _create_sound_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.sound_normal = QLineEdit(
            self.data.get("Sound_Effect_Normal", self.settings.sound_normal)
        )
        btn1 = QPushButton(self.tr("浏览"))
        btn1.clicked.connect(lambda: self._select_file(self.sound_normal))
        btn3 = QPushButton(self.tr("试听"))
        btn3.clicked.connect(lambda: self._test_sound(self.sound_normal))

        row1 = QHBoxLayout()
        row1.addWidget(self.sound_normal)
        row1.addWidget(btn1)
        row1.addWidget(btn3)

        self.sound_important = QLineEdit(
            self.data.get("Sound_Effect_Important", self.settings.sound_important)
        )
        btn2 = QPushButton(self.tr("浏览"))
        btn2.clicked.connect(lambda: self._select_file(self.sound_important))
        btn4 = QPushButton(self.tr("试听"))
        btn4.clicked.connect(lambda: self._test_sound(self.sound_important))

        row2 = QHBoxLayout()
        row2.addWidget(self.sound_important)
        row2.addWidget(btn2)
        row2.addWidget(btn4)

        self.sound_calling = QLineEdit(self.data.get("Sound_Calling", self.settings.sound_calling))
        btn5 = QPushButton(self.tr("浏览"))
        btn5.clicked.connect(lambda: self._select_file(self.sound_calling))
        btn6 = QPushButton(self.tr("试听"))
        btn6.clicked.connect(lambda: self._test_sound(self.sound_calling))

        row3 = QHBoxLayout()
        row3.addWidget(self.sound_calling)
        row3.addWidget(btn5)
        row3.addWidget(btn6)

        form.addRow(self.tr("普通提示音"), row1)
        form.addRow(self.tr("重要提示音"), row2)
        form.addRow(self.tr("呼叫提示音"), row3)

        return widget

    def _create_debug_tab(self):
        container = QWidget()
        stack = QStackedLayout(container)
        content = QWidget()
        form = QFormLayout(content)

        self.mainsdk_debug = QPushButton(self.tr("mainsdk活着吗？"))
        self.mainsdk_debug.clicked.connect(lambda: self._test_exe("mainsdk"))
        self.kill_mainsdk = QPushButton(self.tr("杀死mainsdk"))
        self.kill_mainsdk.clicked.connect(lambda: os.system("taskkill /f /im mainsdk.exe"))
        self.run_mainsdk = QPushButton(self.tr("运行mainsdk"))
        self.run_mainsdk.clicked.connect(lambda: subprocess.Popen(["mainsdk.exe"]))

        self.debug_hint = QLabel(
            self.tr(
                '鉴于现行版本后台主进程工作不稳定，且托盘图标容易丢失，若发现异常建议先杀死mainsdk，然后打开安装目录手动启动而非点击"运行mainsdk"\n注意：鉴于实现逻辑更改，此页面选项已弃用'
            )
        )
        self.debug_hint.setWordWrap(True)

        self.mainsdk_layout = QHBoxLayout()
        self.mainsdk_layout.addWidget(self.mainsdk_debug)
        self.mainsdk_layout.addWidget(self.kill_mainsdk)
        self.mainsdk_layout.addWidget(self.run_mainsdk)
        form.addRow(self.mainsdk_layout)
        form.addRow(self.debug_hint)
        stack.addWidget(content)

        overlay = QWidget()
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)

        pix = QPixmap("asset/disable.png")
        img_label = QLabel()
        img_label.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        overlay_layout.addWidget(img_label, alignment=Qt.AlignCenter)
        tip = QLabel(self.tr("非开发者请勿随意操作调试页面的内容"))
        overlay_layout.addWidget(tip, alignment=Qt.AlignCenter)

        unlock_btn = QPushButton(self.tr("显示调试控件"))
        unlock_btn.clicked.connect(lambda: stack.setCurrentWidget(content))
        overlay_layout.addWidget(unlock_btn, alignment=Qt.AlignCenter)

        stack.addWidget(overlay)
        stack.setCurrentWidget(overlay)

        return container

    def _create_about_tab(self):
        """关于标签页"""
        widget = QWidget()
        form = QFormLayout(widget)

        self.title = QLabel(self.tr("QQListener"))
        self.title.setStyleSheet("font-size: 20px; font-weight: 600;")
        self.subtitle = QLabel(self.tr("最好的QQ通知监控软件 - 班级群监控神器 v1.2 MJ_20260502"))
        self.subtitle.setStyleSheet("font-size: 16px")

        self.author_title = QLabel(
            self.tr(
                "作者：株洲市南方中学 xxt8582753; 修改：Dlam567\n作者网站：https://xxtsoft.top\n作者邮箱：xxt8582753@126.com"
            )
        )
        self.author_title.setStyleSheet("font-size: 16px")

        self.privacy_hint = QLabel(self.tr("我的数据安全吗？"))
        self.privacy_hint.mousePressEvent = lambda event: QMessageBox.information(
            self,
            self.tr("我是绝对绝对不会出卖你的！"),
            self.tr(
                "您的数据是安全的，您的QQ号，文件路径全部保存在本地，聊天记录等信息不会上传，也没有任何遥测和错误报告。\nQQListener 是开源软件，使用 MIT 许可证，您可以在 GitHub 上查看源代码"
            ),
        )

        self.help_me_hint = QLabel(self.tr("支持开发者"))
        self.help_me_hint.mousePressEvent = lambda event: (
            webbrowser.open("https://xxtsoft.top/donate")
            if QMessageBox.information(
                self,
                self.tr("支持一下嘛"),
                self.tr(
                    "我是一名高中生，没有稳定的经济来源，如果您喜欢这个项目，并且想要支持我继续开发和维护，可以考虑请我喝杯奶茶哦~\n"
                ),
                QMessageBox.Ok | QMessageBox.Cancel,
            )
            == QMessageBox.Ok
            else None
        )

        self.find_icon_hint = QLabel(self.tr("QQListener 征集图标"))
        self.find_icon_hint.mousePressEvent = lambda event: QMessageBox.information(
            self,
            self.tr("QQListener 征集图标"),
            self.tr("目前这个图标有点丑，如果你有更好的，欢迎联系我！"),
        )

        self.modifications_title = QLabel(
            self.tr(
                "\n\nTips:\n此版本为修改版\n基于作者 xxt8582753 的 班级群监控神器 v1.1 20260319 版本进行修改\n修改作者：Major_Technology  Dlam567\n原始版权归 xxt8582753 所有, 本修改版基于 MIT 协议进行修改与分发，使用本软件需遵守 MIT 协议."
            )
        )
        self.modifications_title.setStyleSheet("font-size: 13px")

        self.button_layout = QHBoxLayout()
        self.clear = QPushButton(self.tr("清除缓存"))
        self.clear.clicked.connect(self._clear_cache)
        self.help = QPushButton(self.tr("查看教程"))
        self.help.clicked.connect(lambda: webbrowser.open("https://xxtsoft.top/support/qqlistener"))
        self.translation = QPushButton(self.tr("提交翻译"))
        self.translation.clicked.connect(
            lambda: webbrowser.open("https://xxtsoft.top/support/qqlistener/translation")
        )
        self.button_layout.addWidget(self.clear)
        self.button_layout.addWidget(self.help)
        self.button_layout.addWidget(self.translation)

        form.addRow(self.title)
        form.addRow(self.subtitle)
        form.addRow(self.author_title)
        form.addRow(self.privacy_hint)
        form.addRow(self.help_me_hint)
        form.addRow(self.find_icon_hint)
        form.addRow(self.button_layout)
        form.addRow(self.modifications_title)

        return widget

    def _create_list(self, items):
        """创建列表组件"""
        container = QWidget()
        layout = QVBoxLayout(container)

        list_widget = QListWidget()
        for item in items:
            list_widget.addItem(item)

        input_line = QLineEdit()
        input_line.setPlaceholderText(self.tr("输入后点击添加。也可使用回车键"))
        input_line.returnPressed.connect(lambda: self._add_item(list_widget, input_line))
        btn_add = QPushButton(self.tr("添加"))
        btn_remove = QPushButton(self.tr("删除选中"))
        btn_add.clicked.connect(lambda: self._add_item(list_widget, input_line))
        btn_remove.clicked.connect(lambda: self._remove_item(list_widget))

        layout.addWidget(list_widget)

        btn_row = QHBoxLayout()
        btn_row.addWidget(input_line)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        layout.addLayout(btn_row)
        container.list_widget = list_widget

        return container

    def _add_item(self, widget, line):
        """添加列表项"""
        text = line.text().strip()
        if not text:
            return
        for i in range(widget.count()):
            if widget.item(i).text() == text:
                QMessageBox.information(self, self.tr("提示"), self.tr("该项已存在"))
                line.clear()
                return
        widget.addItem(text)
        line.clear()

    def _remove_item(self, widget):
        """删除列表项"""
        selected = widget.selectedItems()
        for item in selected:
            widget.takeItem(widget.row(item))

    def _get_list(self, container):
        """获取列表数据"""
        list_widget = container.list_widget
        return [list_widget.item(i).text() for i in range(list_widget.count())]

    def _select_path(self):
        """选择文件夹"""
        path = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹"))
        if path:
            self.tencent_path.setText(path)

    def _select_file(self, line):
        """选择文件"""
        path, _ = QFileDialog.getOpenFileName(self, self.tr("选择文件"))
        if path:
            line.setText(path)

    def _test_sound(self, line):
        """测试声音"""
        path = line.text().strip()
        if path and os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

    def _test_exe(self, name):
        """测试程序是否运行"""
        try:
            output = subprocess.check_output(
                f'tasklist /fi "imagename eq {name}*"',
                shell=True,
                text=True,
                stderr=subprocess.STDOUT,
            )
            if name in output:
                QMessageBox.information(self, self.tr("成功"), self.tr(f"{name} 活着"))
            else:
                QMessageBox.warning(self, self.tr("失败"), self.tr(f"{name} 死了"))
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"执行命令失败: {e.output}"))

    def _clear_cache(self):
        """清除缓存"""
        if os.path.exists("tts_output.mp3"):
            os.remove("tts_output.mp3")
        QMessageBox.information(self, self.tr("成功"), self.tr("缓存已清除"))

    def _test_notify(self):
        """测试通知"""
        from src.ui.notify_manager import get_notify_manager

        test_data = {
            "Sender": "测试发送者",
            "Message": "这是一条测试消息",
            "Duration": 5000,
            "Priority": 0,
            "Calling": False,
            "icon_file": "asset/pdf.png",
        }
        get_notify_manager().show_notification(test_data)

    def _on_setting_theme_changed(self):
        """设置主题改变"""
        selected = self.theme_setting_combo.currentText()
        app = QApplication.instance()
        if not app:
            return
        if selected in ("Fusion", "Windows11", "Windows9x"):
            app.setStyleSheet("")
            app.setPalette(app.style().standardPalette())
            if selected == "Fusion":
                app.setStyle("Fusion")
            elif selected == "Windows11":
                app.setStyle("windows11")
            elif selected == "Windows9x":
                app.setStyle("windows")
        else:
            apply_stylesheet(app, theme=selected)

    def _on_language_changed(self):
        """语言改变"""
        selected = self.language_combo.currentIndex()
        app = QApplication.instance()
        if not app:
            return
        translator = QTranslator()

        if selected == 0:
            translator.load("translations/en_US.qm")
            app.installTranslator(translator)
        elif selected == 1:
            translator.load("translations/ja_JP.qm")
            app.installTranslator(translator)

    def _on_tts_changed(self, state):
        """TTS状态改变"""
        current = state == Qt.Checked
        self.edge_tts.setEnabled(current)
        self.edge_pitch.setEnabled(current and self.edge_tts.isChecked())
        self.edge_rate.setEnabled(current and self.edge_tts.isChecked())
        self.edge_test_btn.setEnabled(current)
        self.edge_test_text.setEnabled(current)
        self.edge_voice.setEnabled(current and self.edge_tts.isChecked())
        self.edge_volume.setEnabled(current and self.edge_tts.isChecked())

    def _on_edge_test(self):
        """Edge TTS测试"""
        if self.edge_tts.isChecked():
            self._edge_tts_engine(
                TEXT=self.edge_test_text.text(),
                VOICE=self.edge_voice.currentText(),
                PITCH=f"{self.edge_pitch.value():+d}Hz",
                VOLUME=f"{self.edge_volume.value():+d}%",
                RATE=f"{self.edge_rate.value():+d}%",
            )
        else:
            engine = pyttsx3.init()
            engine.setProperty(
                "voice",
                r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ZH-CN_HUIHUI_11.0",
            )
            engine.setProperty("volume", 1)
            engine.say(self.edge_test_text.text())
            engine.runAndWait()

    def _edge_tts_engine(self, TEXT, VOICE, RATE, PITCH, VOLUME):
        """Edge TTS引擎"""
        OUTPUT_FILE = "tts_output.mp3"
        cmd = (
            f"edge-tts "
            f'--voice "{VOICE}" '
            f'--rate "{RATE}" '
            f'--pitch "{PITCH}" '
            f'--volume "{VOLUME}" '
            f'--text "{TEXT}" '
            f'--write-media "{OUTPUT_FILE}"'
        )

        subprocess.run(cmd, shell=True, check=True)
        pygame.mixer.init()
        pygame.mixer.music.load(OUTPUT_FILE)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.quit()

    def _apply_theme(self):
        """应用主题"""
        app = QApplication.instance()
        if not app:
            return
        selected = self.data.get("Theme_Setting_Combo", self.settings.theme_setting)
        if selected == "Fusion":
            app.setStyle("Fusion")
        elif selected == "Windows11":
            app.setStyle("windows11")
        elif selected == "Windows9x":
            app.setStyle("windows")
        else:
            apply_stylesheet(app, theme=selected)

    def save_settings(self):
        """保存设置"""
        self.settings.update(
            {
                "ScanInterval": self.scan_interval.value(),
                "Cooldown": self.cooldown.value(),
                "Tencent_Files_Path": self.tencent_path.text(),
                "User_QQ": self.user_qq.text(),
                "UIAMode": self.uia_mode.isChecked(),
                "auto_start": self.auto_start.isChecked(),
                "Important_Persons": self._get_list(self.list_persons),
                "Important_Keywords": self._get_list(self.list_keywords),
                "BlackList": self._get_list(self.list_black),
                "Sound_Effect_Normal": self.sound_normal.text(),
                "Sound_Effect_Important": self.sound_important.text(),
                "Sound_Calling": self.sound_calling.text(),
                "Auto_Show_Thumb": self.auto_thumb.isChecked(),
                "Always_On_Top": self.always_on_top.isChecked(),
                "Max_Wait_Thumb_Time": self.max_wait.value(),
                "Duration_Everyone": self.duration_everyone.value(),
                "Duration_Important": self.duration_important.value(),
                "Theme_Setting_Combo": self.theme_setting_combo.currentText(),
                "Theme_Notify_Combo": self.theme_notify_combo.currentText(),
                "Notify_Shadow": self.notify_shadow.isChecked(),
                "Notify_Animation": self.notify_animation.isChecked(),
                "Notify_Label": self.notify_label.text(),
                "Someone_At_Me": self.someone_at_me.isChecked(),
                "Calling": self.calling.isChecked(),
                "Calling_Keyword": self.calling_keyword.text(),
                "Calling_Duration": self.calling_during.value(),
                "TTS": self.tts.isChecked(),
                "Edge_TTS": self.edge_tts.isChecked(),
                "Edge_Voice": self.edge_voice.currentText(),
                "Edge_Rate": f"{self.edge_rate.value():+d}%",
                "Edge_Volume": f"{self.edge_volume.value():+d}%",
                "Edge_Pitch": f"{self.edge_pitch.value():+d}Hz",
                "Override_qss": self.override.isChecked(),
                "Override_Path": self.override_qss.text(),
                "Green_Hand": False,
                "Language": self._get_language_code(),
                "QQ_Only": self.qq_only.isChecked(),
                "Notify_Mask": self.notify_mask.isChecked(),
                "Calling_BPM": self.calling_bpm.value(),
                "Calling_Animation": self.calling_anim.isChecked(),
                "icon_ok": self.notify_icon_ok.text(),
                "icon_cancel": self.notify_icon_cancel.text(),
                "Notify_Title_Font": self.notify_title_font.text(),
                "Notify_Message_Font": self.notify_message_font.text(),
                "TimeRestriction": self.time_restriction_config._data.get("TimeRestriction", {}),
            }
        )
        self.time_restriction_config.enabled = self.time_restriction_enabled.isChecked()

        auto_start_value = self.auto_start.isChecked()
        self.settings.set("auto_start", auto_start_value)
        self._update_auto_start_registry(auto_start_value)

        if self.settings.save():
            self.signals.settings_changed.emit()
            QMessageBox.information(self, self.tr("成功"), self.tr("设置已保存"))
        else:
            QMessageBox.warning(self, self.tr("错误"), self.tr("设置保存失败"))

    def _get_language_code(self):
        """获取语言代码"""
        idx = self.language_combo.currentIndex()
        if idx == 0:
            return "en-US"
        elif idx == 1:
            return "ja-JP"
        else:
            return "zh-CN"

    def _update_auto_start_registry(self, enable: bool) -> bool:
        """
        更新开机自启注册表项
        :param enable: True=开启自启, False=关闭自启
        :return: 是否成功
        """
        # 获取当前程序路径
        if getattr(sys, 'frozen', False):
            app_path = sys.executable
        else:
            app_path = os.path.abspath(sys.argv[0])

        app_name = os.path.splitext(os.path.basename(app_path))[0]

        # 构建命令
        if app_path.endswith(".py"):
            command = f'"{sys.executable}" "{app_path}"'
        else:
            command = f'"{app_path}"'

        # 注册表路径
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)

            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
                print(f"✅ 已开启开机自启: {app_name}")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    print(f"✅ 已关闭开机自启: {app_name}")
                except FileNotFoundError:
                    pass

            winreg.CloseKey(key)
            return True
        except Exception as e:
            QMessageBox.warning(self, self.tr("错误"), self.tr(f"操作注册表失败: {e}"))
            return False

    def _init_auto_start_from_registry(self):
        """从注册表读取当前自启状态，同步到设置"""
        try:
            app_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
            app_name = os.path.splitext(os.path.basename(app_path))[0]
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, app_name)
                self.auto_start.setChecked(True)
                self.settings.set("auto_start", True)
            except FileNotFoundError:
                self.auto_start.setChecked(False)
                self.settings.set("auto_start", False)
            winreg.CloseKey(key)
        except Exception:
            pass


class AddTimeRangeDialog(QDialog):
    def __init__(self, parent=None, editing=False):
        super().__init__(parent)
        self.setWindowTitle("编辑禁用时段" if editing else "新增禁用时段")
        self.setFixedSize(480, 340)

        main_layout = QVBoxLayout(self)

        days_group = QGroupBox("选择星期")
        days_layout = QVBoxLayout(days_group)
        self.day_checkboxes = []
        days_row1 = QHBoxLayout()
        days_row2 = QHBoxLayout()
        for i, day_name in enumerate(DAY_NAMES):
            cb = QCheckBox(day_name)
            self.day_checkboxes.append(cb)
            if i < 5:
                days_row1.addWidget(cb)
            else:
                days_row2.addWidget(cb)
        days_layout.addLayout(days_row1)
        days_layout.addLayout(days_row2)
        main_layout.addWidget(days_group)

        time_group = QGroupBox("时间范围")
        time_layout = QHBoxLayout(time_group)
        time_layout.addWidget(QLabel("开始时间："))
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(self.start_time.minimumTime())
        self.start_time.setMinimumWidth(120)
        time_layout.addWidget(self.start_time)
        time_layout.addSpacing(20)
        time_layout.addWidget(QLabel("结束时间："))
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(self.end_time.maximumTime())
        self.end_time.setMinimumWidth(120)
        time_layout.addWidget(self.end_time)
        main_layout.addWidget(time_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok = QPushButton("确定")
        self.btn_cancel = QPushButton("取消")
        self.btn_ok.setMinimumWidth(80)
        self.btn_cancel.setMinimumWidth(80)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    def set_days(self, days: list[int]):
        for d in days:
            if 1 <= d <= 7:
                self.day_checkboxes[d - 1].setChecked(True)

    def set_start_time(self, time_str: str):
        from PySide6.QtCore import QTime

        t = QTime.fromString(time_str, "HH:mm")
        if t.isValid():
            self.start_time.setTime(t)

    def set_end_time(self, time_str: str):
        from PySide6.QtCore import QTime

        t = QTime.fromString(time_str, "HH:mm")
        if t.isValid():
            self.end_time.setTime(t)

    def get_selected_days(self) -> list[int]:
        return [i + 1 for i, cb in enumerate(self.day_checkboxes) if cb.isChecked()]

    def get_start_time(self) -> str:
        return self.start_time.time().toString("HH:mm")

    def get_end_time(self) -> str:
        return self.end_time.time().toString("HH:mm")
