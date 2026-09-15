"""
更新现有学科数据，添加星域相关字段
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.subject import Subject


# 学科名称到星域的映射规则
SUBJECT_TO_SECTOR = {
    # COSMOS (理性星域) - 数学、物理、化学、天文、逻辑学
    "数学": "COSMOS",
    "物理": "COSMOS",
    "化学": "COSMOS",
    "天文": "COSMOS",
    "逻辑": "COSMOS",
    "统计": "COSMOS",

    # TECH (造物星域) - 计算机、工程、AI、建筑、制造
    "计算机": "TECH",
    "编程": "TECH",
    "工程": "TECH",
    "AI": "TECH",
    "人工智能": "TECH",
    "软件": "TECH",
    "硬件": "TECH",
    "建筑": "TECH",
    "机械": "TECH",

    # ART (灵感星域) - 设计、音乐、绘画、文学、ACG
    "设计": "ART",
    "音乐": "ART",
    "绘画": "ART",
    "美术": "ART",
    "文学": "ART",
    "动漫": "ART",
    "摄影": "ART",

    # CIVILIZATION (文明星域) - 历史、经济、政治、社会学、法律
    "历史": "CIVILIZATION",
    "经济": "CIVILIZATION",
    "政治": "CIVILIZATION",
    "社会": "CIVILIZATION",
    "法律": "CIVILIZATION",
    "管理": "CIVILIZATION",

    # LIFE (生活星域) - 健身、烹饪、医学、心理、理财
    "健身": "LIFE",
    "运动": "LIFE",
    "烹饪": "LIFE",
    "美食": "LIFE",
    "医学": "LIFE",
    "心理": "LIFE",
    "理财": "LIFE",
    "健康": "LIFE",

    # WISDOM (智慧星域) - 哲学、宗教、方法论、元认知
    "哲学": "WISDOM",
    "方法论": "WISDOM",
    "学习方法": "WISDOM",
    "思维": "WISDOM",
    "认知": "WISDOM",
}


def get_sector_color(sector_code: str) -> str:
    """获取星域颜色"""
    colors = {
        "COSMOS": "#00BFFF",
        "TECH": "#C0C0C0",
        "ART": "#FF00FF",
        "CIVILIZATION": "#FFD700",
        "LIFE": "#32CD32",
        "WISDOM": "#FFFFFF",
        "VOID": "#2F4F4F"
    }
    return colors.get(sector_code, "#808080")


def get_sector_glow_color(sector_code: str) -> str:
    """获取星域辉光颜色"""
    colors = {
        "COSMOS": "#87CEEB",
        "TECH": "#E8E8E8",
        "ART": "#FFB6C1",
        "CIVILIZATION": "#FFF8DC",
        "LIFE": "#90EE90",
        "WISDOM": "#F0F8FF",
        "VOID": "#696969"
    }
    return colors.get(sector_code, "#A0A0A0")


def get_sector_angle(sector_code: str) -> float:
    """获取星域角度"""
    angles = {
        "WISDOM": 0.0,          # 上 (12点)
        "COSMOS": 300.0,        # 左上 (10点)
        "TECH": 60.0,           # 右上 (2点)
        "ART": 240.0,           # 左下 (8点)
        "CIVILIZATION": 120.0,  # 右下 (4点)
        "LIFE": 180.0,          # 下 (6点)
        "VOID": 0.0
    }
    return angles.get(sector_code, 0.0)


def infer_sector(subject_name: str) -> str:
    """根据学科名称推断星域"""
    # 精确匹配
    if subject_name in SUBJECT_TO_SECTOR:
        return SUBJECT_TO_SECTOR[subject_name]

    # 模糊匹配
    for keyword, sector in SUBJECT_TO_SECTOR.items():
        if keyword in subject_name:
            return sector

    # 默认为 VOID
    return "VOID"


async def update_subjects():
    """更新所有学科的星域字段"""
    print("开始更新学科数据...")

    async with async_session_maker() as db:
        # 查询所有学科
        query = select(Subject)
        result = await db.execute(query)
        subjects = result.scalars().all()

        if not subjects:
            print("数据库中没有学科数据")
            return

        print(f"找到 {len(subjects)} 个学科")

        updated_count = 0
        for subject in subjects:
            # 如果已经有 sector_code，跳过
            if subject.sector_code:
                print(f"  跳过已有星域的学科: {subject.name} ({subject.sector_code})")
                continue

            # 推断星域
            sector_code = infer_sector(subject.name)

            # 更新字段
            subject.sector_code = sector_code
            subject.hex_color = get_sector_color(sector_code)
            subject.glow_color = get_sector_glow_color(sector_code)
            subject.position_angle = get_sector_angle(sector_code)

            updated_count += 1
            print(f"  更新学科: {subject.name} → {sector_code}")

        # 提交更改
        await db.commit()

        print(f"\n✅ 更新完成! 共更新 {updated_count} 个学科")

        # 显示统计
        print("\n星域分布:")
        for subject in subjects:
            print(f"  {subject.name}: {subject.sector_code}")


if __name__ == "__main__":
    asyncio.run(update_subjects())
