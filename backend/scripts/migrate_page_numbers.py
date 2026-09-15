"""
数据迁移脚本：page_number → page_numbers
用于修复 Phase 5B 迁移中可能丢失的页码数据

使用方法：
    cd backend && python scripts/migrate_page_numbers.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, Column, Integer, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from loguru import logger

from app.config import settings


async def check_old_schema():
    """检查是否还存在 page_number 列"""
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'document_chunks'
            AND column_name = 'page_number'
        """))

        return result.fetchone() is not None


async def migrate_from_backup():
    """
    从备份表或日志恢复数据
    如果 page_number 列已经删除，尝试从其他来源恢复
    """
    engine = create_engine(settings.DATABASE_URL)

    logger.info("检查是否有备份数据...")

    with engine.connect() as conn:
        # 检查是否有备份表
        backup_exists = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'document_chunks_backup_phase5b'
            )
        """)).scalar()

        if backup_exists:
            logger.info("发现备份表，开始从备份恢复...")
            # 从备份表恢复
            result = conn.execute(text("""
                UPDATE document_chunks dc
                SET page_numbers = jsonb_build_array(dcb.page_number)
                FROM document_chunks_backup_phase5b dcb
                WHERE dc.id = dcb.id
                AND dcb.page_number IS NOT NULL
                AND (dc.page_numbers IS NULL OR dc.page_numbers = 'null'::jsonb)
            """))
            conn.commit()
            logger.success(f"从备份恢复了 {result.rowcount} 条记录")
            return result.rowcount
        else:
            logger.warning("未找到备份表，无法恢复数据")
            logger.info("提示：如果迁移前有数据库备份，可以手动恢复")
            return 0


async def migrate_direct():
    """
    直接迁移：如果 page_number 列还存在
    """
    engine = create_engine(settings.DATABASE_URL)

    logger.info("开始直接迁移 page_number → page_numbers...")

    with engine.connect() as conn:
        # 迁移非空的 page_number 到 page_numbers
        result = conn.execute(text("""
            UPDATE document_chunks
            SET page_numbers = jsonb_build_array(page_number)
            WHERE page_number IS NOT NULL
            AND (page_numbers IS NULL OR page_numbers = 'null'::jsonb)
        """))

        conn.commit()
        rows_updated = result.rowcount

        logger.success(f"成功迁移 {rows_updated} 条记录")

        # 验证迁移结果
        verify_result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(page_numbers) as with_page_numbers,
                COUNT(page_number) as with_page_number
            FROM document_chunks
        """))

        stats = verify_result.fetchone()
        logger.info(
            f"迁移后统计：总记录 {stats[0]}，"
            f"有 page_numbers {stats[1]}，"
            f"有 page_number {stats[2]}"
        )

        return rows_updated


async def create_backup_if_possible():
    """
    如果 page_number 列还存在，先创建备份
    """
    has_old_column = await check_old_schema()

    if not has_old_column:
        logger.info("page_number 列已不存在，跳过备份")
        return False

    engine = create_engine(settings.DATABASE_URL)

    logger.info("创建备份表...")

    try:
        with engine.connect() as conn:
            # 创建备份表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS document_chunks_backup_phase5b AS
                SELECT id, file_id, chunk_index, page_number, created_at
                FROM document_chunks
                WHERE page_number IS NOT NULL
            """))
            conn.commit()

            # 统计备份记录数
            count_result = conn.execute(text("""
                SELECT COUNT(*) FROM document_chunks_backup_phase5b
            """))
            backup_count = count_result.scalar()

            logger.success(f"备份完成：{backup_count} 条记录")
            return True
    except Exception as e:
        logger.error(f"备份失败：{e}")
        return False


async def fix_existing_data():
    """
    修复已有数据：将单个数字转换为数组
    """
    engine = create_engine(settings.DATABASE_URL)

    logger.info("修复不正确的 page_numbers 格式...")

    with engine.connect() as conn:
        # 查找格式错误的记录（应该是数组但不是）
        result = conn.execute(text("""
            UPDATE document_chunks
            SET page_numbers = jsonb_build_array(page_numbers::int)
            WHERE page_numbers IS NOT NULL
            AND jsonb_typeof(page_numbers) = 'number'
        """))

        conn.commit()
        rows_fixed = result.rowcount

        if rows_fixed > 0:
            logger.success(f"修复了 {rows_fixed} 条格式错误的记录")

        return rows_fixed


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Phase 5B 数据迁移脚本：page_number → page_numbers")
    logger.info("=" * 60)

    # 步骤 1：检查旧列是否存在
    has_old_column = await check_old_schema()

    if has_old_column:
        logger.info("✓ 检测到 page_number 列还存在")

        # 步骤 2：创建备份
        backup_created = await create_backup_if_possible()

        # 步骤 3：执行直接迁移
        migrated_count = await migrate_direct()

        logger.success(f"迁移完成！共迁移 {migrated_count} 条记录")
        logger.info("提示：现在可以运行 Alembic 迁移来删除 page_number 列")
    else:
        logger.warning("✗ page_number 列已不存在")
        logger.info("尝试从备份恢复...")

        # 尝试从备份恢复
        recovered_count = await migrate_from_backup()

        if recovered_count > 0:
            logger.success(f"从备份恢复了 {recovered_count} 条记录")
        else:
            logger.warning("无法恢复数据。如果有数据库备份，请手动恢复。")

    # 步骤 4：修复格式错误的数据
    await fix_existing_data()

    # 步骤 5：最终验证
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_chunks,
                COUNT(page_numbers) as with_page_numbers,
                COUNT(*) FILTER (
                    WHERE page_numbers IS NOT NULL
                    AND jsonb_typeof(page_numbers) = 'array'
                ) as correct_format,
                COUNT(*) FILTER (
                    WHERE page_numbers IS NULL
                ) as missing_page_numbers
            FROM document_chunks
        """))

        stats = result.fetchone()

        logger.info("=" * 60)
        logger.info("最终统计：")
        logger.info(f"  总切片数：{stats[0]}")
        logger.info(f"  有 page_numbers：{stats[1]}")
        logger.info(f"  格式正确（数组）：{stats[2]}")
        logger.info(f"  缺失 page_numbers：{stats[3]}")

        if stats[3] > 0:
            logger.warning(f"  ⚠ 仍有 {stats[3]} 条记录缺失页码信息")
            logger.warning("  这些记录可能在迁移前就没有页码，或数据已丢失")
        else:
            logger.success("  ✓ 所有记录都有页码信息")

        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
