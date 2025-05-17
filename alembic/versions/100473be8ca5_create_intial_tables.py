"""create initial tables

Revision ID: 100473be8ca5
Revises: 
Create Date: 2023-05-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '100473be8ca5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key_value', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_client_id'), 'api_keys', ['client_id'], unique=False)
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_api_keys_key_value'), 'api_keys', ['key_value'], unique=True)

    # Verifications table
    op.create_table(
        'verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('verification_id', sa.String(), nullable=False),
        sa.Column('business_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('result', sa.String(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verifications_business_id'), 'verifications', ['business_id'], unique=False)
    op.create_index(op.f('ix_verifications_id'), 'verifications', ['id'], unique=False)
    op.create_index(op.f('ix_verifications_user_id'), 'verifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_verifications_verification_id'), 'verifications', ['verification_id'], unique=True)

    # Verification Data table
    op.create_table(
        'verification_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('verification_id', sa.String(), nullable=False),
        sa.Column('data_type', sa.String(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['verification_id'], ['verifications.verification_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verification_data_id'), 'verification_data', ['id'], unique=False)

    # Verification Results table
    op.create_table(
        'verification_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('verification_id', sa.String(), nullable=False),
        sa.Column('agent_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('checks', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['verification_id'], ['verifications.verification_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verification_results_id'), 'verification_results', ['id'], unique=False)

    # UBO Verifications table
    op.create_table(
        'ubo_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('verification_id', sa.String(), nullable=False),
        sa.Column('ubo_user_id', sa.String(), nullable=False),
        sa.Column('ubo_verification_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['verification_id'], ['verifications.verification_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ubo_verifications_id'), 'ubo_verifications', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ubo_verifications_id'), table_name='ubo_verifications')
    op.drop_table('ubo_verifications')
    op.drop_index(op.f('ix_verification_results_id'), table_name='verification_results')
    op.drop_table('verification_results')
    op.drop_index(op.f('ix_verification_data_id'), table_name='verification_data')
    op.drop_table('verification_data')
    op.drop_index(op.f('ix_verifications_verification_id'), table_name='verifications')
    op.drop_index(op.f('ix_verifications_user_id'), table_name='verifications')
    op.drop_index(op.f('ix_verifications_id'), table_name='verifications')
    op.drop_index(op.f('ix_verifications_business_id'), table_name='verifications')
    op.drop_table('verifications')
    op.drop_index(op.f('ix_api_keys_key_value'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_client_id'), table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')