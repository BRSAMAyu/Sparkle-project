"""
加载种子数据到数据库
"""
import asyncio
import json
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.subject import Subject
from app.models.galaxy import KnowledgeNode
from app.services.embedding_service import embedding_service


async def load_seed_data():
    """加载种子数据"""
    print("开始加载种子数据...")

    seed_dir = Path(__file__).parent / "nodes"
    json_files = list(seed_dir.glob("*.json"))

    if not json_files:
        print("未找到种子数据文件")
        return

    async with async_session_maker() as db:
        for json_file in json_files:
            print(f"\n处理文件: {json_file.name}")

            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            sector_code = data.get("sector", "VOID")
            subject_name = data.get("subject_name", "未分类")
            nodes_data = data.get("nodes", [])

            # 1. 查找或创建学科
            query = select(Subject).where(Subject.sector_code == sector_code)
            result = await db.execute(query)
            subject = result.scalar_one_or_none()

            if not subject:
                # 创建新学科
                subject = Subject(
                    name=subject_name,
                    sector_code=sector_code,
                    hex_color=get_sector_color(sector_code),
                    glow_color=get_sector_glow_color(sector_code),
                    position_angle=get_sector_angle(sector_code)
                )
                db.add(subject)
                await db.flush()
                print(f"  创建学科: {subject_name} ({sector_code})")

            # 2. 创建知识节点
            for node_data in nodes_data:
                # 检查节点是否已存在
                existing_query = select(KnowledgeNode).where(
                    KnowledgeNode.name == node_data["name"]
                )
                existing_result = await db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    print(f"  跳过已存在的节点: {node_data['name']}")
                    continue

                # 生成向量嵌入
                embedding_text = f"{node_data['name']} {node_data.get('description', '')}"
                try:
                    embedding = await embedding_service.get_embedding(embedding_text)
                except Exception as e:
                    print(f"  警告：无法为节点 {node_data['name']} 生成向量: {e}")
                    embedding = None

                # 创建节点
                node = KnowledgeNode(
                    subject_id=subject.id,
                    name=node_data["name"],
                    name_en=node_data.get("name_en"),
                    description=node_data.get("description"),
                    importance_level=node_data.get("importance_level", 3),
                    is_seed=node_data.get("is_seed", True),
                    source_type="manual_seed",
                    keywords=node_data.get("keywords", []),
                    embedding=embedding
                )
                db.add(node)
                print(f"  创建节点: {node_data['name']}")

        await db.commit()
        print("\n✅ 种子数据加载完成!")


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
        "WISDOM": 0.0,      # 上 (12点)
        "COSMOS": 300.0,    # 左上 (10点)
        "TECH": 60.0,       # 右上 (2点)
        "ART": 240.0,       # 左下 (8点)
        "CIVILIZATION": 120.0,  # 右下 (4点)
        "LIFE": 180.0,      # 下 (6点)
        "VOID": 0.0
    }
    return angles.get(sector_code, 0.0)


if __name__ == "__main__":
    asyncio.run(load_seed_data())
