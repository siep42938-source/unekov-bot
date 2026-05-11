"""Initial migration — all tables

Revision ID: 001
Revises: 
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(64), nullable=True),
        sa.Column('first_name', sa.String(128), nullable=False),
        sa.Column('last_name', sa.String(128), nullable=True),
        sa.Column('language_code', sa.String(8), nullable=False, server_default='en'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('role', sa.String(16), nullable=False, server_default='user'),
        sa.Column('token_balance', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens_spent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_active', sa.DateTime(timezone=True), nullable=True),
        sa.Column('work_mode', sa.String(16), nullable=False, server_default='standard'),
        sa.Column('last_daily_bonus', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_username', 'users', ['username'])

    op.create_table('subscriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('plan', sa.String(16), nullable=False, server_default='free'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monthly_tokens', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('tokens_used_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_mode', sa.String(16), nullable=False, server_default='standard'),
        sa.Column('granted_by', sa.BigInteger(), nullable=True),
        sa.Column('grant_reason', sa.String(256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    op.create_table('token_transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('mode', sa.String(16), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_token_transactions_user_id', 'token_transactions', ['user_id'])

    op.create_table('search_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('mode', sa.String(16), nullable=False),
        sa.Column('tokens_spent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('results_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('result_data', postgresql.JSON(), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default='completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_search_history_user_id', 'search_history', ['user_id'])

    op.create_table('telegram_users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tg_id', sa.BigInteger(), nullable=True),
        sa.Column('username', sa.String(64), nullable=True),
        sa.Column('first_name', sa.String(128), nullable=True),
        sa.Column('last_name', sa.String(128), nullable=True),
        sa.Column('phone', sa.String(32), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('language_code', sa.String(8), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('photo_url', sa.String(512), nullable=True),
        sa.Column('source', sa.String(128), nullable=True),
        sa.Column('source_group', sa.String(128), nullable=True),
        sa.Column('extra_data', postgresql.JSON(), nullable=True),
        sa.Column('seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tg_users_username_lower', 'telegram_users', ['username'])
    op.create_index('ix_tg_users_tg_id', 'telegram_users', ['tg_id'])
    op.create_index('ix_telegram_users_phone', 'telegram_users', ['phone'])

    op.create_table('tools',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('slug', sa.String(64), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(8), nullable=False, server_default='🔧'),
        sa.Column('category', sa.String(32), nullable=False, server_default='general'),
        sa.Column('tool_type', sa.String(32), nullable=False, server_default='search'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('min_plan', sa.String(16), nullable=False, server_default='free'),
        sa.Column('token_cost', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('config', postgresql.JSON(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table('database_sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('slug', sa.String(64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(8), nullable=False, server_default='🗄️'),
        sa.Column('source_type', sa.String(32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_indexed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('record_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_path', sa.String(512), nullable=True),
        sa.Column('connection_config', postgresql.JSON(), nullable=True),
        sa.Column('access_level', sa.String(16), nullable=False, server_default='free'),
        sa.Column('added_by', sa.BigInteger(), nullable=True),
        sa.Column('last_synced_at', sa.String(32), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table('uploaded_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('original_name', sa.String(256), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_type', sa.String(16), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_indexed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('columns_info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('resource', sa.String(64), nullable=True),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default='success'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])

    op.create_table('datasets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('record_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('schema_info', postgresql.JSON(), nullable=True),
        sa.Column('access_level', sa.String(16), nullable=False, server_default='free'),
        sa.Column('added_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table('api_keys',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('key_hash', sa.String(128), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
    )

    op.create_table('indexed_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_file', sa.String(256), nullable=False),
        sa.Column('source_tag', sa.String(64), nullable=False),
        sa.Column('tg_id', sa.String(32), nullable=True),
        sa.Column('phone', sa.String(32), nullable=True),
        sa.Column('username', sa.String(128), nullable=True),
        sa.Column('first_name', sa.String(128), nullable=True),
        sa.Column('last_name', sa.String(128), nullable=True),
        sa.Column('email', sa.String(256), nullable=True),
        sa.Column('raw', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_indexed_records_source_file', 'indexed_records', ['source_file'])
    op.create_index('ix_indexed_records_source_tag', 'indexed_records', ['source_tag'])
    op.create_index('ix_indexed_records_tg_id', 'indexed_records', ['tg_id'])
    op.create_index('ix_indexed_records_phone', 'indexed_records', ['phone'])
    op.create_index('ix_indexed_records_username', 'indexed_records', ['username'])
    op.create_index('ix_indexed_records_email', 'indexed_records', ['email'])
    # GIN full-text search index (PostgreSQL + pg_trgm extension required)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("""
        CREATE INDEX ix_indexed_records_fts
        ON indexed_records
        USING gin (raw gin_trgm_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_indexed_records_fts")
    op.drop_table('indexed_records')
    op.drop_table('api_keys')
    op.drop_table('datasets')
    op.drop_table('audit_logs')
    op.drop_table('uploaded_files')
    op.drop_table('database_sources')
    op.drop_table('tools')
    op.drop_table('telegram_users')
    op.drop_table('search_history')
    op.drop_table('token_transactions')
    op.drop_table('subscriptions')
    op.drop_table('users')
