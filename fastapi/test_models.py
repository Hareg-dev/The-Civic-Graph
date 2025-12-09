#!/usr/bin/env python3
"""
Simple test script to verify database models are working correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User, VideoPost, Activity, DeliveryRecord, UserInteraction, ModerationRecord, DIDDocument, Comment, Follower
from app.config import settings
from datetime import datetime

def test_models():
    """Test that all models can be created and basic operations work"""
    
    # Create engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        try:
            # Test User model
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password_here",
                display_name="Test User",
                bio="Test bio"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✓ User created with ID: {user.id}")
            
            # Test VideoPost model
            video_post = VideoPost(
                user_id=user.id,
                title="Test Video",
                description="Test video description",
                tags=["test", "video"],
                duration=120,
                status="processing"
            )
            db.add(video_post)
            db.commit()
            db.refresh(video_post)
            print(f"✓ VideoPost created with ID: {video_post.id}")
            
            # Test Activity model
            activity = Activity(
                activity_id="https://example.com/activities/1",
                activity_type="Create",
                actor="https://example.com/users/testuser",
                object_id="https://example.com/videos/1",
                object_type="Video",
                content={"type": "Create", "actor": "testuser"},
                is_local=True
            )
            db.add(activity)
            db.commit()
            db.refresh(activity)
            print(f"✓ Activity created with ID: {activity.id}")
            
            # Test DeliveryRecord model
            delivery = DeliveryRecord(
                activity_id=activity.id,
                inbox_url="https://remote.example.com/inbox",
                status="pending"
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)
            print(f"✓ DeliveryRecord created with ID: {delivery.id}")
            
            # Test UserInteraction model
            interaction = UserInteraction(
                user_id=user.id,
                video_post_id=video_post.id,
                interaction_type="view"
            )
            db.add(interaction)
            db.commit()
            db.refresh(interaction)
            print(f"✓ UserInteraction created with ID: {interaction.id}")
            
            # Test ModerationRecord model
            moderation = ModerationRecord(
                video_post_id=video_post.id,
                status="pending",
                reason="Automated scan"
            )
            db.add(moderation)
            db.commit()
            db.refresh(moderation)
            print(f"✓ ModerationRecord created with ID: {moderation.id}")
            
            # Test DIDDocument model
            did_doc = DIDDocument(
                user_id=user.id,
                did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
                public_key="public_key_here",
                encrypted_private_key="encrypted_private_key_here",
                current_instance_url="https://example.com"
            )
            db.add(did_doc)
            db.commit()
            db.refresh(did_doc)
            print(f"✓ DIDDocument created with ID: {did_doc.id}")
            
            # Test Comment model
            comment = Comment(
                video_post_id=video_post.id,
                user_id=user.id,
                content="Great video!"
            )
            db.add(comment)
            db.commit()
            db.refresh(comment)
            print(f"✓ Comment created with ID: {comment.id}")
            
            # Test Follower model
            follower = Follower(
                user_id=user.id,
                follower_actor="https://remote.example.com/users/follower",
                follower_inbox="https://remote.example.com/inbox",
                is_local=False
            )
            db.add(follower)
            db.commit()
            db.refresh(follower)
            print(f"✓ Follower created with ID: {follower.id}")
            
            # Test relationships
            user_with_posts = db.query(User).filter(User.id == user.id).first()
            print(f"✓ User has {len(user_with_posts.video_posts)} video posts")
            print(f"✓ User has {len(user_with_posts.interactions)} interactions")
            
            video_with_interactions = db.query(VideoPost).filter(VideoPost.id == video_post.id).first()
            print(f"✓ VideoPost has {len(video_with_interactions.interactions)} interactions")
            print(f"✓ VideoPost has {len(video_with_interactions.moderation_records)} moderation records")
            
            activity_with_deliveries = db.query(Activity).filter(Activity.id == activity.id).first()
            print(f"✓ Activity has {len(activity_with_deliveries.delivery_records)} delivery records")
            
            print("\n🎉 All models and relationships working correctly!")
            
        except Exception as e:
            print(f"❌ Error testing models: {e}")
            db.rollback()
            raise
        finally:
            # Clean up test data
            db.query(Follower).delete()
            db.query(Comment).delete()
            db.query(DIDDocument).delete()
            db.query(ModerationRecord).delete()
            db.query(UserInteraction).delete()
            db.query(DeliveryRecord).delete()
            db.query(Activity).delete()
            db.query(VideoPost).delete()
            db.query(User).delete()
            db.commit()
            print("✓ Test data cleaned up")

if __name__ == "__main__":
    test_models()