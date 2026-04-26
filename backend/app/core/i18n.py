"""
I18n - Internationalization utility for Sparkle AI.
Loads translations from JSON files and provides localized strings based on locale.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger

class I18n:
    _translations: Dict[str, Dict[str, Any]] = {}
    _default_locale = "en"
    _locales_dir = Path(__file__).resolve().parent.parent / "data" / "i18n"

    @classmethod
    def load_translations(cls):
        """Load all translation files from the locales directory."""
        if not cls._locales_dir.exists():
            cls._locales_dir.mkdir(parents=True, exist_ok=True)
            # Create default files if they don't exist
            cls._create_default_files()

        for file_path in cls._locales_dir.glob("*.json"):
            locale = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    cls._translations[locale] = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load translation file {file_path}: {e}")

    @classmethod
    def _create_default_files(cls):
        """Create initial en.json and zh.json files with basic structure."""
        en_default = {
            "common": {
                "unknown": "Unknown",
                "success": "Success",
                "error": "Error"
            },
            "planner": {
                "constraints_header": "Planning Constraints (must be met if possible):",
                "ai_study_plan": "AI Study Plan",
                "start_task_with": "Before starting the target task, arrange a 「{topic}」"
            }
        }
        zh_default = {
            "common": {
                "unknown": "未知",
                "success": "成功",
                "error": "错误"
            },
            "planner": {
                "constraints_header": "规划约束（必须尽量满足）：",
                "ai_study_plan": "AI 学习计划",
                "start_task_with": "在开始目标任务前，先安排一个针对「{topic}」"
            }
        }
        
        with open(cls._locales_dir / "en.json", "w", encoding="utf-8") as f:
            json.dump(en_default, f, ensure_ascii=False, indent=2)
        with open(cls._locales_dir / "zh.json", "w", encoding="utf-8") as f:
            json.dump(zh_default, f, ensure_ascii=False, indent=2)

    @classmethod
    def t(cls, key: str, locale: str = "en", **kwargs) -> str:
        """
        Translate a key to the given locale.
        Key format: 'namespace.key' or 'namespace.nested.key'
        """
        # Map zh-CN, zh_CN, etc to zh
        if locale.startswith("zh"):
            locale = "zh"
        else:
            locale = "en"

        if not cls._translations:
            cls.load_translations()

        data = cls._translations.get(locale, cls._translations.get(cls._default_locale, {}))
        
        parts = key.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                logger.warning(f"Translation key not found: {key} for locale: {locale}")
                return key
        
        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format argument for key {key}: {e}")
                return value
        
        return str(value)

# Initialize
I18n.load_translations()
