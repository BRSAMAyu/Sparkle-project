"""
Achievement Seed Data
成就系统初始数据 - 定义所有成就的配置
"""

INITIAL_ACHIEVEMENTS = [
    # ========== 连胜系列 ==========
    {
        "id": "streak_7",
        "name": "一周坚持",
        "description": "连续学习7天，养成学习习惯",
        "icon_url": "/icons/achievements/streak_7.png",
        "type": "streak",
        "rarity": "common",
        "trigger_code": "STREAK_DAYS",
        "trigger_config": {"days": 7},
        "category": "streak",
        "sort_order": 1,
        "visual_effect_type": "none",
        "reward_config": [
            {"type": "photon", "quantity": 50},
            {"type": "title", "value": "streak_7", "display": "一周坚持"}
        ]
    },
    {
        "id": "streak_30",
        "name": "月度冠军",
        "description": "连续学习30天，毅力可嘉",
        "icon_url": "/icons/achievements/streak_30.png",
        "type": "streak",
        "rarity": "rare",
        "trigger_code": "STREAK_DAYS",
        "trigger_config": {"days": 30},
        "prerequisites": ["streak_7"],
        "category": "streak",
        "sort_order": 2,
        "visual_effect_type": "gravity_wave",
        "visual_config": {
            "color": "#FFD700",
            "amplitude": 15,
            "frequency": 1.5
        },
        "reward_config": [
            {"type": "photon", "quantity": 200},
            {"type": "title", "value": "monthly_champion", "display": "月度冠军"}
        ]
    },
    {
        "id": "streak_100",
        "name": "百日征服",
        "description": "连续学习100天，成就非凡",
        "icon_url": "/icons/achievements/streak_100.png",
        "type": "streak",
        "rarity": "epic",
        "trigger_code": "STREAK_DAYS",
        "trigger_config": {"days": 100},
        "prerequisites": ["streak_30"],
        "category": "streak",
        "sort_order": 3,
        "visual_effect_type": "supernova",
        "visual_config": {
            "target_node_id": "core_star",
            "brightness": 2.5,
            "particle_count": 150
        },
        "reward_config": [
            {"type": "photon", "quantity": 500},
            {"type": "title", "value": "hundred_day_conqueror", "display": "百日征服"},
            {"type": "freeze_charge", "quantity": 1}
        ]
    },
    {
        "id": "streak_365",
        "name": "年度传说",
        "description": "连续学习365天，传奇不朽",
        "icon_url": "/icons/achievements/streak_365.png",
        "type": "streak",
        "rarity": "legendary",
        "trigger_code": "STREAK_DAYS",
        "trigger_config": {"days": 365},
        "prerequisites": ["streak_100"],
        "category": "streak",
        "sort_order": 4,
        "visual_effect_type": "black_hole",
        "visual_config": {
            "target_node_id": "core_star",
            "event_horizon_color": "#000000",
            "accretion_disk_colors": ["#FF6B00", "#FFD700", "#FFFFFF"],
            "glow_intensity": 3.0
        },
        "reward_config": [
            {"type": "photon", "quantity": 2000},
            {"type": "title", "value": "yearly_legend", "display": "年度传说"},
            {"type": "freeze_charge", "quantity": 3},
            {"type": "galaxy_skin", "skin_id": "legendary_anniversary"}
        ]
    },

    # ========== 知识探索系列 ==========
    {
        "id": "first_light",
        "name": "初次点亮",
        "description": "解锁第一个知识点",
        "icon_url": "/icons/achievements/first_light.png",
        "type": "node_explore",
        "rarity": "common",
        "trigger_code": "NODES_UNLOCKED",
        "trigger_config": {"count": 1},
        "category": "exploration",
        "sort_order": 10,
        "reward_config": [
            {"type": "photon", "quantity": 10}
        ]
    },
    {
        "id": "nodes_10",
        "name": "星火燎原",
        "description": "解锁10个知识点",
        "icon_url": "/icons/achievements/nodes_10.png",
        "type": "node_explore",
        "rarity": "common",
        "trigger_code": "NODES_UNLOCKED",
        "trigger_config": {"count": 10},
        "prerequisites": ["first_light"],
        "category": "exploration",
        "sort_order": 11,
        "reward_config": [
            {"type": "photon", "quantity": 30}
        ]
    },
    {
        "id": "nodes_50",
        "name": "知识新星",
        "description": "解锁50个知识点",
        "icon_url": "/icons/achievements/nodes_50.png",
        "type": "node_explore",
        "rarity": "common",
        "trigger_code": "NODES_UNLOCKED",
        "trigger_config": {"count": 50},
        "prerequisites": ["nodes_10"],
        "category": "exploration",
        "sort_order": 12,
        "reward_config": [
            {"type": "photon", "quantity": 100}
        ]
    },
    {
        "id": "nodes_100",
        "name": "星图探索者",
        "description": "解锁100个知识点",
        "icon_url": "/icons/achievements/nodes_100.png",
        "type": "node_explore",
        "rarity": "rare",
        "trigger_code": "NODES_UNLOCKED",
        "trigger_config": {"count": 100},
        "prerequisites": ["nodes_50"],
        "category": "exploration",
        "sort_order": 13,
        "reward_config": [
            {"type": "photon", "quantity": 200},
            {"type": "title", "value": "galaxy_explorer", "display": "星图探索者"}
        ]
    },
    {
        "id": "nodes_500",
        "name": "知识领航员",
        "description": "解锁500个知识点",
        "icon_url": "/icons/achievements/nodes_500.png",
        "type": "node_explore",
        "rarity": "epic",
        "trigger_code": "NODES_UNLOCKED",
        "trigger_config": {"count": 500},
        "prerequisites": ["nodes_100"],
        "category": "exploration",
        "sort_order": 14,
        "visual_effect_type": "nebula_transform",
        "visual_config": {
            "skin_id": "explorer_nebula",
            "colors": ["#00BFFF", "#1E90FF", "#4169E1"]
        },
        "reward_config": [
            {"type": "photon", "quantity": 1000},
            {"type": "title", "value": "knowledge_navigator", "display": "知识领航员"},
            {"type": "function", "feature": "advanced_analytics", "name": "高级数据分析"}
        ]
    },
    {
        "id": "all_sectors",
        "name": "全域精通",
        "description": "解锁所有7个星域的知识点",
        "icon_url": "/icons/achievements/all_sectors.png",
        "type": "node_explore",
        "rarity": "legendary",
        "trigger_code": "ALL_SECTORS_UNLOCKED",
        "trigger_config": {"sectors": ["math", "physics", "chemistry", "biology", "cs", "literature", "history"]},
        "category": "exploration",
        "sort_order": 15,
        "visual_effect_type": "galaxy_skin",
        "visual_config": {
            "skin_id": "full_mastery_galaxy",
            "background_gradient": ["#0A0A23", "#1A1A4A", "#2D1B69"],
            "star_colors": ["#00FFFF", "#FF00FF", "#FFFF00"],
            "glow_color": "#FFFFFF"
        },
        "reward_config": [
            {"type": "photon", "quantity": 5000},
            {"type": "title", "value": "omniscient", "display": "博学之士"}
        ]
    },

    # ========== 领域精通系列 ==========
    {
        "id": "math_master",
        "name": "数学大师",
        "description": "数学领域掌握度达到80%",
        "icon_url": "/icons/achievements/math_master.png",
        "type": "mastery",
        "rarity": "epic",
        "trigger_code": "SECTOR_MASTERY",
        "trigger_config": {"sector": "math", "percent": 80, "count": 20},
        "category": "mastery",
        "sort_order": 20,
        "reward_config": [
            {"type": "ai_persona", "persona_id": "mathematician", "trigger_keywords": ["数学", "公式", "证明"]},
            {"type": "title", "value": "math_master", "display": "数学大师"}
        ]
    },
    {
        "id": "physics_master",
        "name": "物理大师",
        "description": "物理领域掌握度达到80%",
        "icon_url": "/icons/achievements/physics_master.png",
        "type": "mastery",
        "rarity": "epic",
        "trigger_code": "SECTOR_MASTERY",
        "trigger_config": {"sector": "physics", "percent": 80, "count": 20},
        "category": "mastery",
        "sort_order": 21,
        "reward_config": [
            {"type": "ai_persona", "persona_id": "physicist", "trigger_keywords": ["物理", "力学", "能量"]},
            {"type": "title", "value": "physics_master", "display": "物理大师"}
        ]
    },

    # ========== 学习时长系列 ==========
    {
        "id": "study_1hour",
        "name": "学习一小时",
        "description": "累计学习时长达到1小时",
        "icon_url": "/icons/achievements/study_1hour.png",
        "type": "study_time",
        "rarity": "common",
        "trigger_code": "STUDY_MINUTES_TOTAL",
        "trigger_config": {"minutes": 60},
        "category": "study_time",
        "sort_order": 30,
        "reward_config": [
            {"type": "photon", "quantity": 20}
        ]
    },
    {
        "id": "study_10hours",
        "name": "学习十小时",
        "description": "累计学习时长达到10小时",
        "icon_url": "/icons/achievements/study_10hours.png",
        "type": "study_time",
        "rarity": "common",
        "trigger_code": "STUDY_MINUTES_TOTAL",
        "trigger_config": {"minutes": 600},
        "prerequisites": ["study_1hour"],
        "category": "study_time",
        "sort_order": 31,
        "reward_config": [
            {"type": "photon", "quantity": 100}
        ]
    },
    {
        "id": "study_100hours",
        "name": "学习百小时",
        "description": "累计学习时长达到100小时",
        "icon_url": "/icons/achievements/study_100hours.png",
        "type": "study_time",
        "rarity": "rare",
        "trigger_code": "STUDY_MINUTES_TOTAL",
        "trigger_config": {"minutes": 6000},
        "prerequisites": ["study_10hours"],
        "category": "study_time",
        "sort_order": 32,
        "reward_config": [
            {"type": "photon", "quantity": 500},
            {"type": "title", "value": "dedicated_learner", "display": "勤奋学习者"}
        ]
    },
    {
        "id": "study_1000hours",
        "name": "学习千小时",
        "description": "累计学习时长达到1000小时",
        "icon_url": "/icons/achievements/study_1000hours.png",
        "type": "study_time",
        "rarity": "legendary",
        "trigger_code": "STUDY_MINUTES_TOTAL",
        "trigger_config": {"minutes": 60000},
        "prerequisites": ["study_100hours"],
        "category": "study_time",
        "sort_order": 33,
        "visual_effect_type": "black_hole",
        "reward_config": [
            {"type": "photon", "quantity": 5000},
            {"type": "title", "value": "thousand_hour_master", "display": "千小时大师"}
        ]
    },

    # ========== 任务完成系列 ==========
    {
        "id": "tasks_1",
        "name": "第一任务",
        "description": "完成第一个学习任务",
        "icon_url": "/icons/achievements/tasks_1.png",
        "type": "task_complete",
        "rarity": "common",
        "trigger_code": "TASKS_TOTAL",
        "trigger_config": {"count": 1},
        "category": "tasks",
        "sort_order": 40,
        "reward_config": [
            {"type": "photon", "quantity": 10}
        ]
    },
    {
        "id": "tasks_10",
        "name": "任务达人",
        "description": "完成10个学习任务",
        "icon_url": "/icons/achievements/tasks_10.png",
        "type": "task_complete",
        "rarity": "common",
        "trigger_code": "TASKS_TOTAL",
        "trigger_config": {"count": 10},
        "prerequisites": ["tasks_1"],
        "category": "tasks",
        "sort_order": 41,
        "reward_config": [
            {"type": "photon", "quantity": 50}
        ]
    },
    {
        "id": "tasks_100",
        "name": "任务专家",
        "description": "完成100个学习任务",
        "icon_url": "/icons/achievements/tasks_100.png",
        "type": "task_complete",
        "rarity": "rare",
        "trigger_code": "TASKS_TOTAL",
        "trigger_config": {"count": 100},
        "prerequisites": ["tasks_10"],
        "category": "tasks",
        "sort_order": 42,
        "reward_config": [
            {"type": "photon", "quantity": 300},
            {"type": "title", "value": "task_expert", "display": "任务专家"}
        ]
    },

    # ========== 隐藏成就 ==========
    {
        "id": "night_owl",
        "name": "深夜学者",
        "description": "在深夜23:00-05:00时段学习10次",
        "icon_url": "/icons/achievements/night_owl.png",
        "type": "hidden",
        "rarity": "epic",
        "is_hidden": True,
        "hint": "夜猫子的秘密...在深夜学习会有意外收获",
        "trigger_code": "NIGHT_OWL_STUDY",
        "trigger_config": {"sessions": 10},
        "category": "hidden",
        "sort_order": 100,
        "reward_config": [
            {"type": "avatar_frame", "asset_url": "/frames/night_owl.png", "rarity": "epic"},
            {"type": "title", "value": "night_owl", "display": "深夜学者"}
        ]
    },
    {
        "id": "early_bird",
        "name": "早起鸟儿",
        "description": "在清晨05:00-08:00时段学习10次",
        "icon_url": "/icons/achievements/early_bird.png",
        "type": "hidden",
        "rarity": "epic",
        "is_hidden": True,
        "hint": "一日之计在于晨",
        "trigger_code": "EARLY_BIRD",
        "trigger_config": {"sessions": 10},
        "category": "hidden",
        "sort_order": 101,
        "reward_config": [
            {"type": "title", "value": "early_bird", "display": "早起鸟儿"}
        ]
    },
    {
        "id": "perfectionist",
        "name": "完美主义者",
        "description": "单个知识点掌握度达到100%",
        "icon_url": "/icons/achievements/perfectionist.png",
        "type": "hidden",
        "rarity": "rare",
        "is_hidden": True,
        "hint": "追求完美...",
        "trigger_code": "PERFECTIONIST",
        "trigger_config": {"mastery": 100},
        "category": "hidden",
        "sort_order": 102,
        "reward_config": [
            {"type": "title", "value": "perfectionist", "display": "完美主义者"}
        ]
    },
    {
        "id": "speed_learner",
        "name": "速通大师",
        "description": "24小时内解锁20个新知识点",
        "icon_url": "/icons/achievements/speed_learner.png",
        "type": "hidden",
        "rarity": "epic",
        "is_hidden": True,
        "hint": "效率至上...",
        "trigger_code": "SPEED_UNLOCK",
        "trigger_config": {"count": 20, "hours": 24},
        "category": "hidden",
        "sort_order": 103,
        "visual_effect_type": "supernova",
        "visual_config": {
            "particle_count": 100,
            "expansion_speed": 2.0
        },
        "reward_config": [
            {"type": "title", "value": "speed_learner", "display": "速通大师"}
        ]
    },
    {
        "id": "weekend_warrior",
        "name": "周末战士",
        "description": "连续4个周末都有学习记录",
        "icon_url": "/icons/achievements/weekend_warrior.png",
        "type": "hidden",
        "rarity": "rare",
        "is_hidden": True,
        "hint": "周末也不休息...",
        "trigger_code": "WEEKEND_WARRIOR",
        "trigger_config": {"consecutive_weekends": 4},
        "category": "hidden",
        "sort_order": 104,
        "reward_config": [
            {"type": "title", "value": "weekend_warrior", "display": "周末战士"}
        ]
    },

    # ========== 冲刺成就系列 ==========
    {
        "id": "sprint_first",
        "name": "初出茅庐",
        "description": "完成第一个冲刺计划",
        "icon_url": "/icons/achievements/sprint_first.png",
        "type": "sprint",
        "rarity": "common",
        "trigger_code": "SPRINTS_TOTAL",
        "trigger_config": {"count": 1},
        "category": "sprint",
        "sort_order": 50,
        "reward_config": [
            {"type": "photon", "quantity": 50},
            {"type": "title", "value": "sprint_first", "display": "初出茅庐"}
        ]
    },
    {
        "id": "sprint_5",
        "name": "冲刺能手",
        "description": "完成5个冲刺计划",
        "icon_url": "/icons/achievements/sprint_5.png",
        "type": "sprint",
        "rarity": "common",
        "trigger_code": "SPRINTS_TOTAL",
        "trigger_config": {"count": 5},
        "prerequisites": ["sprint_first"],
        "category": "sprint",
        "sort_order": 51,
        "reward_config": [
            {"type": "photon", "quantity": 100}
        ]
    },
    {
        "id": "sprint_10",
        "name": "冲刺大师",
        "description": "完成10个冲刺计划",
        "icon_url": "/icons/achievements/sprint_10.png",
        "type": "sprint",
        "rarity": "rare",
        "trigger_code": "SPRINTS_TOTAL",
        "trigger_config": {"count": 10},
        "prerequisites": ["sprint_5"],
        "category": "sprint",
        "sort_order": 52,
        "visual_effect_type": "gravity_wave",
        "visual_config": {
            "color": "#FFD700",
            "amplitude": 15,
            "frequency": 1.5
        },
        "reward_config": [
            {"type": "photon", "quantity": 200},
            {"type": "title", "value": "sprint_master", "display": "冲刺大师"}
        ]
    },
    {
        "id": "sprint_perfect_1",
        "name": "完美首秀",
        "description": "以100%完成率完成第一个冲刺",
        "icon_url": "/icons/achievements/sprint_perfect_1.png",
        "type": "sprint",
        "rarity": "rare",
        "trigger_code": "SPRINT_PERFECT",
        "trigger_config": {"count": 1},
        "category": "sprint",
        "sort_order": 53,
        "visual_effect_type": "supernova",
        "visual_config": {
            "particle_count": 50,
            "expansion_speed": 1.5
        },
        "reward_config": [
            {"type": "photon", "quantity": 150},
            {"type": "title", "value": "perfect_debut", "display": "完美首秀"}
        ]
    },
    {
        "id": "sprint_perfect_5",
        "name": "完美主义",
        "description": "以100%完成率完成5个冲刺",
        "icon_url": "/icons/achievements/sprint_perfect_5.png",
        "type": "sprint",
        "rarity": "epic",
        "trigger_code": "SPRINT_PERFECT",
        "trigger_config": {"count": 5},
        "prerequisites": ["sprint_perfect_1"],
        "category": "sprint",
        "sort_order": 54,
        "visual_effect_type": "nebula_transform",
        "visual_config": {
            "skin_id": "perfect_nebula",
            "colors": ["#FFD700", "#FFA500", "#FF8C00"]
        },
        "reward_config": [
            {"type": "photon", "quantity": 500},
            {"type": "title", "value": "perfectionist", "display": "完美主义者"},
            {"type": "freeze_charge", "quantity": 1}
        ]
    },
    {
        "id": "sprint_streak_3",
        "name": "三连胜",
        "description": "连续完成3个冲刺计划",
        "icon_url": "/icons/achievements/sprint_streak_3.png",
        "type": "sprint",
        "rarity": "rare",
        "trigger_code": "SPRINTS_STREAK",
        "trigger_config": {"streak": 3},
        "category": "sprint",
        "sort_order": 55,
        "visual_effect_type": "gravity_wave",
        "visual_config": {
            "color": "#00BFFF",
            "amplitude": 20,
            "frequency": 2.0
        },
        "reward_config": [
            {"type": "photon", "quantity": 200},
            {"type": "title", "value": "triple_winner", "display": "三连胜"}
        ]
    },
    {
        "id": "sprint_streak_10",
        "name": "冲刺传奇",
        "description": "连续完成10个冲刺计划",
        "icon_url": "/icons/achievements/sprint_streak_10.png",
        "type": "sprint",
        "rarity": "legendary",
        "trigger_code": "SPRINTS_STREAK",
        "trigger_config": {"streak": 10},
        "prerequisites": ["sprint_streak_3"],
        "category": "sprint",
        "sort_order": 56,
        "visual_effect_type": "black_hole",
        "visual_config": {
            "target_node_id": "sprint_core",
            "event_horizon_color": "#000000",
            "accretion_disk_colors": ["#FF4500", "#FFD700", "#FFFFFF"],
            "glow_intensity": 3.0
        },
        "reward_config": [
            {"type": "photon", "quantity": 2000},
            {"type": "title", "value": "sprint_legend", "display": "冲刺传奇"},
            {"type": "freeze_charge", "quantity": 3},
            {"type": "galaxy_skin", "skin_id": "sprint_legend_galaxy"}
        ]
    },
    {
        "id": "sprint_ahead",
        "name": "超前完成",
        "description": "提前完成冲刺计划（在目标日期前达到100%进度）",
        "icon_url": "/icons/achievements/sprint_ahead.png",
        "type": "sprint",
        "rarity": "epic",
        "trigger_code": "SPRINT_AHEAD",
        "trigger_config": {"count": 1},
        "category": "sprint",
        "sort_order": 57,
        "visual_effect_type": "supernova",
        "visual_config": {
            "particle_count": 100,
            "expansion_speed": 2.5
        },
        "reward_config": [
            {"type": "photon", "quantity": 300},
            {"type": "title", "value": "ahead_runner", "display": "领跑者"}
        ]
    },
]

