"""P1.3: Refactor error book to Phase 4 schema.

Revision ID: p1_3_error_book_refactor
Revises: p1_2_error_book
Create Date: 2026-01-02 17:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# revision identifiers, used by Alembic.
revision = 'p1_3_error_book_refactor'
down_revision = 'p1_2_error_book'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Drop old auxiliary tables
    op.drop_table('error_knowledge_links')
    op.drop_table('error_reviews')
    op.drop_table('error_analyses')
    
    # 2. Alter error_records table
    # Rename subject -> subject_code
    op.alter_column('error_records', 'subject', new_column_name='subject_code')
    
    # Make text fields nullable (for OCR fallback)
    op.alter_column('error_records', 'question_text', nullable=True)
    op.alter_column('error_records', 'user_answer', nullable=True)
    op.alter_column('error_records', 'correct_answer', nullable=True)
    
    # Add new columns
    op.add_column('error_records', sa.Column('easiness_factor', sa.Float, server_default='2.5'))
    op.add_column('error_records', sa.Column('interval_days', sa.Float, server_default='0.0'))
    
    op.add_column('error_records', sa.Column('latest_analysis', JSONB, nullable=True))
    
    op.add_column('error_records', sa.Column('linked_knowledge_node_ids', ARRAY(UUID(as_uuid=True)), server_default='{}'))
    op.add_column('error_records', sa.Column('suggested_concepts', ARRAY(sa.Text), server_default='{}'))
    
    # 3. Create new optimized index
    # idx_errors_user_review: (user_id, next_review_at) where mastery_level < 1.0
    op.create_index(
        'idx_errors_user_review', 
        'error_records', 
        ['user_id', 'next_review_at'], 
        postgresql_where=sa.text('mastery_level < 1.0')
    )
    
    # Ensure subject_code index exists (was idx_errors_user_subject, now we might want just subject_code or keep the compound)
    # The old index was idx_errors_user_subject on (user_id, subject). 
    # The new model defines idx_errors_subject on (subject_code).
    # Let's create the specific one for stats grouping.
    op.create_index('idx_errors_subject_code', 'error_records', ['subject_code'])

def downgrade():
    # Reverse of upgrade
    
    # 1. Drop new indexes
    op.drop_index('idx_errors_subject_code', table_name='error_records')
    op.drop_index('idx_errors_user_review', table_name='error_records')
    
    # 2. Remove new columns
    op.drop_column('error_records', 'suggested_concepts')
    op.drop_column('error_records', 'linked_knowledge_node_ids')
    op.drop_column('error_records', 'latest_analysis')
    op.drop_column('error_records', 'interval_days')
    op.drop_column('error_records', 'easiness_factor')
    
    # 3. Revert column changes
    # Rename subject_code -> subject
    op.alter_column('error_records', 'subject_code', new_column_name='subject')

    # Revert nullability
    # Note: We execute raw SQL to handle potential NULLs before setting NOT NULL
    op.execute("UPDATE error_records SET correct_answer = '' WHERE correct_answer IS NULL")
    op.alter_column('error_records', 'correct_answer', nullable=False)
    
    op.execute("UPDATE error_records SET user_answer = '' WHERE user_answer IS NULL")
    op.alter_column('error_records', 'user_answer', nullable=False)
    
    op.execute("UPDATE error_records SET question_text = '' WHERE question_text IS NULL")
    op.alter_column('error_records', 'question_text', nullable=False)
    
    # 4. Recreate old tables
    
    # error_analyses
    op.create_table(
        'error_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('error_id', UUID(as_uuid=True), sa.ForeignKey('error_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_result', JSONB, nullable=False, comment='AI分析结果JSON'),
        sa.Column('model_used', sa.String(50), comment='使用的LLM模型'),
        sa.Column('confidence', sa.Float, comment='AI置信度0-1'),
        sa.Column('processing_time_ms', sa.Integer, comment='处理耗时毫秒'),
        sa.Column('user_rating', sa.Integer, nullable=True, comment='用户评分1-5'),
        sa.Column('user_feedback', sa.Text, nullable=True, comment='用户反馈文本'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_analyses_error', 'error_analyses', ['error_id'])

    # error_reviews
    op.create_table(
        'error_reviews',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('error_id', UUID(as_uuid=True), sa.ForeignKey('error_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('performance', sa.String(20), nullable=False, comment='复习表现'),
        sa.Column('time_spent_seconds', sa.Integer, nullable=True, comment='花费时间秒'),
        sa.Column('review_type', sa.String(20), default='active', comment='active/passive'),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_reviews_error', 'error_reviews', ['error_id'])
    op.create_index('idx_reviews_user_time', 'error_reviews', ['user_id', 'reviewed_at'])

    # error_knowledge_links
    op.create_table(
        'error_knowledge_links',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('error_id', UUID(as_uuid=True), sa.ForeignKey('error_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('knowledge_node_id', UUID(as_uuid=True), sa.ForeignKey('knowledge_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relevance', sa.Float, default=1.0, comment='关联强度0-1'),
        sa.Column('is_primary', sa.Boolean, default=False, comment='是否为主要关联知识点'),
        sa.Column('linked_by', sa.String(20), default='ai', comment='关联方式：ai/manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_error_knowledge', 'error_knowledge_links', ['error_id', 'knowledge_node_id'])
    op.create_index('idx_ekl_knowledge', 'error_knowledge_links', ['knowledge_node_id'])
