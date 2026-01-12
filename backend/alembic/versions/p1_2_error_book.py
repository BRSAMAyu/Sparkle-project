"""P1.2: Create error book tables.

Revision ID: p1_2_error_book
Revises: p3_add_node_positions
Create Date: 2026-01-02 16:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'p1_2_error_book'
down_revision = 'p3_add_node_positions'
branch_labels = None
depends_on = None

def upgrade():
    # ============================================
    # 表1: error_records (错题主表)
    # ============================================
    op.create_table(
        'error_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        
        # 题目内容
        sa.Column('question_text', sa.Text, nullable=False, comment='题目原文'),
        sa.Column('question_image_url', sa.String(500), nullable=True, comment='题目图片URL（可选）'),
        sa.Column('user_answer', sa.Text, nullable=False, comment='用户的错误答案'),
        sa.Column('correct_answer', sa.Text, nullable=False, comment='正确答案'),
        
        # 分类与元数据
        sa.Column('subject', sa.String(50), nullable=False, comment='科目'),
        sa.Column('chapter', sa.String(100), nullable=True, comment='章节（可选）'),
        sa.Column('source', sa.String(50), default='manual', comment='来源'),
        sa.Column('difficulty', sa.Integer, nullable=True, comment='难度1-5'),
        
        # 复习状态
        sa.Column('mastery_level', sa.Float, default=0.0, comment='掌握度0-1'),
        sa.Column('review_count', sa.Integer, default=0, comment='复习次数'),
        sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True, comment='下次复习时间'),
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True, comment='上次复习时间'),
        
        # 时间戳
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # 软删除
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    op.create_index('idx_errors_user_subject', 'error_records', ['user_id', 'subject'])
    op.create_index('idx_errors_next_review', 'error_records', ['user_id', 'next_review_at'])
    # Note: Full text search index usually requires specific DB setup, skipping manual SQL execution inside python script if not essential or use op.execute properly
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_errors_question_fts ON error_records 
        USING GIN (to_tsvector('simple', question_text))
    """)
    
    # ============================================
    # 表2: error_analyses (AI分析结果表)
    # ============================================
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
    
    # ============================================
    # 表3: error_reviews (复习记录表)
    # ============================================
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
    
    # ============================================
    # 表4: error_knowledge_links (错题-知识点关联表)
    # ============================================
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


def downgrade():
    op.drop_table('error_knowledge_links')
    op.drop_table('error_reviews')
    op.drop_table('error_analyses')
    op.drop_table('error_records')
