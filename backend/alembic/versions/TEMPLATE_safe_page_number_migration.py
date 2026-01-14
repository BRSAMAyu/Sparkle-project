"""
TEMPLATE: 安全的 page_number → page_numbers 迁移
这是一个改进的迁移模板，包含数据迁移逻辑

⚠️ 注意：这是模板文件，不会被 Alembic 自动执行
如果需要重新迁移，请复制此模板并修改 revision ID
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers - 如果实际使用，需要修改这些
revision: str = 'TEMPLATE_SAFE_MIGRATION'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    安全的升级流程：
    1. 添加新列
    2. 迁移数据
    3. 验证数据
    4. 删除旧列
    """
    connection = op.get_bind()

    # Step 1: 添加新列（允许 NULL）
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('page_numbers', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('bbox', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('quality_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('pipeline_version', sa.String(length=50), nullable=True))

    print("✓ 新列已添加")

    # Step 2: 迁移数据（关键步骤！）
    print("开始迁移 page_number 数据...")

    # 使用原生 SQL 进行数据迁移
    connection.execute(sa.text("""
        UPDATE document_chunks
        SET page_numbers = jsonb_build_array(page_number)
        WHERE page_number IS NOT NULL
    """))

    print("✓ 数据迁移完成")

    # Step 3: 验证数据
    result = connection.execute(sa.text("""
        SELECT
            COUNT(*) as total,
            COUNT(page_number) as old_column_count,
            COUNT(page_numbers) as new_column_count
        FROM document_chunks
    """))

    stats = result.fetchone()
    print(f"验证结果：总记录 {stats[0]}, 旧列有值 {stats[1]}, 新列有值 {stats[2]}")

    if stats[1] != stats[2]:
        raise Exception(
            f"数据迁移验证失败！旧列有 {stats[1]} 条记录，但新列只有 {stats[2]} 条记录。"
        )

    print("✓ 数据验证通过")

    # Step 4: 删除旧列
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.drop_column('page_number')

    print("✓ 旧列已删除")

    # Step 5: 更新索引
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        # 删除旧索引（如果存在）
        try:
            batch_op.drop_index('idx_document_chunks_chunk_index')
        except:
            pass

        try:
            batch_op.drop_index('idx_document_chunks_deleted_at')
        except:
            pass

        try:
            batch_op.drop_index('idx_document_chunks_file_id')
        except:
            pass

        try:
            batch_op.drop_index('idx_document_chunks_user_id')
        except:
            pass

        # 创建新索引
        batch_op.create_index(
            batch_op.f('ix_document_chunks_deleted_at'),
            ['deleted_at'],
            unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_document_chunks_file_id'),
            ['file_id'],
            unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_document_chunks_user_id'),
            ['user_id'],
            unique=False
        )
        batch_op.create_index(
            batch_op.f('idx_document_chunks_chunk_index'),
            ['file_id', 'chunk_index'],
            unique=True
        )

    print("✓ 索引已更新")
    print("🎉 迁移完成！")


def downgrade() -> None:
    """
    降级流程：恢复旧结构
    ⚠️ 注意：降级会丢失多页切片信息（page_numbers 是数组，page_number 是单个值）
    """
    connection = op.get_bind()

    # Step 1: 添加回旧列
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('page_number', sa.INTEGER(), autoincrement=False, nullable=True)
        )

    print("✓ 旧列已添加回来")

    # Step 2: 尝试恢复数据（只取第一个页码）
    print("开始恢复数据...")

    connection.execute(sa.text("""
        UPDATE document_chunks
        SET page_number = (page_numbers->0)::int
        WHERE page_numbers IS NOT NULL
        AND jsonb_array_length(page_numbers) > 0
    """))

    print("⚠ 数据已恢复到旧格式（多页切片只保留了第一页）")

    # Step 3: 删除新列
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.drop_column('pipeline_version')
        batch_op.drop_column('quality_score')
        batch_op.drop_column('bbox')
        batch_op.drop_column('page_numbers')

    print("✓ 新列已删除")
    print("🎉 降级完成！")


# ==========================================
# 使用说明
# ==========================================
"""
如果需要实际使用此模板：

1. 复制此文件并重命名：
   cp TEMPLATE_safe_page_number_migration.py xxxx_safe_page_migration.py

2. 生成新的 revision ID：
   alembic revision --autogenerate -m "safe page migration"

3. 将此模板的 upgrade() 和 downgrade() 复制到新生成的文件

4. 运行迁移：
   alembic upgrade head

5. 验证结果：
   python scripts/migrate_page_numbers.py
"""
