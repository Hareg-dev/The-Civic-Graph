"""Complete database schema

Revision ID: 001
Revises: 
Create Date: 2025-12-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create video_posts table
    op.create_table('video_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=2000), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),  # JSON string for SQLite
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='processing'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('original_file_path', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_small', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_medium', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_large', sa.String(length=500), nullable=True),
        sa.Column('resolutions', sa.JSON(), nullable=True),
        sa.Column('is_federated', sa.Boolean(), nullable=True, default=False),
        sa.Column('origin_instance', sa.String(length=255), nullable=True),
        sa.Column('origin_actor_did', sa.String(length=255), nullable=True),
        sa.Column('activitypub_id', sa.String(length=500), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True, default=0),
        sa.Column('like_count', sa.Integer(), nullable=True, default=0),
        sa.Column('comment_count', sa.Integer(), nullable=True, default=0),
        sa.Column('share_count', sa.Integer(), nullable=True, default=0),
        sa.Column('engagement_score', sa.Float(), nullable=True, default=0.0),
        sa.Column('moderation_status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('moderation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_posts_id'), 'video_posts', ['id'], unique=False)
    op.create_index(op.f('ix_video_posts_user_id'), 'video_posts', ['user_id'], unique=False)
    op.create_index(op.f('ix_video_posts_status'), 'video_posts', ['status'], unique=False)
    op.create_index(op.f('ix_video_posts_is_federated'), 'video_posts', ['is_federated'], unique=False)
    op.create_index(op.f('ix_video_posts_activitypub_id'), 'video_posts', ['activitypub_id'], unique=True)
    op.create_index(op.f('ix_video_posts_engagement_score'), 'video_posts', ['engagement_score'], unique=False)
    op.create_index(op.f('ix_video_posts_moderation_status'), 'video_posts', ['moderation_status'], unique=False)
    op.create_index(op.f('ix_video_posts_created_at'), 'video_posts', ['created_at'], unique=False)
    op.create_index('idx_video_posts_user_created', 'video_posts', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_video_posts_status_created', 'video_posts', ['status', 'created_at'], unique=False)
    op.create_index('idx_video_posts_engagement', 'video_posts', ['engagement_score', 'created_at'], unique=False)

    # Create activities table
    op.create_table('activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activity_id', sa.String(length=500), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('actor', sa.String(length=500), nullable=False),
        sa.Column('object_id', sa.String(length=500), nullable=False),
        sa.Column('object_type', sa.String(length=50), nullable=True),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('is_local', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_id'), 'activities', ['id'], unique=False)
    op.create_index(op.f('ix_activities_activity_id'), 'activities', ['activity_id'], unique=True)
    op.create_index(op.f('ix_activities_activity_type'), 'activities', ['activity_type'], unique=False)
    op.create_index(op.f('ix_activities_actor'), 'activities', ['actor'], unique=False)
    op.create_index(op.f('ix_activities_object_id'), 'activities', ['object_id'], unique=False)
    op.create_index(op.f('ix_activities_is_local'), 'activities', ['is_local'], unique=False)
    op.create_index(op.f('ix_activities_created_at'), 'activities', ['created_at'], unique=False)
    op.create_index('idx_activities_type_created', 'activities', ['activity_type', 'created_at'], unique=False)
    op.create_index('idx_activities_actor_created', 'activities', ['actor', 'created_at'], unique=False)

    # Create delivery_records table
    op.create_table('delivery_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('inbox_url', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=True, default=0),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_records_id'), 'delivery_records', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_records_activity_id'), 'delivery_records', ['activity_id'], unique=False)
    op.create_index(op.f('ix_delivery_records_inbox_url'), 'delivery_records', ['inbox_url'], unique=False)
    op.create_index(op.f('ix_delivery_records_status'), 'delivery_records', ['status'], unique=False)
    op.create_index(op.f('ix_delivery_records_next_retry_at'), 'delivery_records', ['next_retry_at'], unique=False)
    op.create_index('idx_delivery_status_retry', 'delivery_records', ['status', 'next_retry_at'], unique=False)

    # Create user_interactions table
    op.create_table('user_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('video_post_id', sa.Integer(), nullable=False),
        sa.Column('interaction_type', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['video_post_id'], ['video_posts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_interactions_id'), 'user_interactions', ['id'], unique=False)
    op.create_index(op.f('ix_user_interactions_user_id'), 'user_interactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_interactions_video_post_id'), 'user_interactions', ['video_post_id'], unique=False)
    op.create_index(op.f('ix_user_interactions_interaction_type'), 'user_interactions', ['interaction_type'], unique=False)
    op.create_index(op.f('ix_user_interactions_created_at'), 'user_interactions', ['created_at'], unique=False)
    op.create_index('idx_interactions_user_created', 'user_interactions', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_interactions_user_type', 'user_interactions', ['user_id', 'interaction_type', 'created_at'], unique=False)

    # Create did_documents table
    op.create_table('did_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('did', sa.String(length=500), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('encrypted_private_key', sa.Text(), nullable=False),
        sa.Column('current_instance_url', sa.String(length=500), nullable=False),
        sa.Column('previous_instance_url', sa.String(length=500), nullable=True),
        sa.Column('migration_status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_did_documents_id'), 'did_documents', ['id'], unique=False)
    op.create_index(op.f('ix_did_documents_user_id'), 'did_documents', ['user_id'], unique=True)
    op.create_index(op.f('ix_did_documents_did'), 'did_documents', ['did'], unique=True)

    # Create moderation_records table
    op.create_table('moderation_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_post_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('reviewer_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('api_response', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['video_post_id'], ['video_posts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_moderation_records_id'), 'moderation_records', ['id'], unique=False)
    op.create_index(op.f('ix_moderation_records_video_post_id'), 'moderation_records', ['video_post_id'], unique=False)
    op.create_index(op.f('ix_moderation_records_status'), 'moderation_records', ['status'], unique=False)

    # Create comments table
    op.create_table('comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_post_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parent_comment_id', sa.Integer(), nullable=True),
        sa.Column('is_federated', sa.Boolean(), nullable=True, default=False),
        sa.Column('activitypub_id', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_comment_id'], ['comments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['video_post_id'], ['video_posts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comments_id'), 'comments', ['id'], unique=False)
    op.create_index(op.f('ix_comments_video_post_id'), 'comments', ['video_post_id'], unique=False)
    op.create_index(op.f('ix_comments_user_id'), 'comments', ['user_id'], unique=False)
    op.create_index(op.f('ix_comments_activitypub_id'), 'comments', ['activitypub_id'], unique=True)
    op.create_index(op.f('ix_comments_created_at'), 'comments', ['created_at'], unique=False)

    # Create followers table
    op.create_table('followers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('follower_actor', sa.String(length=500), nullable=False),
        sa.Column('follower_inbox', sa.String(length=500), nullable=False),
        sa.Column('is_local', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_followers_id'), 'followers', ['id'], unique=False)
    op.create_index(op.f('ix_followers_user_id'), 'followers', ['user_id'], unique=False)
    op.create_index(op.f('ix_followers_follower_actor'), 'followers', ['follower_actor'], unique=False)
    op.create_index('idx_followers_user_actor', 'followers', ['user_id', 'follower_actor'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('followers')
    op.drop_table('comments')
    op.drop_table('moderation_records')
    op.drop_table('did_documents')
    op.drop_table('user_interactions')
    op.drop_table('delivery_records')
    op.drop_table('activities')
    op.drop_table('video_posts')
    op.drop_table('users')