# 初始星系皮肤数据
INITIAL_GALAXY_SKINS = [
    {
        "id": "default",
        "name": "经典星系",
        "description": "默认的星系主题，宁静深邃",
        "unlock_type": "default",
        "rarity": "common",
        "sort_order": 0,
        "skin_config": {
            "background_gradient": ["#0A0A1A", "#1A1A3A", "#2A2A4A"],
            "star_colors": ["#FFFFFF", "#FFFFF0", "#F0F0FF"],
            "glow_color": "#FFFFFF",
            "grid_style": "circular"
        }
    },
    {
        "id": "nebula_purple",
        "name": "紫色星云",
        "description": "神秘的紫色星云主题",
        "unlock_type": "achievement",
        "unlock_requirement": {"achievement_id": "nodes_100"},
        "rarity": "rare",
        "sort_order": 1,
        "skin_config": {
            "background_gradient": ["#1A0A2E", "#2D1B69", "#4B2B8A"],
            "star_colors": ["#DDA0DD", "#DA70D6", "#FF00FF"],
            "glow_color": "#DDA0DD",
            "grid_style": "hexagonal"
        }
    },
    {
        "id": "golden_galaxy",
        "name": "金色银河",
        "description": "辉煌的金色星系主题",
        "unlock_type": "achievement",
        "unlock_requirement": {"achievement_id": "streak_100"},
        "rarity": "epic",
        "sort_order": 2,
        "skin_config": {
            "background_gradient": ["#1A1A0A", "#3A3A1A", "#4A4A2A"],
            "star_colors": ["#FFD700", "FFA500", "#FF8C00"],
            "glow_color": "#FFD700",
            "grid_style": "radial"
        }
    },
    {
        "id": "cyberpunk",
        "name": "赛博朋克",
        "description": "霓虹闪烁的赛博朋克风格",
        "unlock_type": "achievement",
        "unlock_requirement": {"achievement_id": "study_1000hours"},
        "rarity": "legendary",
        "sort_order": 3,
        "skin_config": {
            "background_gradient": ["#000000", "#0A0A23", "#150033"],
            "star_colors": ["#00FFFF", "#FF00FF", "#FFFF00"],
            "glow_color": "#00FFFF",
            "grid_style": "hexagonal",
            "particle_texture": "digital_rain"
        }
    },
    {
        "id": "explorer_nebula",
        "name": "探索者星云",
        "description": "解锁500个知识点后获得",
        "unlock_type": "achievement",
        "unlock_requirement": {"achievement_id": "nodes_500"},
        "rarity": "epic",
        "sort_order": 4,
        "skin_config": {
            "background_gradient": ["#0A0A1A", "#1E3A5F", "#2D5A7F"],
            "star_colors": ["#00BFFF", "#1E90FF", "#4169E1"],
            "glow_color": "#00BFFF",
            "grid_style": "spiral"
        }
    },
    {
        "id": "legendary_anniversary",
        "name": "周年纪念",
        "description": "连续学习365天获得",
        "unlock_type": "achievement",
        "unlock_requirement": {"achievement_id": "streak_365"},
        "rarity": "legendary",
        "sort_order": 5,
        "skin_config": {
            "background_gradient": ["#1A0A0A", "#3A1A1A", "#5A2A2A"],
            "star_colors": ["#FF4500", "#FF6347", "#FFD700"],
            "glow_color": "#FFD700",
            "grid_style": "circular",
            "special_effects": ["anniversary_confetti", "rainbow_trail"]
        }
    },
]
