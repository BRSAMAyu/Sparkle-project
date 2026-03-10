"""
Achievement share card generation service.
"""
from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from textwrap import shorten
from typing import Any
from uuid import UUID

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.models.achievement import Achievement, UserAchievement
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(slots=True)
class ShareCardResult:
    """Generated share card metadata."""

    card_url: str
    mime_type: str
    width: int
    height: int
    generated_at: datetime


class ShareCardService:
    """Generate and cache achievement share cards."""

    TEMPLATE_VERSION = "v1"
    WIDTH = 1080
    HEIGHT = 1440
    MIME_TYPE = "image/png"
    CACHE_TTL_SECONDS = 86400 * 7
    FONT_CANDIDATES = (
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    )
    STYLE_MAP = {
        "common": {
            "bg_top": (51, 65, 85),
            "bg_bottom": (15, 23, 42),
            "accent": (226, 232, 240),
            "glow": (148, 163, 184),
            "panel": (255, 255, 255, 28),
        },
        "rare": {
            "bg_top": (120, 53, 15),
            "bg_bottom": (69, 26, 3),
            "accent": (253, 224, 71),
            "glow": (251, 191, 36),
            "panel": (255, 255, 255, 30),
        },
        "epic": {
            "bg_top": (76, 29, 149),
            "bg_bottom": (59, 7, 100),
            "accent": (216, 180, 254),
            "glow": (192, 132, 252),
            "panel": (255, 255, 255, 30),
        },
        "legendary": {
            "bg_top": (5, 150, 105),
            "bg_mid": (37, 99, 235),
            "bg_bottom": (126, 34, 206),
            "accent": (254, 240, 138),
            "glow": (251, 191, 36),
            "panel": (255, 255, 255, 36),
        },
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_achievement_share_card(
        self,
        user_id: UUID | str,
        achievement_id: str,
    ) -> tuple[ShareCardResult, Achievement, UserAchievement]:
        """Generate a static PNG share card for an unlocked achievement."""
        user = await self._get_user(user_id)
        achievement = await self._get_achievement(achievement_id)
        user_achievement = await self._get_user_achievement(user_id, achievement_id)

        if user is None:
            raise ValueError("User not found")
        if achievement is None:
            raise ValueError("Achievement not found")
        if user_achievement is None or user_achievement.unlocked_at is None:
            raise ValueError("Achievement not unlocked yet")

        cache_key = self._cache_key(user.id, achievement.id)
        cached_payload = await cache_service.get(cache_key)
        result = await self._resolve_cached_result(user.id, achievement.id, cached_payload)

        if result is None:
            result = await self._render_and_store_card(
                user=user,
                achievement=achievement,
                unlocked_at=user_achievement.unlocked_at,
            )
            await cache_service.set(
                cache_key,
                {
                    "card_url": result.card_url,
                    "mime_type": result.mime_type,
                    "width": result.width,
                    "height": result.height,
                    "generated_at": result.generated_at.isoformat(),
                },
                ttl=self.CACHE_TTL_SECONDS,
            )

        user_achievement.share_count = (user_achievement.share_count or 0) + 1
        await self.db.commit()
        await self.db.refresh(user_achievement)

        return result, achievement, user_achievement

    async def _resolve_cached_result(
        self,
        user_id: UUID,
        achievement_id: str,
        cached_payload: Any,
    ) -> ShareCardResult | None:
        if not isinstance(cached_payload, dict):
            return None

        file_path = self._card_file_path(user_id, achievement_id)
        if not file_path.exists():
            return None

        generated_at = cached_payload.get("generated_at")
        if isinstance(generated_at, str):
            generated_at_value = datetime.fromisoformat(generated_at)
        else:
            generated_at_value = _utcnow()

        return ShareCardResult(
            card_url=str(cached_payload.get("card_url") or self._public_card_url(user_id, achievement_id)),
            mime_type=str(cached_payload.get("mime_type") or self.MIME_TYPE),
            width=int(cached_payload.get("width") or self.WIDTH),
            height=int(cached_payload.get("height") or self.HEIGHT),
            generated_at=generated_at_value,
        )

    async def _render_and_store_card(
        self,
        *,
        user: User,
        achievement: Achievement,
        unlocked_at: datetime,
    ) -> ShareCardResult:
        output_path = self._card_file_path(user.id, achievement.id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generated_at = _utcnow()
        await asyncio.to_thread(
            self._render_card_sync,
            output_path,
            user,
            achievement,
            unlocked_at,
        )
        return ShareCardResult(
            card_url=self._public_card_url(user.id, achievement.id),
            mime_type=self.MIME_TYPE,
            width=self.WIDTH,
            height=self.HEIGHT,
            generated_at=generated_at,
        )

    async def _get_user(self, user_id: UUID | str) -> User | None:
        return await self.db.get(User, user_id)

    async def _get_achievement(self, achievement_id: str) -> Achievement | None:
        return await self.db.get(Achievement, achievement_id)

    async def _get_user_achievement(self, user_id: UUID | str, achievement_id: str) -> UserAchievement | None:
        result = await self.db.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement_id,
                )
            )
        )
        return result.scalar_one_or_none()

    def _cache_key(self, user_id: UUID, achievement_id: str) -> str:
        return f"achievement:share_card:{user_id}:{achievement_id}:{self.TEMPLATE_VERSION}"

    def _card_file_path(self, user_id: UUID, achievement_id: str) -> Path:
        return Path(settings.UPLOAD_DIR).resolve() / "achievement-cards" / str(user_id) / (
            f"{achievement_id}_{self.TEMPLATE_VERSION}.png"
        )

    def _public_card_url(self, user_id: UUID, achievement_id: str) -> str:
        return f"/uploads/achievement-cards/{user_id}/{achievement_id}_{self.TEMPLATE_VERSION}.png"

    def _render_card_sync(
        self,
        output_path: Path,
        user: User,
        achievement: Achievement,
        unlocked_at: datetime,
    ) -> None:
        rarity = getattr(achievement.rarity, "value", str(achievement.rarity))
        style = self.STYLE_MAP[rarity]
        image = self._build_background(style, seed=f"{user.id}:{achievement.id}")
        draw = ImageDraw.Draw(image, "RGBA")

        title_font = self._load_font(72)
        badge_font = self._load_font(32)
        heading_font = self._load_font(42)
        body_font = self._load_font(28)
        tiny_font = self._load_font(24)

        accent = style["accent"]
        panel = style["panel"]

        self._draw_glow_ring(draw, style)
        self._draw_header(draw, achievement, title_font, badge_font, accent)
        self._draw_info_panels(
            draw=draw,
            achievement=achievement,
            user=user,
            unlocked_at=unlocked_at,
            heading_font=heading_font,
            body_font=body_font,
            tiny_font=tiny_font,
            panel_color=panel,
            accent=accent,
        )
        self._draw_footer(draw, tiny_font, accent)

        image = image.filter(ImageFilter.SMOOTH_MORE)
        image.save(output_path, format="PNG", optimize=True)

    def _build_background(self, style: dict[str, Any], *, seed: str) -> Image.Image:
        image = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 255))
        draw = ImageDraw.Draw(image, "RGBA")
        top = style["bg_top"]
        bottom = style["bg_bottom"]
        mid = style.get("bg_mid")

        for y in range(self.HEIGHT):
            ratio = y / max(self.HEIGHT - 1, 1)
            if mid is None:
                color = self._lerp_color(top, bottom, ratio)
            elif ratio < 0.5:
                color = self._lerp_color(top, mid, ratio * 2)
            else:
                color = self._lerp_color(mid, bottom, (ratio - 0.5) * 2)
            draw.line([(0, y), (self.WIDTH, y)], fill=(*color, 255))

        rng = random.Random(seed)
        for _ in range(90):
            radius = rng.randint(2, 6)
            alpha = rng.randint(70, 180)
            x = rng.randint(0, self.WIDTH)
            y = rng.randint(0, self.HEIGHT)
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius),
                fill=(*style["accent"], alpha),
            )

        for offset in range(-250, 251, 125):
            draw.ellipse(
                (
                    80 + offset,
                    140 + max(offset, 0),
                    self.WIDTH - 80 + offset,
                    self.HEIGHT - 220 + max(offset, 0),
                ),
                outline=(*style["glow"], 30),
                width=3,
            )

        return image

    def _draw_glow_ring(self, draw: ImageDraw.ImageDraw, style: dict[str, Any]) -> None:
        center_x = self.WIDTH // 2
        center_y = 320
        for step in range(5):
            radius = 90 + step * 24
            alpha = max(16, 100 - step * 18)
            draw.ellipse(
                (
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                ),
                outline=(*style["glow"], alpha),
                width=6,
            )

        draw.ellipse(
            (center_x - 72, center_y - 72, center_x + 72, center_y + 72),
            fill=(*style["accent"], 44),
            outline=(*style["accent"], 255),
            width=5,
        )

        star_points = []
        outer = 40
        inner = 18
        for index in range(10):
            angle = math.pi / 2 + index * math.pi / 5
            radius = outer if index % 2 == 0 else inner
            star_points.append((center_x + math.cos(angle) * radius, center_y - math.sin(angle) * radius))
        draw.polygon(star_points, fill=(255, 255, 255, 240))

    def _draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        achievement: Achievement,
        title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        badge_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        accent: tuple[int, int, int],
    ) -> None:
        rarity_name = self._rarity_label(getattr(achievement.rarity, "value", str(achievement.rarity)))
        badge_box = (90, 72, 360, 132)
        draw.rounded_rectangle(badge_box, radius=28, fill=(*accent, 42), outline=(*accent, 128), width=2)
        draw.text((122, 88), f"SPARKLE {rarity_name}", fill=(255, 255, 255, 240), font=badge_font)

        self._draw_multiline_text(
            draw=draw,
            text=achievement.name,
            font=title_font,
            fill=(255, 255, 255, 255),
            left=90,
            top=470,
            max_width=self.WIDTH - 180,
            line_spacing=18,
            max_lines=2,
        )

    def _draw_info_panels(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        achievement: Achievement,
        user: User,
        unlocked_at: datetime,
        heading_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        tiny_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        panel_color: tuple[int, int, int, int],
        accent: tuple[int, int, int],
    ) -> None:
        info_top = 690
        draw.rounded_rectangle(
            (78, info_top, self.WIDTH - 78, info_top + 430),
            radius=36,
            fill=panel_color,
            outline=(*accent, 96),
            width=2,
        )

        draw.text((120, info_top + 48), "Achievement Unlocked", fill=(255, 255, 255, 255), font=heading_font)
        description = achievement.description or "Keep moving. Every milestone changes your galaxy."
        self._draw_multiline_text(
            draw=draw,
            text=description,
            font=body_font,
            fill=(244, 244, 245, 230),
            left=120,
            top=info_top + 128,
            max_width=self.WIDTH - 240,
            line_spacing=14,
            max_lines=4,
        )

        username = user.nickname or user.full_name or user.username
        draw.rounded_rectangle(
            (120, info_top + 282, self.WIDTH - 120, info_top + 378),
            radius=26,
            fill=(255, 255, 255, 20),
            outline=(255, 255, 255, 36),
            width=2,
        )
        draw.text((150, info_top + 304), shorten(username, width=24, placeholder="..."), fill=(255, 255, 255, 255), font=body_font)
        draw.text(
            (150, info_top + 344),
            unlocked_at.strftime("Unlocked on %Y-%m-%d %H:%M UTC"),
            fill=(255, 255, 255, 188),
            font=tiny_font,
        )

    def _draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        accent: tuple[int, int, int],
    ) -> None:
        footer_text = "Share your latest milestone from Sparkle."
        text_box = draw.textbbox((0, 0), footer_text, font=font)
        text_width = text_box[2] - text_box[0]
        draw.text(
            ((self.WIDTH - text_width) / 2, self.HEIGHT - 118),
            footer_text,
            fill=(*accent, 220),
            font=font,
        )

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for candidate in self.FONT_CANDIDATES:
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _draw_multiline_text(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        fill: tuple[int, int, int, int] | tuple[int, int, int],
        left: int,
        top: int,
        max_width: int,
        line_spacing: int,
        max_lines: int,
    ) -> None:
        current_top = top
        for index, line in enumerate(self._wrap_text(draw, text, font, max_width, max_lines)):
            if index >= max_lines:
                break
            draw.text((left, current_top), line, fill=fill, font=font)
            box = draw.textbbox((left, current_top), line, font=font)
            current_top = box[3] + line_spacing

    def _wrap_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
        max_lines: int,
    ) -> list[str]:
        text = text.strip()
        if not text:
            return [""]

        lines: list[str] = []
        current = ""

        for char in text:
            if char == "\n":
                if current:
                    lines.append(current)
                current = ""
                if len(lines) >= max_lines:
                    break
                continue

            candidate = f"{current}{char}"
            box = draw.textbbox((0, 0), candidate, font=font)
            width = box[2] - box[0]
            if current and width > max_width:
                lines.append(current)
                current = char
                if len(lines) >= max_lines:
                    break
            else:
                current = candidate

        if len(lines) < max_lines and current:
            lines.append(current)

        if len(lines) > max_lines:
            lines = lines[:max_lines]

        if len(lines) == max_lines and text:
            last_line = lines[-1]
            while last_line and (draw.textbbox((0, 0), f"{last_line}...", font=font)[2] > max_width):
                last_line = last_line[:-1]
            lines[-1] = f"{last_line}..." if last_line != lines[-1] else last_line

        return lines

    def _lerp_color(self, start: tuple[int, int, int], end: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
        ratio = max(0.0, min(1.0, ratio))
        return tuple(int(start[index] + (end[index] - start[index]) * ratio) for index in range(3))

    def _rarity_label(self, rarity: str) -> str:
        labels = {
            "common": "COMMON",
            "rare": "RARE",
            "epic": "EPIC",
            "legendary": "LEGENDARY",
        }
        return labels.get(rarity, rarity.upper())
