"""create visual elements tables

Revision ID: d1f2a3b4c5e6
Revises: c2a8f1e9d0b3
Create Date: 2026-03-16 10:00:00.000000

创建视觉元素系统相关表：
- visual_elements: 视觉元素定义
- user_visual_elements: 用户解锁的视觉元素
- user_visual_configs: 用户当前视觉配置
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "d1f2a3b4c5e6"
down_revision = "c2a8f1e9d0b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建 visual_elements 表
    op.create_table(
        "visual_elements",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("name_i18n", JSONB(), nullable=True, default={}),
        sa.Column("description_i18n", JSONB(), nullable=True, default={}),
        sa.Column(
            "element_type",
            sa.Enum(
                "background",
                "particle",
                "effect",
                "bundle",
                name="visualelementtype",
            ),
            nullable=False,
        ),
        sa.Column(
            "rarity",
            sa.Enum(
                "common",
                "rare",
                "epic",
                "legendary",
                name="visualelementrarity",
            ),
            nullable=False,
            default="common",
        ),
        sa.Column(
            "unlock_source",
            sa.Enum(
                "system",
                "achievement",
                "shop",
                "event",
                "season",
                name="visualelementunlocksource",
            ),
            nullable=True,
            default="system",
        ),
        sa.Column("unlock_requirement", JSONB(), nullable=True),
        sa.Column("config", JSONB(), nullable=False, default={}),
        sa.Column("preview_url", sa.String(500), nullable=True),
        sa.Column("icon_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("season_start", sa.String(10), nullable=True),
        sa.Column("season_end", sa.String(10), nullable=True),
        sa.Column("id", sa.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    # 创建索引
    op.create_index(
        "ix_visual_elements_type_rarity",
        "visual_elements",
        ["element_type", "rarity"],
    )
    op.create_index("ix_visual_elements_category", "visual_elements", ["category"])
    op.create_index("ix_visual_elements_active", "visual_elements", ["is_active"])

    # 2. 创建 user_visual_elements 表
    op.create_table(
        "user_visual_elements",
        sa.Column("user_id", sa.GUID(), nullable=False),
        sa.Column("element_id", sa.String(50), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(), nullable=False),
        sa.Column("unlock_source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=True),
        sa.Column("id", sa.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["element_id"],
            ["visual_elements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "element_id"),
    )

    op.create_index("ix_user_visual_elements_user_id", "user_visual_elements", ["user_id"])

    # 3. 创建 user_visual_configs 表
    op.create_table(
        "user_visual_configs",
        sa.Column("user_id", sa.GUID(), nullable=False),
        sa.Column("equipped_background_id", sa.String(50), nullable=True),
        sa.Column("equipped_particle_id", sa.String(50), nullable=True),
        sa.Column("equipped_effect_id", sa.String(50), nullable=True),
        sa.Column("background_equipped_at", sa.DateTime(), nullable=True),
        sa.Column("particle_equipped_at", sa.DateTime(), nullable=True),
        sa.Column("effect_equipped_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["equipped_background_id"],
            ["visual_elements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["equipped_particle_id"],
            ["visual_elements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["equipped_effect_id"],
            ["visual_elements.id"],
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_index("ix_user_visual_configs_user_id", "user_visual_configs", ["user_id"])

    # 4. 插入默认视觉元素数据
    _insert_default_elements()


def _insert_default_elements() -> None:
    """插入默认视觉元素"""
    from datetime import datetime

    conn = op.get_bind()

    # 背景层元素
    backgrounds = [
        {
            "id": "bg_default_dark",
            "name": "深邃夜空",
            "name_i18n": {"zh": "深邃夜空", "en": "Deep Night Sky"},
            "description": "默认深色渐变背景",
            "description_i18n": {"zh": "默认深色渐变背景", "en": "Default dark gradient background"},
            "element_type": "background",
            "rarity": "common",
            "unlock_source": "system",
            "is_default": True,
            "sort_order": 0,
            "category": "space",
            "config": {
                "gradient": {
                    "colors": ["#0a0a1a", "#1a1a2e", "#16213e"],
                    "begin": "topCenter",
                    "end": "bottomCenter",
                },
                "texture": None,
            },
        },
        {
            "id": "bg_aurora",
            "name": "极光之夜",
            "name_i18n": {"zh": "极光之夜", "en": "Aurora Night"},
            "description": "绿紫渐变极光背景",
            "description_i18n": {"zh": "绿紫渐变极光背景", "en": "Green-purple aurora gradient"},
            "element_type": "background",
            "rarity": "rare",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "streak_30"},
            "sort_order": 10,
            "category": "nature",
            "config": {
                "gradient": {
                    "colors": ["#0f0c29", "#302b63", "#24243e"],
                    "begin": "topCenter",
                    "end": "bottomCenter",
                },
                "aurora_colors": ["#00ff88", "#00ccff", "#ff00ff"],
            },
        },
        {
            "id": "bg_sunset",
            "name": "暮色余晖",
            "name_i18n": {"zh": "暮色余晖", "en": "Sunset Glow"},
            "description": "橙红暖色渐变背景",
            "description_i18n": {"zh": "橙红暖色渐变背景", "en": "Warm orange-red gradient"},
            "element_type": "background",
            "rarity": "rare",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "first_plan_complete"},
            "sort_order": 20,
            "category": "nature",
            "config": {
                "gradient": {
                    "colors": ["#ff7e5f", "#feb47b", "#ff6b6b"],
                    "begin": "topCenter",
                    "end": "bottomCenter",
                },
            },
        },
        {
            "id": "bg_nebula",
            "name": "星云漫游",
            "name_i18n": {"zh": "星云漫游", "en": "Nebula Wanderer"},
            "description": "紫色星云渐变背景",
            "description_i18n": {"zh": "紫色星云渐变背景", "en": "Purple nebula gradient"},
            "element_type": "background",
            "rarity": "epic",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "node_master_50"},
            "sort_order": 30,
            "category": "space",
            "config": {
                "gradient": {
                    "colors": ["#200122", "#6f0000", "#200122"],
                    "begin": "topCenter",
                    "end": "bottomCenter",
                },
                "nebula_colors": ["#8b5cf6", "#a855f7", "#d946ef"],
            },
        },
        {
            "id": "bg_cyberpunk",
            "name": "赛博朋克",
            "name_i18n": {"zh": "赛博朋克", "en": "Cyberpunk"},
            "description": "霓虹紫蓝渐变背景",
            "description_i18n": {"zh": "霓虹紫蓝渐变背景", "en": "Neon purple-blue gradient"},
            "element_type": "background",
            "rarity": "epic",
            "unlock_source": "shop",
            "unlock_requirement": {"price_photons": 200},
            "sort_order": 40,
            "category": "cyberpunk",
            "config": {
                "gradient": {
                    "colors": ["#0d0221", "#0f0728", "#1a0533"],
                    "begin": "topCenter",
                    "end": "bottomCenter",
                },
                "neon_colors": ["#ff00ff", "#00ffff", "#ffff00"],
            },
        },
    ]

    # 粒子层元素
    particles = [
        {
            "id": "particle_default_stars",
            "name": "繁星点点",
            "name_i18n": {"zh": "繁星点点", "en": "Twinkling Stars"},
            "description": "默认闪烁星星粒子",
            "description_i18n": {"zh": "默认闪烁星星粒子", "en": "Default twinkling stars"},
            "element_type": "particle",
            "rarity": "common",
            "unlock_source": "system",
            "is_default": True,
            "sort_order": 0,
            "category": "space",
            "config": {
                "count": 50,
                "shape": "star",
                "min_size": 1.0,
                "max_size": 3.0,
                "colors": ["#ffffff", "#ffd700", "#87ceeb"],
                "speed": 1.0,
                "drift": True,
                "twinkle": True,
                "fall_direction": None,
            },
        },
        {
            "id": "particle_cherry_blossom",
            "name": "樱花纷飞",
            "name_i18n": {"zh": "樱花纷飞", "en": "Cherry Blossoms"},
            "description": "粉色花瓣下落效果",
            "description_i18n": {"zh": "粉色花瓣下落效果", "en": "Falling pink petals"},
            "element_type": "particle",
            "rarity": "rare",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "spring_learner"},
            "sort_order": 10,
            "category": "nature",
            "season_start": "03-01",
            "season_end": "05-31",
            "config": {
                "count": 30,
                "shape": "petal",
                "min_size": 4.0,
                "max_size": 8.0,
                "colors": ["#ffb7c5", "#ffc0cb", "#ff69b4"],
                "speed": 0.8,
                "drift": True,
                "twinkle": False,
                "fall_direction": "down",
                "rotation": True,
            },
        },
        {
            "id": "particle_firefly",
            "name": "萤火虫",
            "name_i18n": {"zh": "萤火虫", "en": "Fireflies"},
            "description": "黄绿色闪烁漂浮效果",
            "description_i18n": {"zh": "黄绿色闪烁漂浮效果", "en": "Yellow-green floating glow"},
            "element_type": "particle",
            "rarity": "rare",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "summer_night_learner"},
            "sort_order": 20,
            "category": "nature",
            "season_start": "06-01",
            "season_end": "08-31",
            "config": {
                "count": 20,
                "shape": "circle",
                "min_size": 2.0,
                "max_size": 4.0,
                "colors": ["#90ee90", "#adff2f", "#ffff00"],
                "speed": 0.5,
                "drift": True,
                "twinkle": True,
                "twinkle_speed": 2.0,
                "fall_direction": None,
            },
        },
        {
            "id": "particle_snow",
            "name": "漫天飞雪",
            "name_i18n": {"zh": "漫天飞雪", "en": "Snowfall"},
            "description": "白色雪花飘落效果",
            "description_i18n": {"zh": "白色雪花飘落效果", "en": "Falling white snowflakes"},
            "element_type": "particle",
            "rarity": "rare",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "winter_learner"},
            "sort_order": 30,
            "category": "nature",
            "season_start": "12-01",
            "season_end": "02-28",
            "config": {
                "count": 60,
                "shape": "snowflake",
                "min_size": 2.0,
                "max_size": 5.0,
                "colors": ["#ffffff", "#f0f8ff", "#e6e6fa"],
                "speed": 1.2,
                "drift": True,
                "twinkle": False,
                "fall_direction": "down",
            },
        },
        {
            "id": "particle_energy",
            "name": "能量粒子",
            "name_i18n": {"zh": "能量粒子", "en": "Energy Particles"},
            "description": "多彩能量漂浮效果",
            "description_i18n": {"zh": "多彩能量漂浮效果", "en": "Colorful energy particles"},
            "element_type": "particle",
            "rarity": "epic",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "task_master_100"},
            "sort_order": 40,
            "category": "abstract",
            "config": {
                "count": 40,
                "shape": "circle",
                "min_size": 1.5,
                "max_size": 4.0,
                "colors": ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7"],
                "speed": 1.5,
                "drift": True,
                "twinkle": True,
                "fall_direction": None,
            },
        },
    ]

    # 特效层元素
    effects = [
        {
            "id": "effect_default_glow",
            "name": "柔光",
            "name_i18n": {"zh": "柔光", "en": "Soft Glow"},
            "description": "默认中心柔光效果",
            "description_i18n": {"zh": "默认中心柔光效果", "en": "Default center soft glow"},
            "element_type": "effect",
            "rarity": "common",
            "unlock_source": "system",
            "is_default": True,
            "sort_order": 0,
            "category": "ambient",
            "config": {
                "effect_type": "pulse_glow",
                "intensity": 0.3,
                "speed": 1.0,
                "color": "#ffffff",
                "position": "center",
                "radius": 200,
            },
        },
        {
            "id": "effect_pulse",
            "name": "脉动光环",
            "name_i18n": {"zh": "脉动光环", "en": "Pulsing Ring"},
            "description": "中心脉动光环效果",
            "description_i18n": {"zh": "中心脉动光环效果", "en": "Center pulsing ring effect"},
            "element_type": "effect",
            "rarity": "rare",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "level_10"},
            "sort_order": 10,
            "category": "ambient",
            "config": {
                "effect_type": "pulse_ring",
                "intensity": 0.6,
                "speed": 1.5,
                "color": "#4ecdc4",
                "position": "center",
                "radius": 150,
                "ring_count": 3,
            },
        },
        {
            "id": "effect_gravity_wave",
            "name": "引力波",
            "name_i18n": {"zh": "引力波", "en": "Gravity Wave"},
            "description": "涟漪扩散效果",
            "description_i18n": {"zh": "涟漪扩散效果", "en": "Ripple expansion effect"},
            "element_type": "effect",
            "rarity": "epic",
            "unlock_source": "achievement",
            "unlock_requirement": {"achievement_id": "node_master_100"},
            "sort_order": 20,
            "category": "space",
            "config": {
                "effect_type": "gravity_wave",
                "intensity": 0.8,
                "speed": 0.8,
                "color": "#8b5cf6",
                "position": "center",
                "wave_count": 5,
                "wave_interval": 2.0,
            },
        },
    ]

    # 插入所有元素
    all_elements = backgrounds + particles + effects
    now = datetime.utcnow()

    for element in all_elements:
        conn.execute(
            sa.text(
                """
                INSERT INTO visual_elements (
                    id, name, description, name_i18n, description_i18n,
                    element_type, rarity, unlock_source, unlock_requirement,
                    config, is_active, is_default, sort_order, category,
                    season_start, season_end, created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :name_i18n, :description_i18n,
                    :element_type, :rarity, :unlock_source, :unlock_requirement,
                    :config, :is_active, :is_default, :sort_order, :category,
                    :season_start, :season_end, :created_at, :updated_at
                )
                """
            ),
            {
                **element,
                "is_active": True,
                "is_default": element.get("is_default", False),
                "unlock_requirement": element.get("unlock_requirement"),
                "season_start": element.get("season_start"),
                "season_end": element.get("season_end"),
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    op.drop_table("user_visual_configs")
    op.drop_table("user_visual_elements")
    op.drop_table("visual_elements")

    # 删除枚举类型
    op.execute("DROP TYPE IF EXISTS visualelementtype")
    op.execute("DROP TYPE IF EXISTS visualelementrarity")
    op.execute("DROP TYPE IF EXISTS visualelementunlocksource")
