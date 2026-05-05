import json
import os
from typing import Any

from loguru import logger


class Settings:
    _instance: "Settings | None" = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "Settings":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings_file: str = "setting.json") -> None:
        if Settings._initialized:
            return

        self._settings_file: str = settings_file
        self._data: dict[str, Any] = {}
        self._load()
        Settings._initialized = True

    def _load(self) -> None:
        if not self._settings_file:
            self._data = {}
            return

        if os.path.exists(self._settings_file):
            try:
                with open(self._settings_file, encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    self._data = loaded_data if isinstance(loaded_data, dict) else {}
            except (json.JSONDecodeError, OSError):
                logger.exception("加载设置失败")
                self._data = {}
        else:
            self._data = {}

    def save(self) -> bool:
        if not self._settings_file:
            return False

        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
            return True
        except OSError:
            logger.exception("保存设置失败")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        if not key or not isinstance(key, str):
            return default
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置值"""
        if not key or not isinstance(key, str):
            return
        self._data[key] = value

    def update(self, data: dict[str, Any] | None) -> None:
        """批量更新设置"""
        if data and isinstance(data, dict):
            self._data.update(data)

    def get_all(self) -> dict[str, Any]:
        """获取所有设置"""
        return self._data.copy() if self._data else {}

    def is_first_run(self) -> bool:
        """检查是否是首次运行（未保存过设置）"""
        return bool(self._data.get("Green_Hand", True))

    def mark_configured(self) -> None:
        """标记已配置"""
        self._data["Green_Hand"] = False

    @property
    def thumb_path(self) -> str | None:
        tencent_path = self.get("Tencent_Files_Path", "")
        user_qq = self.get("User_QQ", "")
        if tencent_path and user_qq:
            import time

            return os.path.join(
                tencent_path, user_qq, "nt_qq", "nt_data", "Pic", time.strftime("%Y-%m"), "Thumb"
            )
        return None

    @property
    def important_persons(self) -> list[str]:
        result = self.get("Important_Persons", [])
        return result if isinstance(result, list) else []

    @property
    def important_keywords(self) -> list[str]:
        result = self.get("Important_Keywords", [])
        return result if isinstance(result, list) else []

    @property
    def blacklist(self) -> list[str]:
        result = self.get("BlackList", [])
        return result if isinstance(result, list) else []

    @property
    def scan_interval(self) -> float:
        result = self.get("ScanInterval", 0.3)
        return float(result) if isinstance(result, (int, float)) else 0.3

    @property
    def cooldown(self) -> int:
        result = self.get("Cooldown", 3)
        return int(result) if isinstance(result, (int, float)) else 3

    @property
    def uia_mode(self) -> bool:
        return bool(self.get("UIAMode", False))

    @property
    def qq_only(self) -> bool:
        return bool(self.get("QQ_Only", False))

    @property
    def auto_show_thumb(self) -> bool:
        return bool(self.get("Auto_Show_Thumb", False))

    @property
    def someone_at_me(self) -> bool:
        return bool(self.get("Someone_At_Me", True))

    @property
    def calling_enabled(self) -> bool:
        return bool(self.get("Calling", True))

    @property
    def calling_keyword(self) -> str:
        result = self.get("Calling_Keyword", "呼叫")
        return str(result) if result else "呼叫"

    @property
    def calling_duration(self) -> int:
        result = self.get("Calling_Duration", 600000)
        return int(result) if isinstance(result, (int, float)) else 600000

    @property
    def calling_animation(self) -> bool:
        return bool(self.get("Calling_Animation", True))

    @property
    def calling_bpm(self) -> int:
        result = self.get("Calling_BPM", 30)
        return int(result) if isinstance(result, (int, float)) else 30

    @property
    def tts_enabled(self) -> bool:
        return bool(self.get("TTS", True))

    @property
    def edge_tts_enabled(self) -> bool:
        return bool(self.get("Edge_TTS", True))

    @property
    def edge_voice(self) -> str:
        result = self.get("Edge_Voice", "zh-CN-XiaoyiNeural")
        return str(result) if result else "zh-CN-XiaoyiNeural"

    @property
    def edge_rate(self) -> str:
        result = self.get("Edge_Rate", "+0%")
        return str(result) if result else "+0%"

    @property
    def edge_pitch(self) -> str:
        result = self.get("Edge_Pitch", "+10Hz")
        return str(result) if result else "+10Hz"

    @property
    def edge_volume(self) -> str:
        result = self.get("Edge_Volume", "+0%")
        return str(result) if result else "+0%"

    @property
    def duration_everyone(self) -> int:
        result = self.get("Duration_Everyone", 5000)
        return int(result) if isinstance(result, (int, float)) else 5000

    @property
    def duration_important(self) -> int:
        result = self.get("Duration_Important", 10000)
        return int(result) if isinstance(result, (int, float)) else 10000

    @property
    def max_wait_thumb_time(self) -> int:
        result = self.get("Max_Wait_Thumb_Time", 5)
        return int(result) if isinstance(result, (int, float)) else 5

    @property
    def always_on_top(self) -> bool:
        return bool(self.get("Always_On_Top", False))

    @property
    def notify_shadow(self) -> bool:
        return bool(self.get("Notify_Shadow", True))

    @property
    def notify_animation(self) -> bool:
        return bool(self.get("Notify_Animation", True))

    @property
    def notify_mask(self) -> bool:
        return bool(self.get("Notify_Mask", True))

    @property
    def notify_label(self) -> str:
        result = self.get("Notify_Label", "xxtsoft QQListener")
        return str(result) if result else "xxtsoft QQListener"

    @property
    def theme_setting(self) -> str:
        result = self.get("Theme_Setting_Combo", "Fusion")
        return str(result) if result else "Fusion"

    @property
    def theme_notify(self) -> str:
        result = self.get("Theme_Notify_Combo", "FluentDark")
        return str(result) if result else "FluentDark"

    @property
    def sound_normal(self) -> str:
        result = self.get("Sound_Effect_Normal", "asset/notify_sound.mp3")
        return str(result) if result else "asset/notify_sound.mp3"

    @property
    def sound_important(self) -> str:
        result = self.get("Sound_Effect_Important", "asset/important_sound.mp3")
        return str(result) if result else "asset/important_sound.mp3"

    @property
    def sound_calling(self) -> str:
        result = self.get("Sound_Calling", "asset/calling_sound.mp3")
        return str(result) if result else "asset/calling_sound.mp3"

    @property
    def language(self) -> str:
        result = self.get("Language", "zh-CN")
        return str(result) if result else "zh-CN"

    @property
    def icon_ok(self) -> str:
        result = self.get("icon_ok", "asset/icon_ok.png")
        return str(result) if result else "asset/icon_ok.png"

    @property
    def icon_cancel(self) -> str:
        result = self.get("icon_cancel", "asset/icon_cancel.png")
        return str(result) if result else "asset/icon_cancel.png"

    @property
    def notify_title_font(self) -> str:
        result = self.get("Notify_Title_Font", "asset/Font/JingNanBoBoHei-Bold-2.ttf")
        return str(result) if result else "asset/Font/JingNanBoBoHei-Bold-2.ttf"

    @property
    def notify_message_font(self) -> str:
        result = self.get("Notify_Message_Font", "asset/Font/FZLanTYK.ttf")
        return str(result) if result else "asset/Font/FZLanTYK.ttf"

    @property
    def override_qss(self) -> bool:
        return bool(self.get("Override_qss", False))

    @property
    def override_qss_path(self) -> str:
        result = self.get("Override_Path", "")
        return str(result) if result else ""

    # 开机自启动
    @property
    def auto_start(self) -> bool:
        return bool(self.get("auto_start", False))


def get_settings() -> Settings:
    """获取设置单例实例"""
    return Settings()
