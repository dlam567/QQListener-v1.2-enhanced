import asyncio
import os

import edge_tts
import pygame
from loguru import logger
from PySide6.QtCore import QThread, Signal

from src.core.settings import get_settings


class TTSThread(QThread):
    finished_signal = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text = text if text and isinstance(text, str) else ""
        self.settings = get_settings()

    def run(self):
        """执行TTS"""
        if not self.text:
            self.finished_signal.emit("")
            return

        try:
            if self.settings.edge_tts_enabled:
                self._run_edge_tts()
            else:
                self._run_system_tts()
        except Exception:
            logger.exception("TTS错误")
            self.finished_signal.emit("")

    def _run_edge_tts(self):
        """使用Edge TTS (模块调用)"""
        output_file = "tts_temp.mp3"

        voice = self.settings.edge_voice or "zh-CN-XiaoyiNeural"
        rate = self.settings.edge_rate
        pitch = self.settings.edge_pitch
        volume = self.settings.edge_volume

        safe_text = self.text.replace('"', "'") if self.text else ""
        if not safe_text:
            self.finished_signal.emit("")
            return

        async def run_tts():
            try:
                communicate = edge_tts.Communicate(
                    text=safe_text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume=volume,
                )
                await communicate.save(output_file)
                self.finished_signal.emit(output_file)
            except Exception:
                logger.exception("Edge TTS执行失败")
                self.finished_signal.emit("")

        asyncio.run(run_tts())

    def _run_system_tts(self):
        import pyttsx3

        try:
            engine = pyttsx3.init()
            engine.setProperty(
                "voice",
                r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ZH-CN_HUIHUI_11.0",
            )
            engine.setProperty("volume", 1)
            engine.say(self.text)
            engine.runAndWait()
            self.finished_signal.emit("")
        except Exception:
            logger.exception("系统TTS失败")
            self.finished_signal.emit("")


class TTSManager:
    def __init__(self):
        self.settings = get_settings()
        self._current_thread: TTSThread | None = None

    def speak(self, text: str) -> None:
        """播放语音"""
        if not self.settings.tts_enabled or not text or not isinstance(text, str):
            return

        self._current_thread = TTSThread(text)

        def on_tts_ready(file_path: str):
            if file_path and os.path.exists(file_path):
                try:
                    sound = pygame.mixer.Sound(file_path)
                    sound.play()
                except Exception:
                    logger.exception("播放TTS音频失败")

        self._current_thread.finished_signal.connect(on_tts_ready)
        self._current_thread.start()

    def stop(self) -> None:
        """停止当前TTS"""
        if self._current_thread and self._current_thread.isRunning():
            self._current_thread.quit()
            self._current_thread.wait(1000)
