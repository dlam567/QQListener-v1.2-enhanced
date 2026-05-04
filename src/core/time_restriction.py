#  Copyright (c) 2026 Major_Technology. All rights reserved.
#  SPDX-License-Identifier: MIT

import json
import os
from datetime import datetime, timedelta
from typing import Any


class TimeRestrictionConfig:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings_file: str = "setting.json"):
        if TimeRestrictionConfig._initialized:
            return
        self._settings_file = settings_file
        self._data: dict[str, Any] = {}
        self._load()
        TimeRestrictionConfig._initialized = True

    def _load(self) -> None:
        if os.path.exists(self._settings_file):
            try:
                with open(self._settings_file, encoding="utf-8") as f:
                    self._data = json.load(f)
                    if not isinstance(self._data, dict):
                        self._data = {}
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> bool:
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
            return True
        except OSError:
            return False

    @property
    def enabled(self) -> bool:
        time_data = self._data.get("TimeRestriction", {})
        return time_data.get("enabled", False) if isinstance(time_data, dict) else False

    @enabled.setter
    def enabled(self, value: bool):
        if "TimeRestriction" not in self._data or not isinstance(self._data["TimeRestriction"], dict):
            self._data["TimeRestriction"] = {}
        self._data["TimeRestriction"]["enabled"] = value
        self._save()

    def get_time_ranges(self) -> list[dict]:
        time_data = self._data.get("TimeRestriction", {})
        if isinstance(time_data, dict) and "ranges" in time_data:
            return time_data["ranges"]
        return []

    def add_time_range(self, days: list[int], start_time: str, end_time: str) -> str:
        if "TimeRestriction" not in self._data or not isinstance(self._data["TimeRestriction"], dict):
            self._data["TimeRestriction"] = {"enabled": True, "ranges": []}

        ranges = self._data["TimeRestriction"].get("ranges", [])
        existing_ids = [
            int(r.get("id", "range_0").replace("range_", ""))
            for r in ranges
            if isinstance(r, dict) and r.get("id", "").startswith("range_")
        ]
        new_id = max(existing_ids, default=0) + 1
        range_id = f"range_{new_id}"

        days_str = ",".join(str(d) for d in sorted(days))
        new_range = {
            "id": range_id,
            "days": days_str,
            "time_range": f"{start_time}-{end_time}",
        }
        ranges.append(new_range)
        self._data["TimeRestriction"]["ranges"] = ranges
        self._save()
        return range_id

    def remove_time_range(self, range_id: str):
        if "TimeRestriction" in self._data and isinstance(self._data["TimeRestriction"], dict):
            ranges = self._data["TimeRestriction"].get("ranges", [])
            self._data["TimeRestriction"]["ranges"] = [
                r for r in ranges if isinstance(r, dict) and r.get("id") != range_id
            ]
            self._save()

    def clear_all_ranges(self):
        if "TimeRestriction" in self._data and isinstance(self._data["TimeRestriction"], dict):
            self._data["TimeRestriction"]["ranges"] = []
            self._save()

    def is_in_restriction(self, weekday: int, current_time: str) -> bool:
        """检查当前时间是否在限制时间段内"""
        if not self.enabled:
            return False

        ranges = self.get_time_ranges()
        try:
            current_t = datetime.strptime(current_time, "%H:%M").time()
        except ValueError:
            return False

        for range_data in ranges:
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
                    return True
            else:
                # 跨天时间段：两种情况
                # 1. 当前时间在start之后：需要当天在days中
                # 2. 当前时间在end之前：需要前一天在days中
                if current_t >= start_t:
                    # 在start之后，检查当天
                    if weekday in day_list:
                        return True
                if current_t <= end_t:
                    # 在end之前，检查前一天
                    prev_day = (weekday - 1) % 7
                    if prev_day in day_list:
                        return True

        return False


def get_time_restriction_config() -> TimeRestrictionConfig:
    return TimeRestrictionConfig()
